from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.enums import RequestSource, RequestStatus


class RequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_copy_id: UUID


class RequestRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    card_copy_id: UUID
    group_id: UUID
    requester_id: UUID
    requester_nick: str
    holder_id: UUID
    holder_nick: str
    source: RequestSource
    source_deck_id: UUID | None
    target_deck_id: UUID
    target_deck_name: str
    status: RequestStatus
    name_en: str
    name_pt: str | None
    created_at: datetime
    resolved_at: datetime | None


class HandoffLists(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to_bring: list[RequestRead]
    to_receive: list[RequestRead]
