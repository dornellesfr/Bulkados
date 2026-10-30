from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import CommanderLegal, DeckFormat, DeckRole, PartnerKind
from app.schemas.copies import CatalogRef, OpenRequestRef, PersonRef


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

    oracle_id: UUID
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


class DeckCommanderRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name_en: str
    name_pt: str | None
    image_url: str | None


class DeckSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    group_id: UUID
    name: str
    format: DeckFormat
    created_at: datetime
    color_identity: list[str] | None
    color_identity_name: str | None
    commanders: list[DeckCommanderRef]


class DeckCatalogRef(CatalogRef):
    commander_legal: CommanderLegal
    can_be_commander: bool
    partner_kind: PartnerKind | None


class DeckCardRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_copy_id: UUID
    role: DeckRole
    locked: bool
    price_cents: int | None
    holder: PersonRef
    catalog: DeckCatalogRef
    open_request: OpenRequestRef | None
    can_toggle_commander: bool


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
    color_identity: list[str] | None
    color_identity_name: str | None
    card_count: int
    main_price_cents: int
    commander_price_cents: int
    warnings: list[WarningRead]
    cards: list[DeckCardRead]
    commanders: list[DeckCardRead]
