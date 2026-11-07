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
        raise DomainError(404, "Não encontramos esse grupo.")
    return group


async def shares_group(session: AsyncSession, user_id: UUID, other_id: UUID) -> bool:
    if user_id == other_id:
        return True
    other_groups = select(GroupMember.group_id).where(
        GroupMember.user_id == other_id,
        GroupMember.status == MembershipStatus.accepted,
    )
    common = await session.scalar(
        select(GroupMember.group_id)
        .where(
            GroupMember.user_id == user_id,
            GroupMember.status == MembershipStatus.accepted,
            GroupMember.group_id.in_(other_groups),
        )
        .limit(1)
    )
    return common is not None


async def group_ids_by_user(
    session: AsyncSession,
    user_ids: set[UUID],
) -> dict[UUID, set[UUID]]:
    if not user_ids:
        return {}
    rows = await session.execute(
        select(GroupMember.user_id, GroupMember.group_id).where(
            GroupMember.user_id.in_(user_ids),
            GroupMember.status == MembershipStatus.accepted,
        )
    )
    found: dict[UUID, set[UUID]] = {}
    for user_id, group_id in rows.all():
        found.setdefault(user_id, set()).add(group_id)
    return found


async def require_deck_reader(session: AsyncSession, deck_id: UUID, user_id: UUID) -> Deck:
    deck = await session.get(Deck, deck_id)
    if deck is None or not await shares_group(session, deck.owner_id, user_id):
        raise DomainError(404, "Não encontramos esse deck.")
    return deck


async def require_deck_owner(session: AsyncSession, deck_id: UUID, user_id: UUID) -> Deck:
    deck = await session.get(Deck, deck_id)
    if deck is None or deck.owner_id != user_id:
        raise DomainError(404, "Não encontramos esse deck.")
    return deck
