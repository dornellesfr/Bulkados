from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.core.database import SessionFactory
from app.domain.enums import CommanderLegal
from app.domain.scryfall import CatalogDraft
from app.models.catalog import CatalogCard
from app.services.catalog_sync import SyncSummary, sync_catalog


class FakeSource:
    def __init__(self, drafts: list[CatalogDraft], names: list[tuple[UUID, str]]) -> None:
        self._drafts = drafts
        self._names = names

    async def oracle_cards(self) -> AsyncIterator[CatalogDraft]:
        for draft in self._drafts:
            yield draft

    async def portuguese_names(self) -> AsyncIterator[tuple[UUID, str]]:
        for pair in self._names:
            yield pair


def _oid(number: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{number:012d}")


def _draft(number: int, name_en: str, *, type_line: str = "Instant") -> CatalogDraft:
    return CatalogDraft(
        oracle_id=_oid(number),
        name_en=name_en,
        name_pt=None,
        mana_cost="{R}",
        image_url=f"https://cards.example/{number}.jpg",
        type_line=type_line,
        oracle_text="",
        color_identity=("R",),
        keywords=(),
        is_basic=False,
        any_number_allowed=False,
        commander_legal=CommanderLegal.legal,
        can_be_commander=False,
        partner_kind=None,
    )


async def _sync(source: FakeSource) -> SyncSummary:
    async with SessionFactory() as session:
        return await sync_catalog(session, source)


async def _cards() -> dict[str, CatalogCard]:
    async with SessionFactory() as session:
        rows = (await session.scalars(select(CatalogCard))).all()
    return {card.name_en: card for card in rows}


@pytest.mark.integration
@pytest.mark.usefixtures("client")
async def test_sync_stores_cards_and_portuguese_names() -> None:
    source = FakeSource(
        [_draft(1, "Abrade"), _draft(2, "Sol Ring", type_line="Artifact")],
        [(_oid(1), "Abrasão"), (_oid(99), "Carta Fantasma")],
    )

    summary = await _sync(source)

    cards = await _cards()
    assert summary == SyncSummary(cards=2, portuguese_names=2)
    assert set(cards) == {"Abrade", "Sol Ring"}
    assert cards["Abrade"].name_pt == "Abrasão"
    assert cards["Abrade"].search_pt == "abrasao"
    assert cards["Abrade"].search_en == "abrade"
    assert cards["Sol Ring"].name_pt is None
    assert cards["Sol Ring"].image_url == "https://cards.example/2.jpg"


@pytest.mark.integration
@pytest.mark.usefixtures("client")
async def test_a_second_sync_updates_without_duplicating_or_losing_names() -> None:
    await _sync(FakeSource([_draft(1, "Abrade")], [(_oid(1), "Abrasão")]))

    await _sync(FakeSource([_draft(1, "Abrade", type_line="Sorcery")], []))

    cards = await _cards()
    assert list(cards) == ["Abrade"]
    assert cards["Abrade"].type_line == "Sorcery"
    assert cards["Abrade"].name_pt == "Abrasão"
    assert cards["Abrade"].search_pt == "abrasao"


@pytest.mark.integration
@pytest.mark.usefixtures("client")
async def test_sync_handles_more_than_one_chunk() -> None:
    drafts = [_draft(number, f"Carta {number}") for number in range(1, 1051)]

    summary = await _sync(FakeSource(drafts, [(_oid(1050), "Carta Mil e Cinquenta")]))

    async with SessionFactory() as session:
        total = await session.scalar(select(func.count()).select_from(CatalogCard))
    assert summary.cards == 1050
    assert total == 1050
    assert (await _cards())["Carta 1050"].name_pt == "Carta Mil e Cinquenta"
