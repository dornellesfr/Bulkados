from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.domain.colors import canonical_colors
from app.domain.enums import DeckRole
from app.models.catalog import CatalogCard
from app.models.copy import CardCopy
from app.models.deck import Deck, DeckCard


async def deck_commanders(
    session: AsyncSession,
    deck_ids: Iterable[UUID],
) -> dict[UUID, list[CatalogCard]]:
    """As cartas que são comandante de cada deck, em ordem de nome."""
    wanted = set(deck_ids)
    if not wanted:
        return {}
    rows = await session.execute(
        select(DeckCard.deck_id, CatalogCard)
        .join(CardCopy, CardCopy.id == DeckCard.card_copy_id)
        .join(CatalogCard, CatalogCard.id == CardCopy.catalog_card_id)
        .where(DeckCard.deck_id.in_(wanted), DeckCard.role == DeckRole.commander)
        .order_by(CatalogCard.name_en)
    )
    found: dict[UUID, list[CatalogCard]] = {}
    for deck_id, card in rows.all():
        found.setdefault(deck_id, []).append(card)
    return found


async def deck_identities(
    session: AsyncSession,
    deck_ids: Iterable[UUID],
) -> dict[UUID, list[str]]:
    """Identidade de cor dos decks que têm comandante: a união das cores dos comandantes."""
    wanted = set(deck_ids)
    if not wanted:
        return {}
    rows = await session.execute(
        select(DeckCard.deck_id, CatalogCard.color_identity)
        .join(CardCopy, CardCopy.id == DeckCard.card_copy_id)
        .join(CatalogCard, CatalogCard.id == CardCopy.catalog_card_id)
        .where(DeckCard.deck_id.in_(wanted), DeckCard.role == DeckRole.commander)
    )
    colors: dict[UUID, set[str]] = {}
    for deck_id, identity in rows.all():
        colors.setdefault(deck_id, set()).update(identity)
    return {deck_id: canonical_colors(found) for deck_id, found in colors.items()}


async def ensure_fits_identity(session: AsyncSession, deck: Deck, card: CatalogCard) -> None:
    """Recusa a carta cuja identidade de cor sai da do deck. Sem comandante, não há limite."""
    identity = (await deck_identities(session, [deck.id])).get(deck.id)
    if identity is None:
        return
    if not {color.upper() for color in card.color_identity} <= set(identity):
        raise DomainError(409, "A identidade de cor da carta não cabe na identidade do deck.")
