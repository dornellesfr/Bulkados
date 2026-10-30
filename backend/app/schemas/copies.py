from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import CopyState

CopyVisibility = Literal["available", "reserved", "in_deck", "in_use_elsewhere"]


class BulkCopyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_card_id: UUID
    quantity: int = Field(ge=1, le=100)
    holder_id: UUID | None = None
    group_ids: list[UUID] | None = None


class ShareCopy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_id: UUID


class CopyRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    catalog_card_id: UUID
    oracle_id: UUID
    name_en: str
    name_pt: str | None
    type_line: str
    color_identity: list[str]
    is_basic: bool
    price_cents: int | None
    holder_id: UUID
    holder_nick: str
    state: CopyState
    locked: bool
    visibility: CopyVisibility
    deck_id: UUID | None = None
    deck_name: str | None = None
    deck_owner_nick: str | None = None
