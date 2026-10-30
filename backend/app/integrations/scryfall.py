import asyncio
import logging
import time
from collections.abc import Mapping
from typing import Protocol

import httpx

from app.core.errors import CatalogUnavailableError
from app.domain.scryfall import CatalogDraft, catalog_draft_from_scryfall

logger = logging.getLogger(__name__)


class CardCatalog(Protocol):
    async def search(self, query: str) -> list[CatalogDraft]: ...


class ScryfallClient:
    """Busca no Scryfall com User-Agent próprio e intervalo abaixo de 10 req/s."""

    def __init__(
        self,
        base_url: str,
        user_agent: str,
        min_interval_seconds: float = 0.12,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._user_agent = user_agent
        self._min_interval_seconds = min_interval_seconds
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

    async def _get(self, path: str, params: dict[str, str]) -> Mapping[str, object] | None:
        await self._wait_turn()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self._base_url}{path}",
                    params=params,
                    headers={
                        "User-Agent": self._user_agent,
                        "Accept": "application/json",
                    },
                )
        except httpx.HTTPError as exc:
            logger.warning("scryfall request failed")
            raise CatalogUnavailableError from exc
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            logger.warning("scryfall responded with status %s", response.status_code)
            raise CatalogUnavailableError
        payload: object = response.json()
        if not isinstance(payload, dict):
            raise CatalogUnavailableError
        return _string_keys(payload)

    async def _wait_turn(self) -> None:
        async with self._lock:
            elapsed = time.monotonic() - self._last_request_at
            remaining = self._min_interval_seconds - elapsed
            if remaining > 0:
                await asyncio.sleep(remaining)
            self._last_request_at = time.monotonic()


def _string_keys(payload: Mapping[object, object]) -> dict[str, object]:
    return {key: value for key, value in payload.items() if isinstance(key, str)}
