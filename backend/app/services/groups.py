from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.errors import DomainError
from app.domain.enums import OPEN_REQUEST_STATUSES, CopyState, MembershipStatus
from app.domain.identity import normalize_nick
from app.models.copy import CardCopy, CardCopyGroup
from app.models.deck import Deck, DeckCard
from app.models.group import Group, GroupMember
from app.models.request import CardRequest
from app.models.user import User
from app.schemas.groups import GroupCreate, GroupSummary, GroupUpdate, InvitationCreate, MemberRead
from app.services.access import require_accepted_group
from app.services.copy_state import (
    cancel_open_requests,
    cancel_row,
    copies_in_decks,
    lock_copy,
    mark_available,
    open_requests_for,
    release_after_requester_cancel,
    remove_deck_card,
)


async def create_group(session: AsyncSession, user: User, body: GroupCreate) -> GroupSummary:
    group = Group(name=body.name, owner_id=user.id)
    session.add(group)
    await session.flush()
    membership = GroupMember(
        group_id=group.id,
        user_id=user.id,
        status=MembershipStatus.accepted,
        invited_by=None,
    )
    session.add(membership)
    await session.flush()
    return _summary(group, user.nick, membership)


async def list_groups(session: AsyncSession, user: User) -> list[GroupSummary]:
    owner = aliased(User)
    rows = (
        await session.execute(
            select(Group, GroupMember, owner)
            .join(GroupMember, GroupMember.group_id == Group.id)
            .join(owner, owner.id == Group.owner_id)
            .where(
                GroupMember.user_id == user.id,
                GroupMember.status.in_((MembershipStatus.accepted, MembershipStatus.invited)),
            )
            .order_by(Group.created_at)
        )
    ).all()
    return [_summary(group, owner_user.nick, membership) for group, membership, owner_user in rows]


async def rename_group(
    session: AsyncSession,
    user: User,
    group_id: UUID,
    body: GroupUpdate,
) -> GroupSummary:
    group = await require_accepted_group(session, group_id, user.id)
    if group.owner_id != user.id:
        raise DomainError(403, "only the group owner can do this")
    group.name = body.name
    owner = await session.get(User, group.owner_id)
    membership = await _membership(session, group_id, user.id)
    if owner is None or membership is None:
        raise DomainError(404, "group not found")
    return _summary(group, owner.nick, membership)


async def invite(
    session: AsyncSession,
    user: User,
    group_id: UUID,
    body: InvitationCreate,
) -> MemberRead:
    await require_accepted_group(session, group_id, user.id)
    try:
        nick = normalize_nick(body.nick)
    except ValueError as exc:
        raise DomainError(422, str(exc)) from exc
    target = await session.scalar(select(User).where(User.nick_normalized == nick.lower()))
    if target is None:
        raise DomainError(404, "user not found")
    existing = await session.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == target.id,
        )
    )
    if existing is not None:
        raise DomainError(409, "user is already invited or a member")
    membership = GroupMember(
        group_id=group_id,
        user_id=target.id,
        status=MembershipStatus.invited,
        invited_by=user.id,
    )
    session.add(membership)
    await session.flush()
    return _member(membership, target)


async def accept_invitation(
    session: AsyncSession,
    user: User,
    invitation_id: UUID,
) -> MemberRead:
    membership = await _own_invitation(session, user, invitation_id)
    if membership.status is not MembershipStatus.invited:
        raise DomainError(409, "invitation is not pending")
    membership.status = MembershipStatus.accepted
    return _member(membership, user)


async def decline_invitation(session: AsyncSession, user: User, invitation_id: UUID) -> None:
    membership = await _own_invitation(session, user, invitation_id)
    if membership.status is not MembershipStatus.invited:
        raise DomainError(409, "invitation is not pending")
    await session.delete(membership)


async def list_members(session: AsyncSession, user: User, group_id: UUID) -> list[MemberRead]:
    await require_accepted_group(session, group_id, user.id)
    member_user = aliased(User)
    rows = (
        await session.execute(
            select(GroupMember, member_user)
            .join(member_user, member_user.id == GroupMember.user_id)
            .where(GroupMember.group_id == group_id)
            .order_by(GroupMember.created_at)
        )
    ).all()
    return [_member(membership, member) for membership, member in rows]


async def leave_group(session: AsyncSession, user: User, group_id: UUID) -> None:
    group = await session.get(Group, group_id, with_for_update=True)
    if group is None:
        raise DomainError(404, "group not found")
    memberships = list(
        await session.scalars(
            select(GroupMember).where(GroupMember.group_id == group_id).with_for_update()
        )
    )
    leaver = next((item for item in memberships if item.user_id == user.id), None)
    if leaver is None or leaver.status is not MembershipStatus.accepted:
        raise DomainError(404, "group not found")

    decks = list(
        await session.scalars(select(Deck).where(Deck.group_id == group_id).with_for_update())
    )
    group_deck_ids = {deck.id for deck in decks}
    leaver_decks = [deck for deck in decks if deck.owner_id == user.id]
    leaver_deck_ids = {deck.id for deck in leaver_decks}

    for copy in await copies_in_decks(session, leaver_deck_ids):
        if copy.holder_id == user.id:
            continue
        await cancel_open_requests(session, copy.id)
        await remove_deck_card(session, copy.id)
        mark_available(copy)

    leaver_copies = await _held_copies(session, group_id, user.id)
    for copy in leaver_copies:
        opens = await open_requests_for(session, copy.id)
        for request in opens:
            source_here = (
                request.source_deck_id is not None and request.source_deck_id in group_deck_ids
            )
            target_here = request.target_deck_id in group_deck_ids
            if request.group_id == group_id or source_here or target_here:
                cancel_row(request)
        still_open = [request for request in opens if request.status in OPEN_REQUEST_STATUSES]
        leaves_deck = copy.deck_id in group_deck_ids
        if leaves_deck:
            await remove_deck_card(session, copy.id)
        if leaves_deck or (copy.deck_id is None and not still_open):
            mark_available(copy)
        elif copy.deck_id is not None and not still_open and copy.state is CopyState.reserved:
            copy.state = CopyState.in_deck
            copy.locked = False
        await session.execute(
            delete(CardCopyGroup).where(
                CardCopyGroup.card_copy_id == copy.id,
                CardCopyGroup.group_id == group_id,
            )
        )

    outgoing = list(
        await session.scalars(
            select(CardRequest).where(
                CardRequest.group_id == group_id,
                CardRequest.requester_id == user.id,
                CardRequest.status.in_(tuple(OPEN_REQUEST_STATUSES)),
            )
        )
    )
    for request in outgoing:
        if request.status not in OPEN_REQUEST_STATUSES:
            continue
        requested = await lock_copy(session, request.card_copy_id)
        if requested is None:
            cancel_row(request)
            continue
        await release_after_requester_cancel(session, requested, request)

    if leaver_deck_ids:
        await session.execute(delete(DeckCard).where(DeckCard.deck_id.in_(leaver_deck_ids)))
        await session.execute(
            delete(CardRequest).where(
                or_(
                    CardRequest.target_deck_id.in_(leaver_deck_ids),
                    CardRequest.source_deck_id.in_(leaver_deck_ids),
                )
            )
        )
        for deck in leaver_decks:
            await session.delete(deck)

    await session.delete(leaver)
    await session.flush()

    remaining = [
        item
        for item in memberships
        if item.user_id != user.id and item.status is MembershipStatus.accepted
    ]
    if not remaining:
        await _delete_group(session, group)
        return
    if group.owner_id == user.id:
        remaining.sort(key=_membership_age)
        group.owner_id = remaining[0].user_id


def _summary(group: Group, owner_nick: str, membership: GroupMember) -> GroupSummary:
    return GroupSummary(
        id=group.id,
        name=group.name,
        owner_id=group.owner_id,
        owner_nick=owner_nick,
        membership_status=membership.status,
        invitation_id=membership.id,
        created_at=group.created_at,
    )


def _member(membership: GroupMember, user: User) -> MemberRead:
    return MemberRead(
        invitation_id=membership.id,
        user_id=user.id,
        nick=user.nick,
        status=membership.status,
        created_at=membership.created_at,
    )


def _membership_age(membership: GroupMember) -> tuple[object, str]:
    return (membership.created_at, str(membership.user_id))


async def _membership(
    session: AsyncSession,
    group_id: UUID,
    user_id: UUID,
) -> GroupMember | None:
    return await session.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
    )


async def _own_invitation(
    session: AsyncSession,
    user: User,
    invitation_id: UUID,
) -> GroupMember:
    membership = await session.get(GroupMember, invitation_id)
    if membership is None or membership.user_id != user.id:
        raise DomainError(404, "invitation not found")
    return membership


async def _held_copies(session: AsyncSession, group_id: UUID, user_id: UUID) -> list[CardCopy]:
    rows = await session.scalars(
        select(CardCopy)
        .join(CardCopyGroup, CardCopyGroup.card_copy_id == CardCopy.id)
        .where(CardCopyGroup.group_id == group_id, CardCopy.holder_id == user_id)
        .with_for_update()
    )
    return list(rows)


async def _delete_group(session: AsyncSession, group: Group) -> None:
    decks = list(await session.scalars(select(Deck).where(Deck.group_id == group.id)))
    deck_ids = {deck.id for deck in decks}
    for copy in await copies_in_decks(session, deck_ids):
        await cancel_open_requests(session, copy.id)
        await remove_deck_card(session, copy.id)
        mark_available(copy)
    request_filter = [CardRequest.group_id == group.id]
    if deck_ids:
        request_filter.append(CardRequest.target_deck_id.in_(deck_ids))
        request_filter.append(CardRequest.source_deck_id.in_(deck_ids))
    await session.execute(delete(CardRequest).where(or_(*request_filter)))
    if deck_ids:
        await session.execute(delete(DeckCard).where(DeckCard.deck_id.in_(deck_ids)))
        await session.execute(delete(Deck).where(Deck.id.in_(deck_ids)))
    await session.execute(delete(CardCopyGroup).where(CardCopyGroup.group_id == group.id))
    await session.execute(delete(GroupMember).where(GroupMember.group_id == group.id))
    await session.delete(group)
