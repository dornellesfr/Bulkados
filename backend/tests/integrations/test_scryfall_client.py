import gzip
import json
from collections.abc import AsyncIterator
from uuid import UUID

import httpx
import pytest

from app.core.errors import CatalogUnavailableError
from app.integrations.scryfall import ScryfallClient

API = "https://api.scryfall.test"
DOWNLOAD = "https://data.scryfall.test/oracle-cards.jsonl.gz"


class _Chunks(httpx.AsyncByteStream):
    """Entrega o corpo em pedaços pequenos, para cortar linhas e o gzip no meio."""

    def __init__(self, body: bytes, size: int) -> None:
        self._body = body
        self._size = size

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for start in range(0, len(self._body), self._size):
            yield self._body[start : start + self._size]


def _oid(number: int) -> str:
    return f"00000000-0000-0000-0000-{number:012d}"


def _card(number: int, name: str, **extra: object) -> dict[str, object]:
    return {
        "object": "card",
        "oracle_id": _oid(number),
        "name": name,
        "type_line": "Artifact",
        "oracle_text": "",
        "color_identity": [],
        "keywords": [],
        "legalities": {"commander": "legal"},
        "games": ["paper"],
        "layout": "normal",
        **extra,
    }


def _jsonl_gz(cards: list[dict[str, object]]) -> bytes:
    return gzip.compress("\n".join(json.dumps(card) for card in cards).encode())


def _client(handler: httpx.MockTransport) -> ScryfallClient:
    return ScryfallClient(
        API,
        "TestAgent/1.0",
        min_interval_seconds=0,
        page_interval_seconds=0,
        transport=handler,
    )


def _bulk_listing() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "data": [
                {"type": "all_cards", "jsonl_download_uri": "https://data.scryfall.test/all.gz"},
                {"type": "oracle_cards", "jsonl_download_uri": DOWNLOAD},
            ]
        },
    )


async def test_oracle_cards_streams_the_gzip_and_keeps_only_game_cards() -> None:
    body = _jsonl_gz(
        [
            _card(1, "Sol Ring"),
            _card(2, "Goblin", layout="token"),
            _card(3, "Arena Only", games=["arena"]),
            _card(4, "Arcane Signet"),
            _card(5, "Palinchron", games=["mtgo"]),
        ]
    )
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/bulk-data":
            return _bulk_listing()
        return httpx.Response(200, stream=_Chunks(body, 7))

    drafts = [draft async for draft in _client(httpx.MockTransport(handler)).oracle_cards()]

    assert [draft.name_en for draft in drafts] == ["Sol Ring", "Arcane Signet", "Palinchron"]
    assert str(seen[-1].url) == DOWNLOAD
    assert seen[-1].headers["User-Agent"] == "TestAgent/1.0"


async def test_oracle_cards_reports_a_failed_download() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/bulk-data":
            return _bulk_listing()
        return httpx.Response(503)

    with pytest.raises(CatalogUnavailableError):
        _ = [draft async for draft in _client(httpx.MockTransport(handler)).oracle_cards()]


async def test_oracle_cards_reports_a_corrupted_gzip() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/bulk-data":
            return _bulk_listing()
        return httpx.Response(200, stream=_Chunks(b"isto nao e um gzip", 5))

    with pytest.raises(CatalogUnavailableError):
        _ = [draft async for draft in _client(httpx.MockTransport(handler)).oracle_cards()]


async def test_portuguese_names_follow_the_pages_and_skip_untranslated_ones() -> None:
    second_page = f"{API}/cards/search?page=2"
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if request.url.params.get("page") == "2":
            return httpx.Response(
                200,
                json={
                    "has_more": False,
                    "data": [_card(3, "Abrade", lang="pt", printed_name="Abrasão")],
                },
            )
        return httpx.Response(
            200,
            json={
                "has_more": True,
                "next_page": second_page,
                "data": [
                    _card(1, "Sol Ring", lang="pt", printed_name="Anel Solar"),
                    _card(2, "Island", lang="pt", printed_name="Island"),
                ],
            },
        )

    names = [pair async for pair in _client(httpx.MockTransport(handler)).portuguese_names()]

    assert names == [(UUID(_oid(1)), "Anel Solar"), (UUID(_oid(3)), "Abrasão")]
    assert requested[0].startswith(f"{API}/cards/search?")
    assert "q=lang%3Apt" in requested[0] and "unique=cards" in requested[0]
    assert requested[1] == second_page


async def test_portuguese_names_refuse_a_next_page_outside_scryfall() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            json={"has_more": True, "next_page": "https://outro.example/cards/search", "data": []},
        )

    with pytest.raises(CatalogUnavailableError):
        _ = [pair async for pair in _client(httpx.MockTransport(handler)).portuguese_names()]


async def test_a_rate_limited_page_is_retried_after_the_wait() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(
            200,
            json={
                "has_more": False,
                "data": [_card(1, "Sol Ring", lang="pt", printed_name="Anel")],
            },
        )

    names = [pair async for pair in _client(httpx.MockTransport(handler)).portuguese_names()]

    assert names == [(UUID(_oid(1)), "Anel")]
    assert len(calls) == 2


async def test_it_gives_up_after_repeated_rate_limits() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(429, headers={"Retry-After": "0"})

    with pytest.raises(CatalogUnavailableError):
        _ = [pair async for pair in _client(httpx.MockTransport(handler)).portuguese_names()]

    assert len(calls) == 6
