from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.domain.deck_rules import DeckCardFact, evaluate_deck
from app.domain.enums import CopyState, DeckRole
from app.domain.pricing import PriceProvider
from app.models.catalog import CatalogCard
from app.models.copy import CardCopy, CardCopyGroup
from app.models.deck import Deck, DeckCard
from app.models.request import CardRequest
from app.models.user import User
from app.schemas.copies import CopyRead
from app.schemas.decks import (
    CommandersUpdate,
    DeckCardRead,
    DeckCopyCreate,
    DeckCreate,
    DeckDetail,
    DeckSummary,
    DeckUpdate,
    MoveCard,
    TakeCard,
    WarningRead,
)
from app.services.access import (
    accepted_group_ids,
    is_accepted,
    require_accepted_group,
    require_deck_owner,
    require_deck_reader,
)
from app.services.copies import _catalog_card, _copy_read, quote_price
from app.services.copy_state import (
    cancel_open_requests,
    copies_in_decks,
    is_linked,
    lock_copy,
    mark_available,
    open_requests_for,
    remove_deck_card,
)


async def create_deck(
    session: AsyncSession,
    user: User,
    group_id: UUID,
    body: DeckCreate,
) -> DeckSummary:
    await require_accepted_group(session, group_id, user.id)
    deck = Deck(group_id=group_id, owner_id=user.id, name=body.name, format=body.format)
    session.add(deck)
    await session.flush()
    return _summary(deck)


async def list_decks(session: AsyncSession, user: User, group_id: UUID) -> list[DeckSummary]:
    await require_accepted_group(session, group_id, user.id)
    rows = await session.scalars(
        select(Deck)
        .where(Deck.group_id == group_id, Deck.owner_id == user.id)
        .order_by(Deck.created_at)
    )
    return [_summary(deck) for deck in rows]


async def get_deck(session: AsyncSession, user: User, deck_id: UUID) -> DeckDetail:
    deck = await require_deck_reader(session, deck_id, user.id)
    return await _detail(session, deck)


async def update_deck(
    session: AsyncSession,
    user: User,
    deck_id: UUID,
    body: DeckUpdate,
) -> DeckSummary:
    deck = await require_deck_owner(session, deck_id, user.id)
    if body.name is not None:
        deck.name = body.name
    if body.format is not None:
        deck.format = body.format
    return _summary(deck)


async def delete_deck(session: AsyncSession, user: User, deck_id: UUID) -> None:
    deck = await require_deck_owner(session, deck_id, user.id)
    for copy in await copies_in_decks(session, {deck.id}):
        await cancel_open_requests(session, copy.id)
        await remove_deck_card(session, copy.id)
        mark_available(copy)
    await session.flush()
    await session.execute(
        delete(CardRequest).where(
            or_(CardRequest.target_deck_id == deck.id, CardRequest.source_deck_id == deck.id)
        )
    )
    await session.execute(delete(DeckCard).where(DeckCard.deck_id == deck.id))
    await session.delete(deck)


async def set_commanders(
    session: AsyncSession,
    user: User,
    deck_id: UUID,
    body: CommandersUpdate,
) -> DeckDetail:
    deck = await require_deck_owner(session, deck_id, user.id)
    rows = list(await session.scalars(select(DeckCard).where(DeckCard.deck_id == deck.id)))
    present = {row.card_copy_id for row in rows}
    wanted = set(body.card_copy_ids)
    if not wanted <= present:
        raise DomainError(409, "commander cards must already be in the deck")
    for row in rows:
        row.role = DeckRole.commander if row.card_copy_id in wanted else DeckRole.main
    return await _detail(session, deck)


async def take_copy(
    session: AsyncSession,
    user: User,
    deck_id: UUID,
    body: TakeCard,
) -> CopyRead:
    deck = await require_deck_owner(session, deck_id, user.id)
    copy = await lock_copy(session, body.card_copy_id)
    if copy is None or not await is_linked(session, copy.id, deck.group_id):
        raise DomainError(404, "copy not found")
    if copy.state is not CopyState.available or copy.holder_id != user.id:
        raise DomainError(409, "card copy is not available")
    copy.state = CopyState.in_deck
    copy.locked = True
    copy.deck_id = deck.id
    session.add(DeckCard(deck_id=deck.id, card_copy_id=copy.id, role=DeckRole.main))
    card = await _catalog_card(session, copy.catalog_card_id)
    return _copy_read(copy, card, user, "in_deck", deck, user.nick)


async def create_deck_copies(
    session: AsyncSession,
    user: User,
    deck_id: UUID,
    body: DeckCopyCreate,
    prices: PriceProvider,
) -> list[CopyRead]:
    deck = await require_deck_owner(session, deck_id, user.id)
    card = await _catalog_card(session, body.catalog_card_id)
    group_ids = await accepted_group_ids(session, user.id)
    if deck.group_id not in group_ids:
        group_ids.append(deck.group_id)
    cents, fetched_at = await quote_price(card, prices)
    copies: list[CardCopy] = []
    for _ in range(body.quantity):
        copy = CardCopy(
            catalog_card_id=card.id,
            holder_id=user.id,
            added_by_id=user.id,
            price_cents=cents,
            price_fetched_at=fetched_at,
            state=CopyState.in_deck,
            locked=True,
            deck_id=deck.id,
        )
        session.add(copy)
        copies.append(copy)
    await session.flush()
    for copy in copies:
        session.add(DeckCard(deck_id=deck.id, card_copy_id=copy.id, role=DeckRole.main))
        for group_id in group_ids:
            session.add(CardCopyGroup(card_copy_id=copy.id, group_id=group_id))
    return [_copy_read(copy, card, user, "in_deck", deck, user.nick) for copy in copies]


async def move_copy(
    session: AsyncSession,
    user: User,
    deck_id: UUID,
    card_copy_id: UUID,
    body: MoveCard,
) -> CopyRead:
    source = await require_deck_owner(session, deck_id, user.id)
    copy = await lock_copy(session, card_copy_id)
    if copy is None or copy.deck_id != source.id or copy.state is not CopyState.in_deck:
        raise DomainError(409, "card copy is not in this deck")
    if await open_requests_for(session, copy.id):
        raise DomainError(409, "card copy has an open request")
    target = await require_deck_owner(session, body.target_deck_id, user.id)
    if target.id == source.id:
        raise DomainError(409, "card copy is already in this deck")
    if target.group_id != source.group_id:
        if not await is_accepted(session, target.group_id, copy.holder_id):
            raise DomainError(409, "holder is not a member of the destination group")
        if not await is_linked(session, copy.id, target.group_id):
            session.add(CardCopyGroup(card_copy_id=copy.id, group_id=target.group_id))
    row = await session.get(DeckCard, copy.id)
    if row is None:
        raise DomainError(409, "card copy is not in this deck")
    row.deck_id = target.id
    row.role = DeckRole.main
    copy.deck_id = target.id
    card = await _catalog_card(session, copy.catalog_card_id)
    holder = await session.get(User, copy.holder_id)
    if holder is None:
        raise DomainError(404, "copy not found")
    owner = await session.get(User, target.owner_id)
    return _copy_read(
        copy,
        card,
        holder,
        "in_deck",
        target,
        owner.nick if owner is not None else None,
    )


async def return_copy(
    session: AsyncSession,
    user: User,
    deck_id: UUID,
    card_copy_id: UUID,
) -> CopyRead:
    deck = await require_deck_owner(session, deck_id, user.id)
    copy = await lock_copy(session, card_copy_id)
    if copy is None or copy.deck_id != deck.id or copy.state is not CopyState.in_deck:
        raise DomainError(409, "card copy is not in this deck")
    if await open_requests_for(session, copy.id):
        raise DomainError(409, "card copy has an open request")
    await remove_deck_card(session, copy.id)
    mark_available(copy)
    card = await _catalog_card(session, copy.catalog_card_id)
    holder = await session.get(User, copy.holder_id)
    if holder is None:
        raise DomainError(404, "copy not found")
    return _copy_read(copy, card, holder, "available")


async def set_locked(
    session: AsyncSession,
    user: User,
    deck_id: UUID,
    card_copy_id: UUID,
    *,
    locked: bool,
) -> CopyRead:
    deck = await require_deck_owner(session, deck_id, user.id)
    copy = await lock_copy(session, card_copy_id)
    if copy is None or copy.deck_id != deck.id or copy.state is not CopyState.in_deck:
        raise DomainError(409, "card copy is not in this deck")
    if await open_requests_for(session, copy.id):
        raise DomainError(409, "card copy has an open request")
    copy.locked = locked
    card = await _catalog_card(session, copy.catalog_card_id)
    holder = await session.get(User, copy.holder_id)
    if holder is None:
        raise DomainError(404, "copy not found")
    return _copy_read(copy, card, holder, "in_deck", deck, user.nick)


def _summary(deck: Deck) -> DeckSummary:
    return DeckSummary(
        id=deck.id,
        group_id=deck.group_id,
        name=deck.name,
        format=deck.format,
        created_at=deck.created_at,
    )


async def _detail(session: AsyncSession, deck: Deck) -> DeckDetail:
    rows = (
        await session.execute(
            select(DeckCard, CardCopy, CatalogCard)
            .join(CardCopy, CardCopy.id == DeckCard.card_copy_id)
            .join(CatalogCard, CatalogCard.id == CardCopy.catalog_card_id)
            .where(DeckCard.deck_id == deck.id)
            .order_by(CatalogCard.name_en, CardCopy.id)
        )
    ).all()
    facts: list[DeckCardFact] = []
    cards: list[DeckCardRead] = []
    for row, copy, card in rows:
        facts.append(
            DeckCardFact(
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
                role=row.role,
            )
        )
        cards.append(
            DeckCardRead(
                card_copy_id=copy.id,
                role=row.role,
                name_en=card.name_en,
                name_pt=card.name_pt,
                price_cents=copy.price_cents,
                locked=copy.locked,
                is_basic=card.is_basic,
            )
        )
    evaluation = evaluate_deck(facts, deck.format)
    commanders = [card for card in cards if card.role is DeckRole.commander]
    return DeckDetail(
        id=deck.id,
        group_id=deck.group_id,
        owner_id=deck.owner_id,
        name=deck.name,
        format=deck.format,
        created_at=deck.created_at,
        card_count=evaluation.card_count,
        main_price_cents=evaluation.main_price_cents,
        commander_price_cents=evaluation.commander_price_cents,
        warnings=[
            WarningRead(
                code=warning.code, message=warning.message, card_copy_id=warning.card_copy_id
            )
            for warning in evaluation.warnings
        ],
        cards=cards,
        commanders=commanders,
    )
