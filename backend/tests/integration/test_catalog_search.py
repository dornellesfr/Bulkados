from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.core.database import SessionFactory
from app.domain.enums import CommanderLegal
from app.domain.scryfall import CatalogDraft
from app.services.catalog import search_cards
from app.services.catalog_sync import sync_catalog
from tests.integration.conftest import bearer, rows
from tests.integration.test_admin import register

URL = "/api/v1/catalog/cards"


def _draft(
    number: int,
    name_en: str,
    *,
    name_pt: str | None = None,
    image_url: str | None = None,
) -> CatalogDraft:
    return CatalogDraft(
        oracle_id=UUID(f"00000000-0000-0000-0000-{number:012d}"),
        name_en=name_en,
        name_pt=name_pt,
        mana_cost="{2}{U}",
        image_url=image_url,
        type_line="Instant",
        oracle_text="",
        color_identity=("U",),
        keywords=(),
        is_basic=False,
        any_number_allowed=False,
        commander_legal=CommanderLegal.legal,
        can_be_commander=False,
        partner_kind=None,
    )


class _Source:
    def __init__(self, drafts: list[CatalogDraft], names: list[tuple[UUID, str]]) -> None:
        self._drafts = drafts
        self._names = names

    async def oracle_cards(self) -> AsyncIterator[CatalogDraft]:
        for draft in self._drafts:
            yield draft

    async def portuguese_names(self) -> AsyncIterator[tuple[UUID, str]]:
        for pair in self._names:
            yield pair


async def _load(drafts: list[CatalogDraft], names: list[tuple[UUID, str]] | None = None) -> None:
    """Carrega o acervo como a atualização real faz e o marca como carregado."""
    async with SessionFactory() as session:
        await sync_catalog(session, _Source(drafts, names or []))
        await session.execute(
            text(
                "INSERT INTO catalog_sync (id, last_synced_at) VALUES (1, now()) "
                "ON CONFLICT (id) DO UPDATE SET last_synced_at = now()"
            )
        )
        await session.commit()


async def _names(client: AsyncClient, token: object, q: str) -> list[object]:
    response = await client.get(URL, params={"q": q}, headers=bearer(token))
    assert response.status_code == 200, response.text
    return [card["name_en"] for card in rows(response)]


@pytest.mark.integration
async def test_suggestions_start_with_exact_then_prefix_then_inside_the_name(
    client: AsyncClient,
) -> None:
    await _load(
        [
            _draft(1, "Fear of Abduction"),
            _draft(2, "Abduction"),
            _draft(3, "Abrade"),
            _draft(4, "Sol"),
            _draft(5, "Solitude"),
            _draft(6, "Sol Ring"),
            _draft(7, "Mana Ring"),
        ]
    )
    token = (await register(client, "ada"))["access_token"]

    assert await _names(client, token, "abd") == ["Abduction", "Fear of Abduction"]
    assert await _names(client, token, "sol") == ["Sol", "Sol Ring", "Solitude"]
    assert await _names(client, token, "ring") == ["Mana Ring", "Sol Ring"]


@pytest.mark.integration
async def test_search_finds_portuguese_names_without_caring_for_accents_or_case(
    client: AsyncClient,
) -> None:
    await _load(
        [_draft(1, "Abduction"), _draft(2, "Abrade")],
        [(UUID(int=1), "Abdução"), (UUID(int=2), "Abrasão")],
    )
    token = (await register(client, "ada"))["access_token"]

    assert await _names(client, token, "abducao") == ["Abduction"]
    assert await _names(client, token, "ABDUÇÃO") == ["Abduction"]
    assert await _names(client, token, "abra") == ["Abrade"]


@pytest.mark.integration
async def test_search_returns_at_most_twenty_and_ignores_punctuation_only_queries(
    client: AsyncClient,
) -> None:
    await _load([_draft(number, f"Zed {number:02d}") for number in range(1, 31)])
    token = (await register(client, "ada"))["access_token"]

    assert len(await _names(client, token, "zed")) == 20
    assert await _names(client, token, "!!") == []


@pytest.mark.integration
async def test_search_returns_cost_and_image_from_the_stored_catalog(client: AsyncClient) -> None:
    await _load([_draft(1, "Abduction", image_url="https://cards.example/abduction.jpg")])
    token = (await register(client, "ada"))["access_token"]

    response = await client.get(URL, params={"q": "abd"}, headers=bearer(token))

    [card] = rows(response)
    assert card["mana_cost"] == "{2}{U}"
    assert card["image_url"] == "https://cards.example/abduction.jpg"


class _LiveCatalog:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search(self, query: str) -> list[CatalogDraft]:
        self.queries.append(query)
        return [_draft(1, "Abduction")]


@pytest.mark.integration
@pytest.mark.usefixtures("client")
async def test_before_the_first_load_it_still_asks_scryfall() -> None:
    live = _LiveCatalog()

    async with SessionFactory() as session:
        found = await search_cards(session, live, "abd")

    assert [card.name_en for card in found] == ["Abduction"]
    assert live.queries == ["abd"]


@pytest.mark.integration
@pytest.mark.usefixtures("client")
async def test_after_the_first_load_it_no_longer_asks_scryfall() -> None:
    await _load([_draft(1, "Abduction")])
    live = _LiveCatalog()

    async with SessionFactory() as session:
        found = await search_cards(session, live, "abd")

    assert [card.name_en for card in found] == ["Abduction"]
    assert live.queries == []
