from uuid import UUID

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.groups import GroupCreate, GroupSummary, GroupUpdate, InvitationCreate, MemberRead
from app.services import groups as group_service

router = APIRouter(tags=["groups"])


@router.post("/groups", response_model=GroupSummary, status_code=201)
async def create_group(body: GroupCreate, user: CurrentUser, session: DbSession) -> GroupSummary:
    return await group_service.create_group(session, user, body)


@router.get("/groups", response_model=list[GroupSummary])
async def list_groups(user: CurrentUser, session: DbSession) -> list[GroupSummary]:
    return await group_service.list_groups(session, user)


@router.patch("/groups/{group_id}", response_model=GroupSummary)
async def rename_group(
    group_id: UUID,
    body: GroupUpdate,
    user: CurrentUser,
    session: DbSession,
) -> GroupSummary:
    return await group_service.rename_group(session, user, group_id, body)


@router.post("/groups/{group_id}/invitations", response_model=MemberRead, status_code=201)
async def invite(
    group_id: UUID,
    body: InvitationCreate,
    user: CurrentUser,
    session: DbSession,
) -> MemberRead:
    return await group_service.invite(session, user, group_id, body)


@router.post("/invitations/{invitation_id}/accept", response_model=MemberRead)
async def accept_invitation(
    invitation_id: UUID,
    user: CurrentUser,
    session: DbSession,
) -> MemberRead:
    return await group_service.accept_invitation(session, user, invitation_id)


@router.post("/invitations/{invitation_id}/decline", status_code=204)
async def decline_invitation(
    invitation_id: UUID,
    user: CurrentUser,
    session: DbSession,
) -> None:
    await group_service.decline_invitation(session, user, invitation_id)


@router.get("/groups/{group_id}/members", response_model=list[MemberRead])
async def list_members(
    group_id: UUID,
    user: CurrentUser,
    session: DbSession,
) -> list[MemberRead]:
    return await group_service.list_members(session, user, group_id)


@router.post("/groups/{group_id}/leave", status_code=204)
async def leave_group(group_id: UUID, user: CurrentUser, session: DbSession) -> None:
    await group_service.leave_group(session, user, group_id)
