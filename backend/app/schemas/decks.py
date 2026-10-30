from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import DeckFormat, DeckRole


class DeckCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    format: DeckFormat


class DeckUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=80)
    format: DeckFormat | None = None


class DeckCopyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_card_id: UUID
    quantity: int = Field(ge=1, le=100)


class CommandersUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_copy_ids: list[UUID]


class TakeCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_copy_id: UUID


class MoveCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_deck_id: UUID


class DeckSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    group_id: UUID
    name: str
    format: DeckFormat
    created_at: datetime


class DeckCardRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_copy_id: UUID
    role: DeckRole
    name_en: str
    name_pt: str | None
    price_cents: int | None
    locked: bool
    is_basic: bool


class WarningRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    card_copy_id: UUID | None = None


class DeckDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    group_id: UUID
    owner_id: UUID
    name: str
    format: DeckFormat
    created_at: datetime
    card_count: int
    main_price_cents: int
    commander_price_cents: int
    warnings: list[WarningRead]
    cards: list[DeckCardRead]
    commanders: list[DeckCardRead]
