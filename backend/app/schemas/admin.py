from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.identity import ADMIN_LEVEL, USER_LEVEL
from app.schemas.auth import RegisterRequest


class AdminCreateUserRequest(RegisterRequest):
    level: int = Field(default=USER_LEVEL, ge=ADMIN_LEVEL, le=USER_LEVEL)


class AdminUserRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    nick: str
    email: str
    level: int


class SyncIntervalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    days: int = Field(ge=1, le=3650)


class CatalogSyncStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interval_days: int
    last_synced_at: datetime | None
    running: bool
    last_error: str | None
