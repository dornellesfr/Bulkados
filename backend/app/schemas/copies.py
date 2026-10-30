from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import CopyState, RequestSource, RequestStatus

CopyVisibility = Literal["available", "reserved", "in_deck", "in_use_elsewhere"]


class BulkCopyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    oracle_id: UUID
    quantity: int = Field(ge=1, le=100)
    holder_id: UUID | None = None
    group_ids: list[UUID] | None = None


class ShareCopy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_id: UUID


class PersonRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    nick: str


class CatalogRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    oracle_id: UUID
    name_en: str
    name_pt: str | None
    image_url: str | None
    mana_cost: str | None
    type_line: str
    color_identity: list[str]
    is_basic: bool


class CopyDeckRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str
    owner: PersonRef


class OpenRequestRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    status: RequestStatus
    source: RequestSource
    requester: PersonRef


class CopyRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    catalog: CatalogRef
    holder: PersonRef
    added_by: PersonRef
    price_cents: int | None
    price_fetched_at: datetime | None
    state: CopyState
    locked: bool
    visibility: CopyVisibility
    deck: CopyDeckRef | None
    open_request: OpenRequestRef | None
