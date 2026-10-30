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
from app.models.copy import CardCopy
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
from app.services.access import accepted_group_ids, require_accepted_group, require_deck_owner
from app.services.copy_state import (
    is_linked,
    lock_copy,
    release_after_requester_cancel,
    sync_holder_groups,
)
from app.services.deck_identity import ensure_fits_identity


async def create_request(
    session: AsyncSession,
    user: User,
    deck_id: UUID,
    body: RequestCreate,
) -> RequestRead:
    deck = await require_deck_owner(session, deck_id, user.id)
    copy = await lock_copy(session, body.card_copy_id)
    if copy is None or not await is_linked(session, copy.id, deck.group_id):
        raise DomainError(404, "copy not found")
    card = await session.get(CatalogCard, copy.catalog_card_id)
    if card is None:
        raise DomainError(404, "catalog card not found")
    await ensure_fits_identity(session, deck, card)
    if copy.state is CopyState.available:
        if copy.holder_id == user.id:
            raise DomainError(409, "card copy is not available")
        request = CardRequest(
            card_copy_id=copy.id,
            group_id=deck.group_id,
            requester_id=user.id,
            holder_id=copy.holder_id,
            source=RequestSource.bulk,
            source_deck_id=None,
            target_deck_id=deck.id,
            status=RequestStatus.awaiting_handoff,
        )
        copy.state = CopyState.reserved
        copy.locked = True
    elif copy.state is CopyState.in_deck:
        if copy.locked or copy.deck_id is None:
            raise DomainError(409, "card copy is not available")
        source = await session.get(Deck, copy.deck_id)
        if source is None or source.owner_id == user.id:
            raise DomainError(409, "card copy is not available")
        request = CardRequest(
            card_copy_id=copy.id,
            group_id=deck.group_id,
            requester_id=user.id,
            holder_id=copy.holder_id,
            source=RequestSource.deck,
            source_deck_id=source.id,
            target_deck_id=deck.id,
            status=RequestStatus.pending_acceptance,
        )
        copy.state = CopyState.reserved
        copy.locked = True
    else:
        raise DomainError(409, "card copy is not available")
    try:
        async with session.begin_nested():
            session.add(request)
            await session.flush()
    except IntegrityError as exc:
        raise DomainError(409, "card copy already has an open request") from exc
    return await _read(session, request.id)


async def accept_request(session: AsyncSession, user: User, request_id: UUID) -> RequestRead:
    request, _copy = await _owned_source_request(session, user, request_id)
    if (
        request.status is not RequestStatus.pending_acceptance
        or request.source is not RequestSource.deck
    ):
        raise DomainError(409, "request cannot be accepted")
    request.status = RequestStatus.awaiting_handoff
    return await _read(session, request.id)


async def reject_request(session: AsyncSession, user: User, request_id: UUID) -> RequestRead:
    request, copy = await _owned_source_request(session, user, request_id)
    if (
        request.status is not RequestStatus.pending_acceptance
        or request.source is not RequestSource.deck
    ):
        raise DomainError(409, "request cannot be rejected")
    if request.source_deck_id is None:
        raise DomainError(409, "request is missing its source deck")
    request.status = RequestStatus.rejected
    request.resolved_at = datetime.now(UTC)
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
        raise DomainError(403, "only the requester can cancel")
    if request.status not in OPEN_REQUEST_STATUSES:
        raise DomainError(409, "request cannot be cancelled")
    copy = await lock_copy(session, request.card_copy_id)
    if copy is None:
        raise DomainError(404, "copy not found")
    await release_after_requester_cancel(session, copy, request)
    return await _read(session, request.id)


async def confirm_request(session: AsyncSession, user: User, request_id: UUID) -> RequestRead:
    request = await _get_request(session, request_id)
    if request.requester_id != user.id:
        raise DomainError(403, "only the requester can confirm")
    if request.status is not RequestStatus.awaiting_handoff:
        raise DomainError(409, "request cannot be confirmed")
    target = await session.get(Deck, request.target_deck_id)
    if target is None or target.owner_id != user.id or target.group_id != request.group_id:
        raise DomainError(409, "target deck is no longer valid")
    copy = await lock_copy(session, request.card_copy_id)
    if copy is None:
        raise DomainError(404, "copy not found")
    row = await session.get(DeckCard, copy.id)
    if row is None:
        session.add(DeckCard(deck_id=target.id, card_copy_id=copy.id, role=DeckRole.main))
    else:
        row.deck_id = target.id
        row.role = DeckRole.main
    copy.holder_id = user.id
    copy.deck_id = target.id
    copy.state = CopyState.in_deck
    copy.locked = True
    await sync_holder_groups(session, copy.id, await accepted_group_ids(session, user.id))
    request.status = RequestStatus.completed
    request.resolved_at = datetime.now(UTC)
    return await _read(session, request.id)


async def handoffs(session: AsyncSession, user: User, group_id: UUID) -> HandoffLists:
    await require_accepted_group(session, group_id, user.id)
    to_bring = await _list(
        session,
        group_id,
        holder_id=user.id,
        statuses={RequestStatus.awaiting_handoff},
    )
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
                requester=PersonRef(id=item.requester_id, nick=item.requester_nick),
                target_deck=DeckBrief(id=item.target_deck_id, name=item.target_deck_name),
            )
            for item in to_bring
        ],
        to_receive=[
            HandoffReceive(
                id=item.id,
                source=item.source,
                catalog=CatalogName(name_en=item.name_en, name_pt=item.name_pt),
                status=item.status,
                holder=PersonRef(id=item.holder_id, nick=item.holder_nick),
                target_deck=DeckBrief(id=item.target_deck_id, name=item.target_deck_name),
            )
            for item in to_receive
        ],
    )


async def _owned_source_request(
    session: AsyncSession,
    user: User,
    request_id: UUID,
) -> tuple[CardRequest, CardCopy]:
    request = await _get_request(session, request_id)
    copy = await lock_copy(session, request.card_copy_id)
    if copy is None or request.source_deck_id is None:
        raise DomainError(409, "request cannot be accepted")
    source = await session.get(Deck, request.source_deck_id)
    if source is None or source.owner_id != user.id:
        raise DomainError(403, "only the source deck owner can do this")
    return request, copy


async def _get_request(session: AsyncSession, request_id: UUID) -> CardRequest:
    request = await session.get(CardRequest, request_id)
    if request is None:
        raise DomainError(404, "request not found")
    return request


async def _read(session: AsyncSession, request_id: UUID) -> RequestRead:
    rows = await _query(session, CardRequest.id == request_id)
    if not rows:
        raise DomainError(404, "request not found")
    return rows[0]


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
            requester_nick=requester_user.nick,
            holder_id=request.holder_id,
            holder_nick=holder_user.nick,
            source=request.source,
            source_deck_id=request.source_deck_id,
            target_deck_id=request.target_deck_id,
            target_deck_name=target.name,
            status=request.status,
            name_en=card.name_en,
            name_pt=card.name_pt,
            created_at=request.created_at,
            resolved_at=request.resolved_at,
        )
        for request, requester_user, holder_user, card, target in rows
    ]
