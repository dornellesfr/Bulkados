from uuid import UUID

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession, Prices
from app.schemas.copies import BulkCopyCreate, CopyRead, ShareCopy
from app.services import copies as copy_service

router = APIRouter(tags=["copies"])


@router.post("/groups/{group_id}/copies", response_model=list[CopyRead], status_code=201)
async def create_bulk_copies(
    group_id: UUID,
    body: BulkCopyCreate,
    user: CurrentUser,
    session: DbSession,
    prices: Prices,
) -> list[CopyRead]:
    return await copy_service.create_bulk_copies(session, user, group_id, body, prices)


@router.get("/groups/{group_id}/copies", response_model=list[CopyRead])
async def list_group_copies(
    group_id: UUID,
    user: CurrentUser,
    session: DbSession,
) -> list[CopyRead]:
    return await copy_service.list_group_copies(session, user, group_id)


@router.post("/copies/{copy_id}/groups", response_model=CopyRead, status_code=201)
async def share_copy(
    copy_id: UUID,
    body: ShareCopy,
    user: CurrentUser,
    session: DbSession,
) -> CopyRead:
    return await copy_service.share_copy(session, user, copy_id, body)


@router.delete("/copies/{copy_id}", status_code=204)
async def remove_copy(copy_id: UUID, user: CurrentUser, session: DbSession) -> None:
    await copy_service.remove_copy(session, user, copy_id)


@router.post("/copies/{copy_id}/refresh-price", response_model=CopyRead)
async def refresh_price(
    copy_id: UUID,
    user: CurrentUser,
    session: DbSession,
    prices: Prices,
) -> CopyRead:
    return await copy_service.refresh_price(session, user, copy_id, prices)
