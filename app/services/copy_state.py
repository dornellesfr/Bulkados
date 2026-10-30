from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.domain.enums import (
    OPEN_REQUEST_STATUSES,
    CopyState,
    DeckRole,
    RequestSource,
    RequestStatus,
)
from app.models.copy import CardCopy, CardCopyGroup
from app.models.deck import DeckCard
from app.models.request import CardRequest


async def lock_copy(session: AsyncSession, copy_id: UUID) -> CardCopy | None:
    result = await session.execute(select(CardCopy).where(CardCopy.id == copy_id).with_for_update())
    return result.scalar_one_or_none()


async def open_requests_for(session: AsyncSession, copy_id: UUID) -> list[CardRequest]:
    rows = await session.scalars(
        select(CardRequest).where(
            CardRequest.card_copy_id == copy_id,
            CardRequest.status.in_(OPEN_REQUEST_STATUSES),
        )
    )
    return list(rows)


async def is_linked(session: AsyncSession, copy_id: UUID, group_id: UUID) -> bool:
    link = await session.scalar(
        select(CardCopyGroup.card_copy_id).where(
            CardCopyGroup.card_copy_id == copy_id,
            CardCopyGroup.group_id == group_id,
        )
    )
    return link is not None


def mark_available(copy: CardCopy) -> None:
    copy.state = CopyState.available
    copy.locked = False
    copy.deck_id = None


def cancel_row(request: CardRequest) -> None:
    request.status = RequestStatus.cancelled
    request.resolved_at = datetime.now(UTC)


async def remove_deck_card(session: AsyncSession, copy_id: UUID) -> None:
    await session.execute(delete(DeckCard).where(DeckCard.card_copy_id == copy_id))


async def cancel_open_requests(session: AsyncSession, copy_id: UUID) -> None:
    for request in await open_requests_for(session, copy_id):
        cancel_row(request)


async def release_after_requester_cancel(
    session: AsyncSession,
    copy: CardCopy,
    request: CardRequest,
) -> None:
    cancel_row(request)
    if request.source is RequestSource.bulk:
        await remove_deck_card(session, copy.id)
        mark_available(copy)
        return
    if request.source_deck_id is None:
        raise DomainError(409, "request is missing its source deck")
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


async def sync_holder_groups(
    session: AsyncSession,
    copy_id: UUID,
    group_ids: Sequence[UUID],
) -> None:
    if group_ids:
        await session.execute(
            delete(CardCopyGroup).where(
                CardCopyGroup.card_copy_id == copy_id,
                CardCopyGroup.group_id.notin_(list(group_ids)),
            )
        )
    else:
        await session.execute(delete(CardCopyGroup).where(CardCopyGroup.card_copy_id == copy_id))
    current = set(
        await session.scalars(
            select(CardCopyGroup.group_id).where(CardCopyGroup.card_copy_id == copy_id)
        )
    )
    for group_id in group_ids:
        if group_id not in current:
            session.add(CardCopyGroup(card_copy_id=copy_id, group_id=group_id))


async def copies_in_decks(session: AsyncSession, deck_ids: set[UUID]) -> list[CardCopy]:
    if not deck_ids:
        return []
    rows = await session.scalars(
        select(CardCopy).where(CardCopy.deck_id.in_(deck_ids)).with_for_update()
    )
    return list(rows)
