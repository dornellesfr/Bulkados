import logging
from collections.abc import Iterable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.errors import DomainError
from app.domain.cards import price_is_free_basic
from app.domain.enums import OPEN_REQUEST_STATUSES, CopyState
from app.domain.pricing import PriceProvider
from app.models.catalog import CatalogCard
from app.models.copy import CardCopy, CardCopyGroup
from app.models.deck import Deck
from app.models.request import CardRequest
from app.models.user import User
from app.schemas.copies import (
    BulkCopyCreate,
    CatalogRef,
    CopyDeckRef,
    CopyRead,
    CopyVisibility,
    OpenRequestRef,
    PersonRef,
    ShareCopy,
)
from app.services.access import (
    accepted_group_ids,
    group_ids_by_user,
    is_accepted,
    require_accepted_group,
)
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
    card = await catalog_card_by_oracle(session, body.oracle_id)
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
    linked = sorted(selected, key=str)
    return [_copy_read(copy, card, holder, user, "available", group_ids=linked) for copy in copies]


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
    owner_groups = await group_ids_by_user(session, {owner.id for owner in owners.values()})
    added_by = await _users_by_id(session, {copy.added_by_id for copy, _, _ in rows})
    copy_ids = [copy.id for copy, _, _ in rows]
    open_requests = await open_request_refs(session, copy_ids)
    groups_by_copy = await _group_ids_by_copy(session, copy_ids)
    return [
        _visible_copy(
            copy,
            card,
            holder_user,
            added_by[copy.added_by_id],
            decks_by_id,
            owners,
            visible_groups,
            owner_groups,
            open_requests.get(copy.id),
            groups_by_copy.get(copy.id, []),
        )
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
        raise DomainError(404, "Não encontramos essa carta.")
    if copy.holder_id != user.id:
        raise DomainError(403, "Só quem está com a carta pode fazer isso.")
    if copy.state is CopyState.reserved:
        raise DomainError(409, "Carta reservada não pode ser compartilhada.")
    if not await is_accepted(session, body.group_id, user.id):
        raise DomainError(404, "Não encontramos esse grupo.")
    if await is_linked(session, copy.id, body.group_id):
        raise DomainError(409, "Essa carta já está neste grupo.")
    session.add(CardCopyGroup(card_copy_id=copy.id, group_id=body.group_id))
    return await read_copy(session, copy)


async def unlink_copy(
    session: AsyncSession,
    user: User,
    copy_id: UUID,
    group_id: UUID,
) -> CopyRead:
    copy = await lock_copy(session, copy_id)
    if copy is None:
        raise DomainError(404, "Não encontramos essa carta.")
    if copy.holder_id != user.id:
        raise DomainError(403, "Só quem está com a carta pode fazer isso.")
    if copy.state is CopyState.reserved:
        raise DomainError(409, "Carta reservada não pode mudar de grupo.")
    if copy.state is not CopyState.available:
        raise DomainError(
            409,
            "Essa carta está num deck. Devolva ao bulk antes de tirar o vínculo.",
        )
    if not await is_accepted(session, group_id, user.id):
        raise DomainError(404, "Não encontramos esse grupo.")
    if not await is_linked(session, copy.id, group_id):
        raise DomainError(404, "Essa carta não está neste grupo.")
    linked = await _group_ids_by_copy(session, [copy.id])
    if len(linked.get(copy.id, [])) <= 1:
        raise DomainError(409, "A carta precisa ficar em pelo menos um grupo.")
    await session.execute(
        delete(CardCopyGroup).where(
            CardCopyGroup.card_copy_id == copy.id,
            CardCopyGroup.group_id == group_id,
        )
    )
    return await read_copy(session, copy)


async def remove_copy(session: AsyncSession, user: User, copy_id: UUID) -> None:
    copy = await lock_copy(session, copy_id)
    if copy is None:
        raise DomainError(404, "Não encontramos essa carta.")
    if copy.holder_id != user.id:
        raise DomainError(403, "Só quem está com a carta pode fazer isso.")
    if copy.state is not CopyState.available:
        raise DomainError(409, "Só uma carta livre pode sair do grupo.")
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
        raise DomainError(404, "Não encontramos essa carta.")
    if user.id not in {copy.holder_id, copy.added_by_id}:
        raise DomainError(403, "Só quem está com a carta ou quem cadastrou pode atualizar o preço.")
    card = await _catalog_card(session, copy.catalog_card_id)
    cents, fetched_at = await quote_price(card, prices)
    copy.price_cents = cents
    copy.price_fetched_at = fetched_at
    return await read_copy(session, copy)


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
        raise DomainError(404, "Não encontramos essa pessoa no grupo.")
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
    elif requested is None:
        selected = [path_group_id]
    else:
        selected = _dedupe(requested)
    if not selected:
        raise DomainError(409, "A carta precisa ficar em pelo menos um grupo.")
    for group_id in selected:
        if not await is_accepted(session, group_id, user.id):
            raise DomainError(404, "Não encontramos esse grupo.")
        if holder.id != user.id and not await is_accepted(session, group_id, holder.id):
            raise DomainError(
                409,
                "A casa da carta precisa participar de todos os grupos escolhidos.",
            )
    return selected


async def _catalog_card(session: AsyncSession, catalog_card_id: UUID) -> CatalogCard:
    card = await session.get(CatalogCard, catalog_card_id)
    if card is None:
        raise DomainError(404, "Não encontramos essa carta no catálogo.")
    return card


async def catalog_card_by_oracle(session: AsyncSession, oracle_id: UUID) -> CatalogCard:
    card = await session.scalar(select(CatalogCard).where(CatalogCard.oracle_id == oracle_id))
    if card is None:
        raise DomainError(404, "Não encontramos essa carta no catálogo.")
    return card


async def _user(session: AsyncSession, user_id: UUID) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise DomainError(404, "Não encontramos essa carta.")
    return user


async def _users_by_id(session: AsyncSession, user_ids: Iterable[UUID]) -> dict[UUID, User]:
    wanted = set(user_ids)
    if not wanted:
        return {}
    return {
        user.id: user for user in await session.scalars(select(User).where(User.id.in_(wanted)))
    }


async def open_request_refs(
    session: AsyncSession,
    copy_ids: Iterable[UUID],
) -> dict[UUID, OpenRequestRef]:
    wanted = set(copy_ids)
    if not wanted:
        return {}
    rows = await session.execute(
        select(CardRequest, User)
        .join(User, User.id == CardRequest.requester_id)
        .where(
            CardRequest.card_copy_id.in_(wanted),
            CardRequest.status.in_(OPEN_REQUEST_STATUSES),
        )
    )
    return {
        request.card_copy_id: OpenRequestRef(
            id=request.id,
            status=request.status,
            source=request.source,
            requester=_person(requester),
        )
        for request, requester in rows.all()
    }


async def read_copy(session: AsyncSession, copy: CardCopy) -> CopyRead:
    """Monta a cópia lida por quem age sobre ela (a casa, o dono do deck ou quem cadastrou)."""
    card = await _catalog_card(session, copy.catalog_card_id)
    holder = await _user(session, copy.holder_id)
    added_by = await _user(session, copy.added_by_id)
    deck = await session.get(Deck, copy.deck_id) if copy.deck_id is not None else None
    owner = await _user(session, deck.owner_id) if deck is not None else None
    open_request = (await open_request_refs(session, [copy.id])).get(copy.id)
    group_ids = (await _group_ids_by_copy(session, [copy.id])).get(copy.id, [])
    visibility: CopyVisibility = "in_deck"
    if copy.state is CopyState.available:
        visibility = "available"
    elif copy.state is CopyState.reserved:
        visibility = "reserved"
    return _copy_read(
        copy,
        card,
        holder,
        added_by,
        visibility,
        deck,
        owner,
        open_request,
        group_ids,
    )


async def _group_ids_by_copy(
    session: AsyncSession,
    copy_ids: Iterable[UUID],
) -> dict[UUID, list[UUID]]:
    ids = list(copy_ids)
    grouped: dict[UUID, list[UUID]] = {copy_id: [] for copy_id in ids}
    if not ids:
        return grouped
    rows = await session.execute(
        select(CardCopyGroup.card_copy_id, CardCopyGroup.group_id)
        .where(CardCopyGroup.card_copy_id.in_(ids))
        .order_by(CardCopyGroup.group_id)
    )
    for copy_id, group_id in rows:
        grouped.setdefault(copy_id, []).append(group_id)
    return grouped


def _dedupe(group_ids: list[UUID]) -> list[UUID]:
    selected: list[UUID] = []
    for group_id in group_ids:
        if group_id not in selected:
            selected.append(group_id)
    return selected


def _person(user: User) -> PersonRef:
    return PersonRef(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
    )


def _copy_read(
    copy: CardCopy,
    card: CatalogCard,
    holder: User,
    added_by: User,
    visibility: CopyVisibility,
    deck: Deck | None = None,
    deck_owner: User | None = None,
    open_request: OpenRequestRef | None = None,
    group_ids: list[UUID] | None = None,
) -> CopyRead:
    visible_deck = None
    if visibility == "in_deck" and deck is not None and deck_owner is not None:
        visible_deck = CopyDeckRef(id=deck.id, name=deck.name, owner=_person(deck_owner))
    return CopyRead(
        id=copy.id,
        catalog=CatalogRef(
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
        ),
        holder=_person(holder),
        added_by=_person(added_by),
        price_cents=copy.price_cents,
        price_fetched_at=copy.price_fetched_at,
        state=copy.state,
        locked=copy.locked,
        visibility=visibility,
        deck=visible_deck,
        open_request=open_request,
        group_ids=list(group_ids or []),
    )


def _visible_copy(
    copy: CardCopy,
    card: CatalogCard,
    holder: User,
    added_by: User,
    decks_by_id: dict[UUID, Deck],
    owners: dict[UUID, User],
    visible_groups: set[UUID],
    owner_groups: dict[UUID, set[UUID]],
    open_request: OpenRequestRef | None,
    group_ids: list[UUID],
) -> CopyRead:
    deck = decks_by_id.get(copy.deck_id) if copy.deck_id is not None else None
    visibility: CopyVisibility = "available"
    if copy.state is CopyState.available:
        visibility = "available"
    elif copy.state is CopyState.reserved:
        visibility = "reserved"
    elif deck is not None and owner_groups.get(deck.owner_id, set()) & visible_groups:
        visibility = "in_deck"
    else:
        visibility = "in_use_elsewhere"
    owner = owners.get(deck.owner_id) if deck is not None else None
    return _copy_read(
        copy,
        card,
        holder,
        added_by,
        visibility,
        deck,
        owner,
        open_request,
        group_ids,
    )
