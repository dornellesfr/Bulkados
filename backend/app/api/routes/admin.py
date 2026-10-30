from fastapi import APIRouter

from app.api.deps import AdminUser, Auth, CatalogFeed, DbSession
from app.core.errors import DomainError
from app.schemas.admin import (
    AdminCreateUserRequest,
    AdminUserRead,
    CatalogSyncStatus,
    SyncIntervalRequest,
)
from app.services import auth as auth_service
from app.services import catalog_control

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/users", response_model=AdminUserRead, status_code=201)
async def create_user(
    body: AdminCreateUserRequest,
    session: DbSession,
    auth: Auth,
    _admin: AdminUser,
) -> AdminUserRead:
    user = await auth_service.create_user(session, auth, body, body.level)
    return AdminUserRead(id=user.id, nick=user.nick, email=user.email, level=user.level)


@router.get("/catalog/sync", response_model=CatalogSyncStatus)
async def catalog_sync_status(session: DbSession, _admin: AdminUser) -> CatalogSyncStatus:
    return await catalog_control.get_status(session)


@router.post("/catalog/sync-interval", response_model=CatalogSyncStatus)
async def set_catalog_sync_interval(
    body: SyncIntervalRequest,
    session: DbSession,
    _admin: AdminUser,
) -> CatalogSyncStatus:
    return await catalog_control.set_interval(session, body.days)


@router.post("/catalog/sync", response_model=CatalogSyncStatus, status_code=202)
async def start_catalog_sync(
    source: CatalogFeed,
    session: DbSession,
    _admin: AdminUser,
) -> CatalogSyncStatus:
    if not await catalog_control.start_sync(source):
        raise DomainError(409, "catalog sync already running")
    return await catalog_control.get_status(session)
