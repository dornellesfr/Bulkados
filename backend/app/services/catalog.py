from collections.abc import Sequence

from sqlalchemy import case, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import CatalogUnavailableError, DomainError
from app.domain.scryfall import CatalogDraft
from app.domain.search import normalize_search_text
from app.integrations.scryfall import CardCatalog
from app.models.catalog import CatalogCard
from app.models.catalog_sync import CatalogSync
from app.schemas.catalog import CatalogCardRead

_SUGGESTION_LIMIT = 20


async def search_cards(
    session: AsyncSession,
    catalog: CardCatalog,
    query: str,
    within: Sequence[str] | None = None,
) -> list[CatalogCardRead]:
    """Sugere cartas do acervo local. Enquanto ele nunca foi carregado, consulta o Scryfall.

    Com `within`, só entram cartas cuja identidade de cor cabe nessas cores.
    """
    if await _catalog_loaded(session):
        return await _search_local(session, query, within)
    return await _search_live(session, catalog, query, within)


async def _catalog_loaded(session: AsyncSession) -> bool:
    synced_at = await session.scalar(select(CatalogSync.last_synced_at).where(CatalogSync.id == 1))
    return synced_at is not None


async def _search_local(
    session: AsyncSession,
    query: str,
    within: Sequence[str] | None,
) -> list[CatalogCardRead]:
    key = normalize_search_text(query)
    if not key:
        return []
    prefix, word = f"{key}%", f"% {key}%"
    exact = or_(CatalogCard.search_en == key, CatalogCard.search_pt == key)
    starts = or_(CatalogCard.search_en.like(prefix), CatalogCard.search_pt.like(prefix))
    inside = or_(CatalogCard.search_en.like(word), CatalogCard.search_pt.like(word))
    matches = or_(starts, inside)
    if within is not None:
        matches = matches & CatalogCard.color_identity.contained_by(list(within))
    statement = (
        select(CatalogCard)
        .where(matches)
        .order_by(case((exact, 0), (starts, 1), else_=2), CatalogCard.search_en.collate("C"))
        .limit(_SUGGESTION_LIMIT)
    )
    return [_read(card) for card in (await session.scalars(statement)).all()]


async def _search_live(
    session: AsyncSession,
    catalog: CardCatalog,
    query: str,
    within: Sequence[str] | None,
) -> list[CatalogCardRead]:
    try:
        drafts = await catalog.search(query)
    except CatalogUnavailableError as exc:
        raise DomainError(503, "catalog unavailable") from exc
    results: list[CatalogCardRead] = []
    for draft in drafts:
        card = await _upsert(session, draft)
        if within is None or {color.upper() for color in draft.color_identity} <= set(within):
            results.append(_read(card))
    await session.flush()
    return results


async def _upsert(session: AsyncSession, draft: CatalogDraft) -> CatalogCard:
    card = await session.scalar(select(CatalogCard).where(CatalogCard.oracle_id == draft.oracle_id))
    if card is None:
        card = CatalogCard(
            oracle_id=draft.oracle_id,
            name_en=draft.name_en,
            name_pt=draft.name_pt,
            search_en=normalize_search_text(draft.name_en),
            search_pt=_search_pt(draft),
            mana_cost=draft.mana_cost,
            image_url=draft.image_url,
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
    card.search_en = normalize_search_text(draft.name_en)
    if draft.name_pt is not None:
        card.name_pt = draft.name_pt
        card.search_pt = _search_pt(draft)
    card.mana_cost = draft.mana_cost
    if draft.image_url is not None:
        card.image_url = draft.image_url
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


def _search_pt(draft: CatalogDraft) -> str | None:
    return normalize_search_text(draft.name_pt) if draft.name_pt is not None else None


def _read(card: CatalogCard) -> CatalogCardRead:
    return CatalogCardRead(
        id=card.id,
        oracle_id=card.oracle_id,
        name_en=card.name_en,
        name_pt=card.name_pt,
        mana_cost=card.mana_cost,
        image_url=card.image_url,
        type_line=card.type_line,
        color_identity=list(card.color_identity),
        is_basic=card.is_basic,
    )
