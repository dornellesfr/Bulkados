from uuid import UUID

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.requests import HandoffLists, RequestCreate, RequestRead
from app.services import requests as request_service

router = APIRouter(tags=["requests"])


@router.post("/decks/{deck_id}/requests", response_model=RequestRead, status_code=201)
async def create_request(
    deck_id: UUID,
    body: RequestCreate,
    user: CurrentUser,
    session: DbSession,
) -> RequestRead:
    return await request_service.create_request(session, user, deck_id, body)


@router.post("/requests/{request_id}/accept", response_model=RequestRead)
async def accept_request(
    request_id: UUID,
    user: CurrentUser,
    session: DbSession,
) -> RequestRead:
    return await request_service.accept_request(session, user, request_id)


@router.post("/requests/{request_id}/reject", response_model=RequestRead)
async def reject_request(
    request_id: UUID,
    user: CurrentUser,
    session: DbSession,
) -> RequestRead:
    return await request_service.reject_request(session, user, request_id)


@router.post("/requests/{request_id}/cancel", response_model=RequestRead)
async def cancel_request(
    request_id: UUID,
    user: CurrentUser,
    session: DbSession,
) -> RequestRead:
    return await request_service.cancel_request(session, user, request_id)


@router.post("/requests/{request_id}/confirm", response_model=RequestRead)
async def confirm_request(
    request_id: UUID,
    user: CurrentUser,
    session: DbSession,
) -> RequestRead:
    return await request_service.confirm_request(session, user, request_id)


@router.get("/groups/{group_id}/handoffs", response_model=HandoffLists)
async def handoffs(group_id: UUID, user: CurrentUser, session: DbSession) -> HandoffLists:
    return await request_service.handoffs(session, user, group_id)
