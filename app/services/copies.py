import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.errors import DomainError
from app.domain.cards import price_is_free_basic
from app.domain.enums import CopyState
from app.domain.pricing import PriceProvider
from app.models.catalog import CatalogCard
from app.models.copy import CardCopy, CardCopyGroup
from app.models.deck import Deck
from app.models.request import CardRequest
from app.models.user import User
from app.schemas.copies import BulkCopyCreate, CopyRead, CopyVisibility, ShareCopy
from app.services.access import accepted_group_ids, is_accepted, require_accepted_group
from app.services.copy_state import is_linked, lock_copy

logger = logging.getLogger(__name__)


async def create_bulk_copies(
    session: AsyncSession,
    user: User,
    group_id: UUID,
    body: BulkCopyCreate,
    prices: PriceProvider,
) -> list[CopyRead]:
    await require_accepted_group(session, group_id, user.id)
    holder = await _holder(session, user, body.holder_id)
    selected = await _selected_groups(session, user, holder, group_id, body.group_ids)
    card = await _catalog_card(session, body.catalog_card_id)
    cents, fetched_at = await quote_price(card, prices)
    copies: list[CardCopy] = []
    for _ in range(body.quantity):
        copy = CardCopy(
            catalog_card_id=card.id,
            holder_id=holder.id,
            added_by_id=user.id,
            price_cents=cents,
            price_fetched_at=fetched_at,
            state=CopyState.available,
            locked=False,
            deck_id=None,
        )
        session.add(copy)
        copies.append(copy)
    await session.flush()
    for copy in copies:
        for selected_group_id in selected:
            session.add(CardCopyGroup(card_copy_id=copy.id, group_id=selected_group_id))
    return [_copy_read(copy, card, holder, visibility="available") for copy in copies]


async def list_group_copies(
    session: AsyncSession,
    user: User,
    group_id: UUID,
) -> list[CopyRead]:
    await require_accepted_group(session, group_id, user.id)
    holder = aliased(User)
    rows = (
        await session.execute(
            select(CardCopy, CatalogCard, holder)
            .join(CardCopyGroup, CardCopyGroup.card_copy_id == CardCopy.id)
            .join(CatalogCard, CatalogCard.id == CardCopy.catalog_card_id)
            .join(holder, holder.id == CardCopy.holder_id)
            .where(CardCopyGroup.group_id == group_id)
            .order_by(CatalogCard.name_en, CardCopy.id)
        )
    ).all()
    deck_ids = {copy.deck_id for copy, _, _ in rows if copy.deck_id is not None}
    decks_by_id: dict[UUID, Deck] = {}
    owners: dict[UUID, User] = {}
    if deck_ids:
        decks = list(await session.scalars(select(Deck).where(Deck.id.in_(deck_ids))))
        decks_by_id = {deck.id: deck for deck in decks}
        owner_ids = {deck.owner_id for deck in decks}
        owners = {
            owner.id: owner
            for owner in await session.scalars(select(User).where(User.id.in_(owner_ids)))
        }
    visible_groups = set(await accepted_group_ids(session, user.id))
    return [
        _visible_copy(copy, card, holder_user, decks_by_id, owners, visible_groups)
        for copy, card, holder_user in rows
    ]


async def share_copy(
    session: AsyncSession,
    user: User,
    copy_id: UUID,
    body: ShareCopy,
) -> CopyRead:
    copy = await lock_copy(session, copy_id)
    if copy is None:
        raise DomainError(404, "copy not found")
    if copy.holder_id != user.id:
        raise DomainError(403, "only the holder can do this")
    if copy.state is CopyState.reserved:
        raise DomainError(409, "reserved copy cannot be shared")
    if not await is_accepted(session, body.group_id, user.id):
        raise DomainError(404, "group not found")
    if await is_linked(session, copy.id, body.group_id):
        raise DomainError(409, "copy is already in this group")
    session.add(CardCopyGroup(card_copy_id=copy.id, group_id=body.group_id))
    card = await _catalog_card(session, copy.catalog_card_id)
    return await _read_known_copy(session, copy, card, user)


async def remove_copy(session: AsyncSession, user: User, copy_id: UUID) -> None:
    copy = await lock_copy(session, copy_id)
    if copy is None:
        raise DomainError(404, "copy not found")
    if copy.holder_id != user.id:
        raise DomainError(403, "only the holder can do this")
    if copy.state is not CopyState.available:
        raise DomainError(409, "only an available copy can be removed")
    await session.execute(delete(CardRequest).where(CardRequest.card_copy_id == copy.id))
    await session.execute(delete(CardCopyGroup).where(CardCopyGroup.card_copy_id == copy.id))
    await session.delete(copy)


async def refresh_price(
    session: AsyncSession,
    user: User,
    copy_id: UUID,
    prices: PriceProvider,
) -> CopyRead:
    copy = await lock_copy(session, copy_id)
    if copy is None:
        raise DomainError(404, "copy not found")
    if user.id not in {copy.holder_id, copy.added_by_id}:
        raise DomainError(403, "only the holder or whoever added the copy can refresh the price")
    card = await _catalog_card(session, copy.catalog_card_id)
    cents, fetched_at = await quote_price(card, prices)
    copy.price_cents = cents
    copy.price_fetched_at = fetched_at
    holder = await session.get(User, copy.holder_id)
    if holder is None:
        raise DomainError(404, "copy not found")
    return await _read_known_copy(session, copy, card, holder)


async def quote_price(
    card: CatalogCard,
    prices: PriceProvider,
) -> tuple[int | None, datetime | None]:
    now = datetime.now(UTC)
    if price_is_free_basic(card.name_en, card.is_basic):
        return 0, now
    try:
        cents = await prices.lowest_brl_cents(card.name_en)
    except Exception:
        logger.warning("price provider failed for %s", card.name_en)
        return None, None
    if cents is None or cents < 0:
        return None, now
    return cents, now


async def _holder(session: AsyncSession, user: User, holder_id: UUID | None) -> User:
    if holder_id is None or holder_id == user.id:
        return user
    holder = await session.get(User, holder_id)
    if holder is None:
        raise DomainError(404, "holder not found")
    return holder


async def _selected_groups(
    session: AsyncSession,
    user: User,
    holder: User,
    path_group_id: UUID,
    requested: list[UUID] | None,
) -> list[UUID]:
    if requested is None and holder.id == user.id:
        selected = await accepted_group_ids(session, user.id)
    else:
        selected = _dedupe([path_group_id, *(requested or [])])
    if not selected:
        raise DomainError(409, "copy must belong to at least one group")
    for group_id in selected:
        if not await is_accepted(session, group_id, user.id):
            raise DomainError(404, "group not found")
        if holder.id != user.id and not await is_accepted(session, group_id, holder.id):
            raise DomainError(409, "holder is not a member of every selected group")
    return selected


async def _catalog_card(session: AsyncSession, catalog_card_id: UUID) -> CatalogCard:
    card = await session.get(CatalogCard, catalog_card_id)
    if card is None:
        raise DomainError(404, "catalog card not found")
    return card


def _dedupe(group_ids: list[UUID]) -> list[UUID]:
    selected: list[UUID] = []
    for group_id in group_ids:
        if group_id not in selected:
            selected.append(group_id)
    return selected


def _copy_read(
    copy: CardCopy,
    card: CatalogCard,
    holder: User,
    visibility: CopyVisibility,
    deck: Deck | None = None,
    deck_owner_nick: str | None = None,
) -> CopyRead:
    visible_deck = deck if visibility == "in_deck" else None
    return CopyRead(
        id=copy.id,
        catalog_card_id=card.id,
        oracle_id=card.oracle_id,
        name_en=card.name_en,
        name_pt=card.name_pt,
        type_line=card.type_line,
        color_identity=list(card.color_identity),
        is_basic=card.is_basic,
        price_cents=copy.price_cents,
        holder_id=holder.id,
        holder_nick=holder.nick,
        state=copy.state,
        locked=copy.locked,
        visibility=visibility,
        deck_id=visible_deck.id if visible_deck is not None else None,
        deck_name=visible_deck.name if visible_deck is not None else None,
        deck_owner_nick=deck_owner_nick if visible_deck is not None else None,
    )


def _visible_copy(
    copy: CardCopy,
    card: CatalogCard,
    holder: User,
    decks_by_id: dict[UUID, Deck],
    owners: dict[UUID, User],
    visible_groups: set[UUID],
) -> CopyRead:
    deck = decks_by_id.get(copy.deck_id) if copy.deck_id is not None else None
    visibility: CopyVisibility = "available"
    if copy.state is CopyState.available:
        visibility = "available"
    elif copy.state is CopyState.reserved:
        visibility = "reserved"
    elif deck is not None and deck.group_id in visible_groups:
        visibility = "in_deck"
    else:
        visibility = "in_use_elsewhere"
    owner_nick = None
    if deck is not None:
        owner = owners.get(deck.owner_id)
        owner_nick = owner.nick if owner is not None else None
    return _copy_read(copy, card, holder, visibility, deck, owner_nick)


async def _read_known_copy(
    session: AsyncSession,
    copy: CardCopy,
    card: CatalogCard,
    holder: User,
) -> CopyRead:
    deck = await session.get(Deck, copy.deck_id) if copy.deck_id is not None else None
    visibility: CopyVisibility = "available"
    if copy.state is CopyState.available:
        visibility = "available"
    elif copy.state is CopyState.reserved:
        visibility = "reserved"
    else:
        visibility = "in_deck"
    owner_nick = None
    if deck is not None:
        owner = await session.get(User, deck.owner_id)
        owner_nick = owner.nick if owner is not None else None
    return _copy_read(copy, card, holder, visibility, deck, owner_nick)
