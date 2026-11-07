from uuid import UUID, uuid4

from sqlalchemy import and_, delete, func, or_, select
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
from app.domain.enums import OPEN_REQUEST_STATUSES, CopyState, DeckRole
from app.domain.pricing import PriceProvider
from app.domain.search import normalize_search_text
from app.models.catalog import CatalogCard
from app.models.copy import CardCopy, CardCopyGroup
from app.models.deck import Deck, DeckCard
from app.models.request import CardRequest
from app.models.user import User
from app.schemas.copies import CopyRead, PersonRef
from app.schemas.decks import (
    CommandersUpdate,
    DeckBulkUpdate,
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
    lock_copy,
    mark_available,
    open_requests_for,
    remove_deck_card,
)
from app.services.deck_identity import (
    ensure_commander_seat,
    ensure_fits_identity,
)


async def create_deck(
    session: AsyncSession,
    user: User,
    body: DeckCreate,
) -> DeckSummary:
    deck = Deck(owner_id=user.id, name=body.name, format=body.format)
    session.add(deck)
    await session.flush()
    return _summary(deck, [], 0)


async def list_decks(session: AsyncSession, user: User) -> list[DeckSummary]:
    rows = await session.execute(
        select(
            Deck,
            func.count(DeckCard.card_copy_id).over(partition_by=Deck.id).label("card_count"),
            CatalogCard,
        )
        .outerjoin(DeckCard, DeckCard.deck_id == Deck.id)
        .outerjoin(CardCopy, CardCopy.id == DeckCard.card_copy_id)
        .outerjoin(
            CatalogCard,
            and_(
                CatalogCard.id == CardCopy.catalog_card_id,
                DeckCard.role == DeckRole.commander,
            ),
        )
        .where(Deck.owner_id == user.id)
        .order_by(Deck.created_at, CatalogCard.name_en)
    )
    decks: dict[UUID, Deck] = {}
    counts: dict[UUID, int] = {}
    commanders: dict[UUID, list[CatalogCard]] = {}
    for deck, count, card in rows:
        decks.setdefault(deck.id, deck)
        counts[deck.id] = count
        if card is not None:
            commanders.setdefault(deck.id, []).append(card)
    return [
        _summary(deck, commanders.get(deck.id, []), counts.get(deck.id, 0))
        for deck in decks.values()
    ]


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
        raise DomainError(409, "Os comandantes precisam já estar no deck.")
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
    if copy is None:
        raise DomainError(404, "Não encontramos essa carta.")
    if copy.state is not CopyState.available or copy.holder_id != user.id:
        raise DomainError(409, "Essa carta não está mais disponível.")
    card = await _card_of(session, copy)
    if body.as_commander:
        await ensure_commander_seat(session, deck, copy, card)
    else:
        await ensure_fits_identity(session, deck, card)
    copy.state = CopyState.in_deck
    copy.locked = False
    copy.deck_id = deck.id
    session.add(
        DeckCard(
            deck_id=deck.id,
            card_copy_id=copy.id,
            role=DeckRole.commander if body.as_commander else DeckRole.main,
        )
    )
    return await read_copy(session, copy)


async def create_deck_copies(
    session: AsyncSession,
    user: User,
    deck_id: UUID,
    body: DeckCopyCreate,
    prices: PriceProvider,
) -> list[CopyRead]:
    """Põe a carta no deck, sem travar: usa as cópias livres da casa e cadastra o resto."""
    deck = await require_deck_owner(session, deck_id, user.id)
    card = await catalog_card_by_oracle(session, body.oracle_id)
    await ensure_fits_identity(session, deck, card)
    taken = await _free_copies(session, user, deck, card, body.quantity)
    for copy in taken:
        copy.state = CopyState.in_deck
        copy.locked = False
        copy.deck_id = deck.id
        session.add(DeckCard(deck_id=deck.id, card_copy_id=copy.id, role=DeckRole.main))
    reads = [await read_copy(session, copy) for copy in taken]
    missing = body.quantity - len(taken)
    if missing > 0:
        reads.extend(await _register_in_deck(session, user, deck, card, missing, prices))
    return reads


async def replace_deck_cards(
    session: AsyncSession,
    user: User,
    deck_id: UUID,
    body: DeckBulkUpdate,
    prices: PriceProvider,
) -> DeckDetail:
    """Troca a lista do deck pelos nomes enviados, sem tocar em nada se um nome não existir."""
    deck = await require_deck_owner(session, deck_id, user.id)
    wanted = [(item.name.strip(), item.role) for item in body.cards if item.name.strip()]
    resolved = await _resolve_bulk_cards(session, [name for name, _ in wanted])
    unknown = list(dict.fromkeys(name for name, _ in wanted if name not in resolved))
    if unknown:
        raise DomainError(422, f"Não reconhecemos estas cartas: {', '.join(unknown)}.")
    desired = [(resolved[name], role) for name, role in wanted]

    facts = [_card_fact(card, role) for card, role in desired]
    commanders = [fact for fact in facts if fact.role is DeckRole.commander]
    error = commander_set_error(commanders)
    if error is not None:
        raise DomainError(409, error)
    if commanders:
        outside = cards_outside_identity(
            commanders,
            [fact for fact in facts if fact.role is DeckRole.main],
        )
        if outside:
            raise DomainError(409, _outside_identity_message(outside))

    rows = (
        await session.execute(
            select(DeckCard, CardCopy, CatalogCard)
            .join(CardCopy, CardCopy.id == DeckCard.card_copy_id)
            .join(CatalogCard, CatalogCard.id == CardCopy.catalog_card_id)
            .where(DeckCard.deck_id == deck.id)
        )
    ).all()
    existing: dict[UUID, list[tuple[DeckCard, CardCopy, CatalogCard]]] = {}
    for row, copy, card in rows:
        existing.setdefault(card.id, []).append((row, copy, card))
    open_ids: set[UUID] = set()
    if rows:
        open_ids = set(
            await session.scalars(
                select(CardRequest.card_copy_id).where(
                    CardRequest.card_copy_id.in_([copy.id for _, copy, _ in rows]),
                    CardRequest.status.in_(tuple(OPEN_REQUEST_STATUSES)),
                )
            )
        )

    kept: list[tuple[CardCopy | None, CatalogCard, DeckRole]] = []
    for card, role in desired:
        bucket = existing.get(card.id, [])
        bucket.sort(key=lambda item: (item[1].id not in open_ids, item[0].role != role))
        if bucket:
            row, copy, _ = bucket.pop(0)
            row.role = role
            kept.append((copy, card, role))
        else:
            kept.append((None, card, role))

    removed = [item for bucket in existing.values() for item in bucket]
    blocked = [card.name_en for _, existing_copy, card in removed if existing_copy.id in open_ids]
    if blocked:
        names = ", ".join(dict.fromkeys(blocked))
        raise DomainError(
            409,
            f"Estas cartas têm pedido aberto e não podem sair do deck: {names}.",
        )

    for _, existing_copy, _ in removed:
        await remove_deck_card(session, existing_copy.id)
        mark_available(existing_copy)

    for kept_copy, card, role in kept:
        if kept_copy is not None:
            continue
        free = await _free_copies(session, user, deck, card, 1)
        if free:
            [taken] = free
            taken.state = CopyState.in_deck
            taken.locked = False
            taken.deck_id = deck.id
            session.add(DeckCard(deck_id=deck.id, card_copy_id=taken.id, role=role))
        else:
            await _register_in_deck(session, user, deck, card, 1, prices, role)

    await session.flush()
    return await _detail(session, deck)


async def _resolve_bulk_cards(
    session: AsyncSession,
    names: list[str],
) -> dict[str, CatalogCard]:
    keys = {normalize_search_text(name): name for name in names}
    keys.pop("", None)
    if not keys:
        return {}
    rows = await session.scalars(
        select(CatalogCard)
        .where(
            or_(
                CatalogCard.search_en.in_(keys),
                CatalogCard.search_pt.in_(keys),
            )
        )
        .order_by(CatalogCard.name_en)
    )
    found: dict[str, CatalogCard] = {}
    for card in rows:
        for key in (card.search_en, card.search_pt):
            if key is not None and key in keys and key not in found:
                found[key] = card
    return {keys[key]: card for key, card in found.items()}


async def _free_copies(
    session: AsyncSession,
    user: User,
    deck: Deck,
    card: CatalogCard,
    quantity: int,
) -> list[CardCopy]:
    del deck
    rows = await session.scalars(
        select(CardCopy)
        .where(
            CardCopy.catalog_card_id == card.id,
            CardCopy.holder_id == user.id,
            CardCopy.state == CopyState.available,
        )
        .order_by(CardCopy.created_at, CardCopy.id)
        .limit(quantity)
        .with_for_update(skip_locked=True)
    )
    return list(rows)


async def _register_in_deck(
    session: AsyncSession,
    user: User,
    deck: Deck,
    card: CatalogCard,
    quantity: int,
    prices: PriceProvider,
    role: DeckRole = DeckRole.main,
) -> list[CopyRead]:
    group_ids = await accepted_group_ids(session, user.id)
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
            locked=False,
            deck_id=deck.id,
        )
        session.add(copy)
        copies.append(copy)
    await session.flush()
    for copy in copies:
        session.add(DeckCard(deck_id=deck.id, card_copy_id=copy.id, role=role))
        for group_id in group_ids:
            session.add(CardCopyGroup(card_copy_id=copy.id, group_id=group_id))
    linked = sorted(group_ids, key=str)
    return [
        _copy_read(copy, card, user, user, "in_deck", deck, user, None, linked) for copy in copies
    ]


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
        raise DomainError(409, "Essa carta não está neste deck.")
    if await open_requests_for(session, copy.id):
        raise DomainError(409, "Essa carta tem um pedido em aberto.")
    target = await require_deck_owner(session, body.target_deck_id, user.id)
    if target.id == source.id:
        raise DomainError(409, "Essa carta já está neste deck.")
    card = await _card_of(session, copy)
    if body.as_commander:
        await ensure_commander_seat(session, target, copy, card)
    else:
        await ensure_fits_identity(session, target, card)
    row = await session.get(DeckCard, copy.id)
    if row is None:
        raise DomainError(409, "Essa carta não está neste deck.")
    row.deck_id = target.id
    row.role = DeckRole.commander if body.as_commander else DeckRole.main
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
        raise DomainError(409, "Essa carta não está neste deck.")
    if await open_requests_for(session, copy.id):
        raise DomainError(409, "Essa carta tem um pedido em aberto.")
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
        raise DomainError(409, "Essa carta não está neste deck.")
    if await open_requests_for(session, copy.id):
        raise DomainError(409, "Essa carta tem um pedido em aberto.")
    copy.locked = locked
    return await read_copy(session, copy)


def _summary(deck: Deck, commanders: list[CatalogCard], card_count: int) -> DeckSummary:
    identity = (
        canonical_colors(color for card in commanders for color in card.color_identity)
        if commanders
        else None
    )
    return DeckSummary(
        id=deck.id,
        name=deck.name,
        format=deck.format,
        created_at=deck.created_at,
        color_identity=identity,
        color_identity_name=identity_name(identity) if identity is not None else None,
        card_count=card_count,
        commanders=[
            DeckCommanderRef(
                name_en=card.name_en,
                name_pt=card.name_pt,
                image_url=card.image_url,
                can_be_commander=card.can_be_commander,
                partner_kind=card.partner_kind,
                type_line=card.type_line,
                oracle_text=card.oracle_text,
                keywords=list(card.keywords),
            )
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
        raise DomainError(404, "Não encontramos essa carta no catálogo.")
    return card


def _fact(copy: CardCopy, card: CatalogCard, role: DeckRole) -> DeckCardFact:
    return _card_fact(card, role, copy.id, copy.price_cents)


def _card_fact(
    card: CatalogCard,
    role: DeckRole,
    copy_id: UUID | None = None,
    price_cents: int | None = None,
) -> DeckCardFact:
    return DeckCardFact(
        card_copy_id=copy_id or uuid4(),
        name_en=card.name_en,
        price_cents=price_cents,
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
                holder=PersonRef(
                    id=holder.id,
                    email=holder.email,
                    first_name=holder.first_name,
                    last_name=holder.last_name,
                ),
                catalog=DeckCatalogRef(
                    oracle_id=card.oracle_id,
                    name_en=card.name_en,
                    name_pt=card.name_pt,
                    image_url=card.image_url,
                    mana_cost=card.mana_cost,
                    type_line=card.type_line,
                    oracle_text=card.oracle_text,
                    color_identity=list(card.color_identity),
                    is_basic=card.is_basic,
                    keywords=list(card.keywords),
                    can_be_commander=card.can_be_commander,
                    partner_kind=card.partner_kind,
                    commander_legal=card.commander_legal,
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
