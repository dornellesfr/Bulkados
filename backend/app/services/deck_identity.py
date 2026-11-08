from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.domain.colors import canonical_colors
from app.domain.deck_rules import (
    DeckCardFact,
    cards_outside_identity,
    commander_set_error,
)
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


async def ensure_commander_seat(
    session: AsyncSession,
    deck: Deck,
    copy: CardCopy,
    card: CatalogCard,
) -> None:
    """A carta pode entrar neste deck já na cadeira de comandante?"""
    rows = (
        await session.execute(
            select(DeckCard, CardCopy, CatalogCard)
            .join(CardCopy, CardCopy.id == DeckCard.card_copy_id)
            .join(CatalogCard, CatalogCard.id == CardCopy.catalog_card_id)
            .where(DeckCard.deck_id == deck.id)
        )
    ).all()
    commanders: list[DeckCardFact] = []
    others: list[DeckCardFact] = []
    for row, seated_copy, seated_card in rows:
        if seated_copy.id == copy.id:
            continue
        fact = _fact(seated_copy, seated_card, row.role)
        if row.role is DeckRole.commander:
            commanders.append(fact)
        else:
            others.append(fact)
    chosen = [*commanders, _fact(copy, card, DeckRole.commander)]
    error = commander_set_error(chosen)
    if error is None:
        outside = cards_outside_identity(chosen, others)
        if outside:
            error = _outside_identity_message(outside)
    if error is not None:
        raise DomainError(409, error)


def _fact(copy: CardCopy, card: CatalogCard, role: DeckRole) -> DeckCardFact:
    return DeckCardFact(
        card_copy_id=copy.id,
        name_en=card.name_en,
        price_cents=copy.price_cents,
        is_basic=card.is_basic,
        any_number_allowed=card.any_number_allowed,
        color_identity=tuple(card.color_identity),
        commander_legal=card.commander_legal,
        can_be_commander=card.can_be_commander,
        partner_kind=card.partner_kind,
        oracle_text=card.oracle_text,
        type_line=card.type_line,
        keywords=tuple(card.keywords),
        role=role,
    )


def _outside_identity_message(cards: list[DeckCardFact]) -> str:
    names = sorted({card.name_en for card in cards})
    shown = ", ".join(names[:3])
    rest = len(names) - 3
    suffix = f" e mais {rest}" if rest > 0 else ""
    return f"Há cartas no deck fora da identidade de cor dos comandantes: {shown}{suffix}."
