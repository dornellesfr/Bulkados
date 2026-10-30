from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import CatalogUnavailableError, DomainError
from app.domain.scryfall import CatalogDraft
from app.integrations.scryfall import CardCatalog
from app.models.catalog import CatalogCard
from app.schemas.catalog import CatalogCardRead


async def search_cards(
    session: AsyncSession,
    catalog: CardCatalog,
    query: str,
) -> list[CatalogCardRead]:
    try:
        drafts = await catalog.search(query)
    except CatalogUnavailableError as exc:
        raise DomainError(503, "catalog unavailable") from exc
    results: list[CatalogCardRead] = []
    for draft in drafts:
        card = await _upsert(session, draft)
        results.append(_read(card, draft.mana_cost))
    await session.flush()
    return results


async def _upsert(session: AsyncSession, draft: CatalogDraft) -> CatalogCard:
    card = await session.scalar(select(CatalogCard).where(CatalogCard.oracle_id == draft.oracle_id))
    if card is None:
        card = CatalogCard(
            oracle_id=draft.oracle_id,
            name_en=draft.name_en,
            name_pt=draft.name_pt,
            type_line=draft.type_line,
            oracle_text=draft.oracle_text,
            color_identity=list(draft.color_identity),
            keywords=list(draft.keywords),
            is_basic=draft.is_basic,
            any_number_allowed=draft.any_number_allowed,
            commander_legal=draft.commander_legal,
            can_be_commander=draft.can_be_commander,
            partner_kind=draft.partner_kind,
        )
        session.add(card)
        await session.flush()
        return card
    card.name_en = draft.name_en
    if draft.name_pt is not None:
        card.name_pt = draft.name_pt
    card.type_line = draft.type_line
    card.oracle_text = draft.oracle_text
    card.color_identity = list(draft.color_identity)
    card.keywords = list(draft.keywords)
    card.is_basic = draft.is_basic
    card.any_number_allowed = draft.any_number_allowed
    card.commander_legal = draft.commander_legal
    card.can_be_commander = draft.can_be_commander
    card.partner_kind = draft.partner_kind
    return card


def _read(card: CatalogCard, mana_cost: str | None) -> CatalogCardRead:
    return CatalogCardRead(
        id=card.id,
        oracle_id=card.oracle_id,
        name_en=card.name_en,
        name_pt=card.name_pt,
        mana_cost=mana_cost,
        type_line=card.type_line,
        color_identity=list(card.color_identity),
        is_basic=card.is_basic,
    )
