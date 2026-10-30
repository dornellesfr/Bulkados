from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.domain.colors import canonical_colors, identity_name
from app.domain.deck_rules import (
    DeckCardFact,
    can_toggle_commander,
    cards_outside_identity,
    commander_set_error,
    evaluate_deck,
)
from app.domain.enums import CopyState, DeckRole
from app.domain.pricing import PriceProvider
from app.models.catalog import CatalogCard
from app.models.copy import CardCopy, CardCopyGroup
from app.models.deck import Deck, DeckCard
from app.models.request import CardRequest
from app.models.user import User
from app.schemas.copies import CopyRead, PersonRef
from app.schemas.decks import (
    CommandersUpdate,
    DeckCardRead,
    DeckCatalogRef,
    DeckCommanderRef,
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
from app.services.copies import (
    _copy_read,
    catalog_card_by_oracle,
    open_request_refs,
    quote_price,
    read_copy,
)
from app.services.copy_state import (
    cancel_open_requests,
    copies_in_decks,
    is_linked,
    lock_copy,
    mark_available,
    open_requests_for,
    remove_deck_card,
)
from app.services.deck_identity import deck_commanders, ensure_fits_identity


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
    return _summary(deck, [])


async def list_decks(session: AsyncSession, user: User, group_id: UUID) -> list[DeckSummary]:
    await require_accepted_group(session, group_id, user.id)
    rows = await session.scalars(
        select(Deck)
        .where(Deck.group_id == group_id, Deck.owner_id == user.id)
        .order_by(Deck.created_at)
    )
    decks = list(rows)
    commanders = await deck_commanders(session, [deck.id for deck in decks])
    return [_summary(deck, commanders.get(deck.id, [])) for deck in decks]


async def get_deck(session: AsyncSession, user: User, deck_id: UUID) -> DeckDetail:
    deck = await require_deck_reader(session, deck_id, user.id)
    return await _detail(session, deck)


async def update_deck(
    session: AsyncSession,
    user: User,
    deck_id: UUID,
    body: DeckUpdate,
) -> DeckDetail:
    deck = await require_deck_owner(session, deck_id, user.id)
    if body.name is not None:
        deck.name = body.name
    if body.format is not None:
        deck.format = body.format
    return await _detail(session, deck)


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
    cards = (
        await session.execute(
            select(CardCopy, CatalogCard)
            .join(CatalogCard, CatalogCard.id == CardCopy.catalog_card_id)
            .where(CardCopy.id.in_(present))
        )
    ).all()
    chosen = [_fact(copy, card, DeckRole.commander) for copy, card in cards if copy.id in wanted]
    others = [_fact(copy, card, DeckRole.main) for copy, card in cards if copy.id not in wanted]
    error = commander_set_error(chosen)
    if error is None and chosen:
        outside = cards_outside_identity(chosen, others)
        if outside:
            error = _outside_identity_message(outside)
    if error is not None:
        raise DomainError(409, error)
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
    await ensure_fits_identity(session, deck, await _card_of(session, copy))
    copy.state = CopyState.in_deck
    copy.locked = True
    copy.deck_id = deck.id
    session.add(DeckCard(deck_id=deck.id, card_copy_id=copy.id, role=DeckRole.main))
    return await read_copy(session, copy)


async def create_deck_copies(
    session: AsyncSession,
    user: User,
    deck_id: UUID,
    body: DeckCopyCreate,
    prices: PriceProvider,
) -> list[CopyRead]:
    """Põe a carta no deck: trava as cópias livres da casa do usuário e cadastra o resto."""
    deck = await require_deck_owner(session, deck_id, user.id)
    card = await catalog_card_by_oracle(session, body.oracle_id)
    await ensure_fits_identity(session, deck, card)
    taken = await _free_copies(session, user, deck, card, body.quantity)
    for copy in taken:
        copy.state = CopyState.in_deck
        copy.locked = True
        copy.deck_id = deck.id
        session.add(DeckCard(deck_id=deck.id, card_copy_id=copy.id, role=DeckRole.main))
    reads = [await read_copy(session, copy) for copy in taken]
    missing = body.quantity - len(taken)
    if missing > 0:
        reads.extend(await _register_in_deck(session, user, deck, card, missing, prices))
    return reads


async def _free_copies(
    session: AsyncSession,
    user: User,
    deck: Deck,
    card: CatalogCard,
    quantity: int,
) -> list[CardCopy]:
    rows = await session.scalars(
        select(CardCopy)
        .join(CardCopyGroup, CardCopyGroup.card_copy_id == CardCopy.id)
        .where(
            CardCopy.catalog_card_id == card.id,
            CardCopy.holder_id == user.id,
            CardCopy.state == CopyState.available,
            CardCopyGroup.group_id == deck.group_id,
        )
        .order_by(CardCopy.created_at, CardCopy.id)
        .limit(quantity)
        .with_for_update(of=CardCopy, skip_locked=True)
    )
    return list(rows)


async def _register_in_deck(
    session: AsyncSession,
    user: User,
    deck: Deck,
    card: CatalogCard,
    quantity: int,
    prices: PriceProvider,
) -> list[CopyRead]:
    group_ids = await accepted_group_ids(session, user.id)
    if deck.group_id not in group_ids:
        group_ids.append(deck.group_id)
    cents, fetched_at = await quote_price(card, prices)
    copies: list[CardCopy] = []
    for _ in range(quantity):
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
    return [_copy_read(copy, card, user, user, "in_deck", deck, user) for copy in copies]


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
    await ensure_fits_identity(session, target, await _card_of(session, copy))
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
    return await read_copy(session, copy)


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
    return await read_copy(session, copy)


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
    return await read_copy(session, copy)


def _summary(deck: Deck, commanders: list[CatalogCard]) -> DeckSummary:
    identity = (
        canonical_colors(color for card in commanders for color in card.color_identity)
        if commanders
        else None
    )
    return DeckSummary(
        id=deck.id,
        group_id=deck.group_id,
        name=deck.name,
        format=deck.format,
        created_at=deck.created_at,
        color_identity=identity,
        color_identity_name=identity_name(identity) if identity is not None else None,
        commanders=[
            DeckCommanderRef(name_en=card.name_en, name_pt=card.name_pt, image_url=card.image_url)
            for card in commanders
        ],
    )


def _outside_identity_message(cards: list[DeckCardFact]) -> str:
    names = sorted({card.name_en for card in cards})
    shown = ", ".join(names[:3])
    rest = len(names) - 3
    suffix = f" e mais {rest}" if rest > 0 else ""
    return f"Há cartas no deck fora da identidade de cor dos comandantes: {shown}{suffix}."


async def _card_of(session: AsyncSession, copy: CardCopy) -> CatalogCard:
    card = await session.get(CatalogCard, copy.catalog_card_id)
    if card is None:
        raise DomainError(404, "catalog card not found")
    return card


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


async def _detail(session: AsyncSession, deck: Deck) -> DeckDetail:
    rows = (
        await session.execute(
            select(DeckCard, CardCopy, CatalogCard, User)
            .join(CardCopy, CardCopy.id == DeckCard.card_copy_id)
            .join(CatalogCard, CatalogCard.id == CardCopy.catalog_card_id)
            .join(User, User.id == CardCopy.holder_id)
            .where(DeckCard.deck_id == deck.id)
            .order_by(CatalogCard.name_en, CardCopy.id)
        )
    ).all()
    open_requests = await open_request_refs(session, [copy.id for _, copy, _, _ in rows])
    facts = [_fact(copy, card, row.role) for row, copy, card, _ in rows]
    cards: list[DeckCardRead] = []
    for (row, copy, card, holder), fact in zip(rows, facts, strict=True):
        cards.append(
            DeckCardRead(
                card_copy_id=copy.id,
                role=row.role,
                locked=copy.locked,
                price_cents=copy.price_cents,
                holder=PersonRef(id=holder.id, nick=holder.nick),
                catalog=DeckCatalogRef(
                    oracle_id=card.oracle_id,
                    name_en=card.name_en,
                    name_pt=card.name_pt,
                    image_url=card.image_url,
                    mana_cost=card.mana_cost,
                    type_line=card.type_line,
                    color_identity=list(card.color_identity),
                    is_basic=card.is_basic,
                    commander_legal=card.commander_legal,
                    can_be_commander=card.can_be_commander,
                    partner_kind=card.partner_kind,
                ),
                open_request=open_requests.get(copy.id),
                can_toggle_commander=can_toggle_commander(fact, facts),
            )
        )
    evaluation = evaluate_deck(facts, deck.format)
    commanders = [card for card in cards if card.role is DeckRole.commander]
    identity = (
        canonical_colors(
            color
            for fact in facts
            if fact.role is DeckRole.commander
            for color in fact.color_identity
        )
        if commanders
        else None
    )
    return DeckDetail(
        id=deck.id,
        group_id=deck.group_id,
        owner_id=deck.owner_id,
        name=deck.name,
        format=deck.format,
        created_at=deck.created_at,
        color_identity=identity,
        color_identity_name=identity_name(identity) if identity is not None else None,
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
