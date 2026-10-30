from uuid import UUID

import pytest
from sqlalchemy import select

from app.core.database import SessionFactory
from app.domain.enums import CommanderLegal
from app.domain.scryfall import CatalogDraft
from app.models.catalog import CatalogCard
from app.services.catalog import search_cards


class FakeCatalog:
    def __init__(self, drafts: list[CatalogDraft]) -> None:
        self._drafts = drafts

    async def search(self, query: str) -> list[CatalogDraft]:
        del query
        return self._drafts


def _draft(*, name_pt: str | None, image_url: str | None) -> CatalogDraft:
    return CatalogDraft(
        oracle_id=UUID("00000000-0000-0000-0000-0000000000a1"),
        name_en="Abduction",
        name_pt=name_pt,
        mana_cost="{2}{U}",
        image_url=image_url,
        type_line="Enchantment — Aura",
        oracle_text="",
        color_identity=("U",),
        keywords=(),
        is_basic=False,
        any_number_allowed=False,
        commander_legal=CommanderLegal.legal,
        can_be_commander=False,
        partner_kind=None,
    )


async def _search(draft: CatalogDraft) -> None:
    async with SessionFactory() as session:
        await search_cards(session, FakeCatalog([draft]), "abd")
        await session.commit()


async def _stored() -> CatalogCard:
    async with SessionFactory() as session:
        return (await session.scalars(select(CatalogCard))).one()


@pytest.mark.integration
@pytest.mark.usefixtures("client")
async def test_search_stores_search_keys_cost_and_image() -> None:
    await _search(_draft(name_pt="Abdução", image_url="https://cards.example/abduction.jpg"))

    card = await _stored()
    assert card.search_en == "abduction"
    assert card.search_pt == "abducao"
    assert card.mana_cost == "{2}{U}"
    assert card.image_url == "https://cards.example/abduction.jpg"


@pytest.mark.integration
@pytest.mark.usefixtures("client")
async def test_a_later_search_without_portuguese_or_image_keeps_what_was_stored() -> None:
    await _search(_draft(name_pt="Abdução", image_url="https://cards.example/abduction.jpg"))
    await _search(_draft(name_pt=None, image_url=None))

    card = await _stored()
    assert card.name_pt == "Abdução"
    assert card.search_pt == "abducao"
    assert card.image_url == "https://cards.example/abduction.jpg"
