from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import MembershipStatus
from app.domain.identity import normalize_email


class GroupCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)


class GroupUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)


class InvitationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        return normalize_email(value)


class GroupSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str
    owner_id: UUID
    owner_email: str
    membership_status: MembershipStatus
    invitation_id: UUID
    created_at: datetime


class MemberRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invitation_id: UUID
    user_id: UUID
    email: str
    first_name: str
    last_name: str
    status: MembershipStatus
    created_at: datetime


class InvitationGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str


class InvitationPerson(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    email: str
    first_name: str
    last_name: str


class InvitationRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    group: InvitationGroup
    invited_by: InvitationPerson
    created_at: datetime
