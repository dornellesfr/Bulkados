from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import MembershipStatus


class GroupCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)


class GroupUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)


class InvitationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nick: str


class GroupSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str
    owner_id: UUID
    owner_nick: str
    membership_status: MembershipStatus
    invitation_id: UUID
    created_at: datetime


class MemberRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invitation_id: UUID
    user_id: UUID
    nick: str
    status: MembershipStatus
    created_at: datetime
