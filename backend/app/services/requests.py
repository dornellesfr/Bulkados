from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from app.core.errors import DomainError
from app.domain.enums import (
    OPEN_REQUEST_STATUSES,
    CopyState,
    DeckRole,
    RequestSource,
    RequestStatus,
)
from app.models.catalog import CatalogCard
from app.models.copy import CardCopy, CardCopyGroup
from app.models.deck import Deck, DeckCard
from app.models.request import CardRequest
from app.models.user import User
from app.schemas.copies import PersonRef
from app.schemas.requests import (
    CatalogName,
    DeckBrief,
    HandoffBring,
    HandoffLists,
    HandoffReceive,
    RequestCreate,
    RequestRead,
)
from app.services.access import (
    accepted_group_ids,
    require_accepted_group,
    require_deck_owner,
)
from app.services.copy_state import (
    is_linked,
    lock_copy,
    mark_available,
    release_after_requester_cancel,
    sync_holder_groups,
)
from app.services.deck_identity import ensure_commander_seat, ensure_fits_identity


async def create_request(
    session: AsyncSession,
    user: User,
    deck_id: UUID,
    body: RequestCreate,
) -> RequestRead:
    deck = await require_deck_owner(session, deck_id, user.id)
    copy = await lock_copy(session, body.card_copy_id)
    if copy is None:
        raise DomainError(404, "Não encontramos essa carta.")
    card = await session.get(CatalogCard, copy.catalog_card_id)
    if card is None:
        raise DomainError(404, "Não encontramos essa carta no catálogo.")
    group_id = await _request_group(session, user, copy, body.group_id)
    if body.as_commander:
        await ensure_commander_seat(session, deck, copy, card)
    else:
        await ensure_fits_identity(session, deck, card)
    if copy.state is CopyState.available:
        if copy.holder_id == user.id:
            raise DomainError(409, "Essa carta já está na sua casa.")
        request = CardRequest(
            card_copy_id=copy.id,
            group_id=group_id,
            requester_id=user.id,
            holder_id=copy.holder_id,
            source=RequestSource.bulk,
            source_deck_id=None,
            target_deck_id=deck.id,
            as_commander=body.as_commander,
            status=RequestStatus.pending_acceptance,
        )
        copy.state = CopyState.reserved
        copy.locked = True
    elif copy.state is CopyState.in_deck:
        if copy.locked or copy.deck_id is None:
            raise DomainError(409, "Essa carta não está mais disponível.")
        source = await session.get(Deck, copy.deck_id)
        if source is None or source.owner_id == user.id:
            raise DomainError(409, "Essa carta não está mais disponível.")
        request = CardRequest(
            card_copy_id=copy.id,
            group_id=group_id,
            requester_id=user.id,
            holder_id=copy.holder_id,
            source=RequestSource.deck,
            source_deck_id=source.id,
            target_deck_id=deck.id,
            as_commander=body.as_commander,
            status=RequestStatus.pending_acceptance,
        )
        copy.state = CopyState.reserved
        copy.locked = True
    else:
        raise DomainError(409, "Essa carta não está mais disponível.")
    try:
        async with session.begin_nested():
            session.add(request)
            await session.flush()
    except IntegrityError as exc:
        raise DomainError(409, "Essa carta já tem um pedido em aberto.") from exc
    return await _read(session, request.id)


async def accept_request(session: AsyncSession, user: User, request_id: UUID) -> RequestRead:
    request = await _get_request(session, request_id)
    copy = await lock_copy(session, request.card_copy_id)
    if copy is None:
        raise DomainError(404, "Não encontramos essa carta.")
    await _authorize_decision(session, user, request, copy)
    if request.status is not RequestStatus.pending_acceptance:
        raise DomainError(409, "Esse pedido não pode ser aceito.")
    request.status = RequestStatus.awaiting_handoff
    return await _read(session, request.id)


async def reject_request(session: AsyncSession, user: User, request_id: UUID) -> RequestRead:
    request = await _get_request(session, request_id)
    copy = await lock_copy(session, request.card_copy_id)
    if copy is None:
        raise DomainError(404, "Não encontramos essa carta.")
    await _authorize_decision(session, user, request, copy)
    if request.status is not RequestStatus.pending_acceptance:
        raise DomainError(409, "Esse pedido não pode ser recusado.")
    request.status = RequestStatus.rejected
    request.resolved_at = datetime.now(UTC)
    if request.source is RequestSource.bulk:
        mark_available(copy)
    else:
        if request.source_deck_id is None:
            raise DomainError(409, "Esse pedido perdeu o deck de origem.")
        copy.state = CopyState.in_deck
        copy.locked = False
        copy.deck_id = request.source_deck_id
        existing = await session.get(DeckCard, copy.id)
        if existing is None:
            session.add(
                DeckCard(
                    deck_id=request.source_deck_id,
                    card_copy_id=copy.id,
                    role=DeckRole.main,
                )
            )
    return await _read(session, request.id)


async def cancel_request(session: AsyncSession, user: User, request_id: UUID) -> RequestRead:
    request = await _get_request(session, request_id)
    if request.requester_id != user.id:
        raise DomainError(403, "Só quem pediu pode cancelar.")
    if request.status not in OPEN_REQUEST_STATUSES:
        raise DomainError(409, "Esse pedido não pode ser cancelado.")
    copy = await lock_copy(session, request.card_copy_id)
    if copy is None:
        raise DomainError(404, "Não encontramos essa carta.")
    await release_after_requester_cancel(session, copy, request)
    return await _read(session, request.id)


async def confirm_request(session: AsyncSession, user: User, request_id: UUID) -> RequestRead:
    """Cada lado confirma no encontro. A carta só muda de mão quando os dois confirmam."""
    request = await _get_request(session, request_id)
    if request.status is not RequestStatus.awaiting_handoff:
        raise DomainError(409, "Esse pedido não pode ser confirmado.")
    if user.id not in {request.requester_id, request.holder_id}:
        raise DomainError(403, "Só quem pediu ou quem está com a carta pode confirmar.")
    copy = await lock_copy(session, request.card_copy_id)
    if copy is None:
        raise DomainError(404, "Não encontramos essa carta.")
    now = datetime.now(UTC)
    if user.id == request.requester_id and request.requester_confirmed_at is None:
        request.requester_confirmed_at = now
    if user.id == request.holder_id and request.holder_confirmed_at is None:
        request.holder_confirmed_at = now
    if request.requester_confirmed_at is not None and request.holder_confirmed_at is not None:
        await _complete_request(session, request, copy)
    return await _read(session, request.id)


async def handoffs(session: AsyncSession, user: User, group_id: UUID) -> HandoffLists:
    await require_accepted_group(session, group_id, user.id)
    to_bring = await _bring_list(session, user, group_id)
    to_receive = await _list(
        session,
        group_id,
        requester_id=user.id,
        statuses=set(OPEN_REQUEST_STATUSES),
    )
    return HandoffLists(
        to_bring=[
            HandoffBring(
                id=item.id,
                source=item.source,
                catalog=CatalogName(name_en=item.name_en, name_pt=item.name_pt),
                status=item.status,
                requester=PersonRef(
                    id=item.requester_id,
                    email=item.requester_email,
                    first_name=item.requester_first_name,
                    last_name=item.requester_last_name,
                ),
                holder=PersonRef(
                    id=item.holder_id,
                    email=item.holder_email,
                    first_name=item.holder_first_name,
                    last_name=item.holder_last_name,
                ),
                target_deck=DeckBrief(id=item.target_deck_id, name=item.target_deck_name),
                requester_confirmed=item.requester_confirmed,
                holder_confirmed=item.holder_confirmed,
            )
            for item in to_bring
        ],
        to_receive=[
            HandoffReceive(
                id=item.id,
                source=item.source,
                catalog=CatalogName(name_en=item.name_en, name_pt=item.name_pt),
                status=item.status,
                holder=PersonRef(
                    id=item.holder_id,
                    email=item.holder_email,
                    first_name=item.holder_first_name,
                    last_name=item.holder_last_name,
                ),
                target_deck=DeckBrief(id=item.target_deck_id, name=item.target_deck_name),
                requester_confirmed=item.requester_confirmed,
                holder_confirmed=item.holder_confirmed,
            )
            for item in to_receive
        ],
    )


async def _request_group(
    session: AsyncSession,
    user: User,
    copy: CardCopy,
    requested: UUID | None,
) -> UUID:
    if requested is not None:
        await require_accepted_group(session, requested, user.id)
        if not await is_linked(session, copy.id, requested):
            raise DomainError(404, "Não encontramos essa carta nesse grupo.")
        return requested
    linked = set(
        await session.scalars(
            select(CardCopyGroup.group_id).where(CardCopyGroup.card_copy_id == copy.id)
        )
    )
    accepted = set(await accepted_group_ids(session, user.id))
    candidates = sorted(linked & accepted, key=str)
    if not candidates:
        raise DomainError(404, "Não encontramos essa carta num grupo seu.")
    return candidates[0]


async def _authorize_decision(
    session: AsyncSession,
    user: User,
    request: CardRequest,
    copy: CardCopy,
) -> None:
    if request.source is RequestSource.bulk:
        if copy.holder_id != user.id:
            raise DomainError(403, "Só quem está com a carta pode decidir este pedido.")
        return
    if request.source_deck_id is None:
        raise DomainError(409, "Esse pedido perdeu o deck de origem.")
    source = await session.get(Deck, request.source_deck_id)
    if source is None or source.owner_id != user.id:
        raise DomainError(403, "Só o dono do deck de origem pode decidir este pedido.")


async def _complete_request(
    session: AsyncSession,
    request: CardRequest,
    copy: CardCopy,
) -> None:
    target = await session.get(Deck, request.target_deck_id)
    if target is None or target.owner_id != request.requester_id:
        raise DomainError(409, "O deck de destino não vale mais.")
    card = await session.get(CatalogCard, copy.catalog_card_id)
    if card is None:
        raise DomainError(404, "Não encontramos essa carta no catálogo.")
    if request.as_commander:
        await ensure_commander_seat(session, target, copy, card)
        role = DeckRole.commander
    else:
        await ensure_fits_identity(session, target, card)
        role = DeckRole.main
    row = await session.get(DeckCard, copy.id)
    if row is None:
        session.add(DeckCard(deck_id=target.id, card_copy_id=copy.id, role=role))
    else:
        row.deck_id = target.id
        row.role = role
    copy.holder_id = request.requester_id
    copy.deck_id = target.id
    copy.state = CopyState.in_deck
    copy.locked = False
    await sync_holder_groups(
        session,
        copy.id,
        await accepted_group_ids(session, request.requester_id),
    )
    request.status = RequestStatus.completed
    request.resolved_at = datetime.now(UTC)


async def _get_request(session: AsyncSession, request_id: UUID) -> CardRequest:
    request = await session.get(CardRequest, request_id)
    if request is None:
        raise DomainError(404, "Não encontramos esse pedido.")
    return request


async def _read(session: AsyncSession, request_id: UUID) -> RequestRead:
    rows = await _query(session, CardRequest.id == request_id)
    if not rows:
        raise DomainError(404, "Não encontramos esse pedido.")
    return rows[0]


async def _bring_list(session: AsyncSession, user: User, group_id: UUID) -> list[RequestRead]:
    source_decks = select(Deck.id).where(Deck.owner_id == user.id)
    rows = await _query(
        session,
        CardRequest.group_id == group_id,
        CardRequest.status.in_(tuple(OPEN_REQUEST_STATUSES)),
        ((CardRequest.holder_id == user.id) | CardRequest.source_deck_id.in_(source_decks)),
    )
    return rows


async def _list(
    session: AsyncSession,
    group_id: UUID,
    *,
    holder_id: UUID | None = None,
    requester_id: UUID | None = None,
    statuses: set[RequestStatus],
) -> list[RequestRead]:
    filters: list[ColumnElement[bool]] = [
        CardRequest.group_id == group_id,
        CardRequest.status.in_(tuple(statuses)),
    ]
    if holder_id is not None:
        filters.append(CardRequest.holder_id == holder_id)
    if requester_id is not None:
        filters.append(CardRequest.requester_id == requester_id)
    return await _query(session, *filters)


async def _query(session: AsyncSession, *filters: ColumnElement[bool]) -> list[RequestRead]:
    requester = aliased(User)
    holder = aliased(User)
    statement = (
        select(CardRequest, requester, holder, CatalogCard, Deck)
        .join(requester, requester.id == CardRequest.requester_id)
        .join(holder, holder.id == CardRequest.holder_id)
        .join(CardCopy, CardCopy.id == CardRequest.card_copy_id)
        .join(CatalogCard, CatalogCard.id == CardCopy.catalog_card_id)
        .join(Deck, Deck.id == CardRequest.target_deck_id)
        .where(*filters)
        .order_by(CardRequest.created_at)
    )
    rows = (await session.execute(statement)).all()
    return [
        RequestRead(
            id=request.id,
            card_copy_id=request.card_copy_id,
            group_id=request.group_id,
            requester_id=request.requester_id,
            requester_email=requester_user.email,
            requester_first_name=requester_user.first_name,
            requester_last_name=requester_user.last_name,
            holder_id=request.holder_id,
            holder_email=holder_user.email,
            holder_first_name=holder_user.first_name,
            holder_last_name=holder_user.last_name,
            source=request.source,
            source_deck_id=request.source_deck_id,
            target_deck_id=request.target_deck_id,
            target_deck_name=target.name,
            as_commander=request.as_commander,
            status=request.status,
            requester_confirmed=request.requester_confirmed_at is not None,
            holder_confirmed=request.holder_confirmed_at is not None,
            name_en=card.name_en,
            name_pt=card.name_pt,
            created_at=request.created_at,
            resolved_at=request.resolved_at,
        )
        for request, requester_user, holder_user, card, target in rows
    ]
