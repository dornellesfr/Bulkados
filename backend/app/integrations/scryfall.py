import asyncio
import json
import logging
import time
import zlib
from collections.abc import AsyncIterator, Mapping
from functools import lru_cache
from typing import Protocol
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.core.errors import CatalogUnavailableError
from app.domain.scryfall import CatalogDraft, catalog_draft_from_scryfall, is_catalog_card

logger = logging.getLogger(__name__)

_DOWNLOAD_TIMEOUT_SECONDS = 60
_RATE_LIMIT_RETRIES = 5
_DEFAULT_RETRY_AFTER_SECONDS = 30
_MAX_RETRY_AFTER_SECONDS = 120


class CardCatalog(Protocol):
    async def search(self, query: str) -> list[CatalogDraft]: ...


class CatalogSource(Protocol):
    """Origem do acervo inteiro: as cartas em inglês e os nomes em português."""

    def oracle_cards(self) -> AsyncIterator[CatalogDraft]: ...

    def portuguese_names(self) -> AsyncIterator[tuple[UUID, str]]: ...


class ScryfallClient:
    """Busca no Scryfall com User-Agent próprio e intervalo abaixo de 10 req/s."""

    def __init__(
        self,
        base_url: str,
        user_agent: str,
        min_interval_seconds: float = 0.12,
        page_interval_seconds: float = 1.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._user_agent = user_agent
        self._min_interval_seconds = min_interval_seconds
        self._page_interval_seconds = page_interval_seconds
        self._transport = transport
        self._lock = asyncio.Lock()
        self._last_request_at = 0.0

    async def search(self, query: str) -> list[CatalogDraft]:
        english = await self._search(query, unique="cards")
        portuguese = await self._search(f"lang:pt {query}", unique="prints")
        merged: dict[str, CatalogDraft] = {}
        for card in english:
            merged[str(card.oracle_id)] = card
        for card in portuguese:
            current = merged.get(str(card.oracle_id))
            if current is None:
                merged[str(card.oracle_id)] = card
            elif card.name_pt is not None and current.name_pt is None:
                merged[str(card.oracle_id)] = CatalogDraft(
                    oracle_id=current.oracle_id,
                    name_en=current.name_en,
                    name_pt=card.name_pt,
                    mana_cost=current.mana_cost,
                    image_url=current.image_url,
                    type_line=current.type_line,
                    oracle_text=current.oracle_text,
                    color_identity=current.color_identity,
                    keywords=current.keywords,
                    is_basic=current.is_basic,
                    any_number_allowed=current.any_number_allowed,
                    commander_legal=current.commander_legal,
                    can_be_commander=current.can_be_commander,
                    partner_kind=current.partner_kind,
                )
        return list(merged.values())

    async def _search(self, query: str, unique: str) -> list[CatalogDraft]:
        payload = await self._get("/cards/search", {"q": query, "unique": unique})
        if payload is None:
            return []
        data = payload.get("data")
        if not isinstance(data, list):
            return []
        drafts: list[CatalogDraft] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            draft = catalog_draft_from_scryfall(_string_keys(item))
            if draft is not None:
                drafts.append(draft)
        return drafts

    async def oracle_cards(self) -> AsyncIterator[CatalogDraft]:
        """Uma carta por Oracle ID, lida do arquivo em massa sem carregá-lo inteiro."""
        async for item in self._download_jsonl(await self._bulk_download_url("oracle_cards")):
            draft = catalog_draft_from_scryfall(item) if is_catalog_card(item) else None
            if draft is not None:
                yield draft

    async def portuguese_names(self) -> AsyncIterator[tuple[UUID, str]]:
        payload = await self._get(
            "/cards/search", {"q": "lang:pt", "unique": "cards", "order": "name"}
        )
        while payload is not None:
            data = payload.get("data")
            for item in data if isinstance(data, list) else []:
                if not isinstance(item, dict):
                    continue
                draft = catalog_draft_from_scryfall(_string_keys(item))
                if draft is not None and draft.name_pt is not None:
                    yield draft.oracle_id, draft.name_pt
            next_page = payload.get("next_page")
            if payload.get("has_more") is not True or not isinstance(next_page, str):
                return
            if not next_page.startswith(f"{self._base_url}/"):
                raise CatalogUnavailableError
            await asyncio.sleep(self._page_interval_seconds)
            payload = await self._get(next_page)

    async def _bulk_download_url(self, bulk_type: str) -> str:
        payload = await self._get("/bulk-data")
        data = payload.get("data") if payload is not None else None
        for item in data if isinstance(data, list) else []:
            if isinstance(item, dict) and item.get("type") == bulk_type:
                url = item.get("jsonl_download_uri")
                if isinstance(url, str) and url.startswith("https://"):
                    return url
        raise CatalogUnavailableError

    async def _download_jsonl(self, url: str) -> AsyncIterator[dict[str, object]]:
        decompressor = zlib.decompressobj(zlib.MAX_WBITS | 16)
        pending = b""
        try:
            async with (
                self._client(_DOWNLOAD_TIMEOUT_SECONDS) as client,
                client.stream("GET", url, headers={"User-Agent": self._user_agent}) as response,
            ):
                if response.status_code != 200:
                    logger.warning("scryfall bulk download responded with %s", response.status_code)
                    raise CatalogUnavailableError
                async for chunk in response.aiter_raw():
                    *lines, pending = (pending + decompressor.decompress(chunk)).split(b"\n")
                    for line in lines:
                        if (item := _json_object(line)) is not None:
                            yield item
        except (httpx.HTTPError, zlib.error) as exc:
            logger.warning("scryfall bulk download failed")
            raise CatalogUnavailableError from exc
        if (item := _json_object(pending + decompressor.flush())) is not None:
            yield item

    def _client(self, timeout: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=timeout, transport=self._transport)

    async def _get(
        self,
        path: str,
        params: dict[str, str] | None = None,
    ) -> Mapping[str, object] | None:
        url = path if path.startswith("https://") else f"{self._base_url}{path}"
        for attempt in range(_RATE_LIMIT_RETRIES + 1):
            await self._wait_turn()
            response = await self._send(url, params)
            if response.status_code != 429 or attempt == _RATE_LIMIT_RETRIES:
                break
            delay = _retry_after_seconds(response)
            logger.warning("scryfall rate limit reached, waiting %s seconds", delay)
            await asyncio.sleep(delay)
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            logger.warning("scryfall responded with status %s", response.status_code)
            raise CatalogUnavailableError
        payload: object = response.json()
        if not isinstance(payload, dict):
            raise CatalogUnavailableError
        return _string_keys(payload)

    async def _send(self, url: str, params: dict[str, str] | None) -> httpx.Response:
        try:
            async with self._client(10) as client:
                return await client.get(
                    url,
                    params=params,
                    headers={
                        "User-Agent": self._user_agent,
                        "Accept": "application/json",
                    },
                )
        except httpx.HTTPError as exc:
            logger.warning("scryfall request failed")
            raise CatalogUnavailableError from exc

    async def _wait_turn(self) -> None:
        async with self._lock:
            elapsed = time.monotonic() - self._last_request_at
            remaining = self._min_interval_seconds - elapsed
            if remaining > 0:
                await asyncio.sleep(remaining)
            self._last_request_at = time.monotonic()


def _string_keys(payload: Mapping[object, object]) -> dict[str, object]:
    return {key: value for key, value in payload.items() if isinstance(key, str)}


def _retry_after_seconds(response: httpx.Response) -> float:
    raw = response.headers.get("Retry-After", "")
    try:
        seconds = float(raw)
    except ValueError:
        seconds = _DEFAULT_RETRY_AFTER_SECONDS
    return min(max(seconds, 0), _MAX_RETRY_AFTER_SECONDS)


def _json_object(line: bytes) -> dict[str, object] | None:
    if not line.strip():
        return None
    parsed: object = json.loads(line)
    return _string_keys(parsed) if isinstance(parsed, dict) else None


@lru_cache
def scryfall_client() -> ScryfallClient:
    settings = get_settings()
    return ScryfallClient(settings.scryfall_api_url, settings.scryfall_user_agent)
