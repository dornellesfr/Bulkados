from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.domain.enums import MembershipStatus
from app.models.deck import Deck
from app.models.group import Group, GroupMember


async def is_accepted(session: AsyncSession, group_id: UUID, user_id: UUID) -> bool:
    membership = await session.scalar(
        select(GroupMember.id).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
            GroupMember.status == MembershipStatus.accepted,
        )
    )
    return membership is not None


async def accepted_group_ids(session: AsyncSession, user_id: UUID) -> list[UUID]:
    rows = await session.scalars(
        select(GroupMember.group_id).where(
            GroupMember.user_id == user_id,
            GroupMember.status == MembershipStatus.accepted,
        )
    )
    return list(rows)


async def require_accepted_group(session: AsyncSession, group_id: UUID, user_id: UUID) -> Group:
    group = await session.get(Group, group_id)
    if group is None or not await is_accepted(session, group_id, user_id):
        raise DomainError(404, "group not found")
    return group


async def require_deck_reader(session: AsyncSession, deck_id: UUID, user_id: UUID) -> Deck:
    deck = await session.get(Deck, deck_id)
    if deck is None or not await is_accepted(session, deck.group_id, user_id):
        raise DomainError(404, "deck not found")
    return deck


async def require_deck_owner(session: AsyncSession, deck_id: UUID, user_id: UUID) -> Deck:
    deck = await require_deck_reader(session, deck_id, user_id)
    if deck.owner_id != user_id:
        raise DomainError(403, "only the deck owner can do this")
    return deck
