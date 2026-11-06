from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.enums import RequestSource, RequestStatus
from app.schemas.copies import PersonRef


class RequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_copy_id: UUID


class RequestRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    card_copy_id: UUID
    group_id: UUID
    requester_id: UUID
    requester_email: str
    requester_first_name: str
    requester_last_name: str
    holder_id: UUID
    holder_email: str
    holder_first_name: str
    holder_last_name: str
    source: RequestSource
    source_deck_id: UUID | None
    target_deck_id: UUID
    target_deck_name: str
    status: RequestStatus
    name_en: str
    name_pt: str | None
    created_at: datetime
    resolved_at: datetime | None


class CatalogName(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name_en: str
    name_pt: str | None


class DeckBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str


class HandoffBring(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    source: RequestSource
    catalog: CatalogName
    requester: PersonRef
    target_deck: DeckBrief


class HandoffReceive(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    source: RequestSource
    catalog: CatalogName
    status: RequestStatus
    holder: PersonRef
    target_deck: DeckBrief


class HandoffLists(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to_bring: list[HandoffBring]
    to_receive: list[HandoffReceive]
