from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CatalogCardRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    oracle_id: UUID
    name_en: str
    name_pt: str | None
    mana_cost: str | None
    type_line: str
    color_identity: list[str]
    is_basic: bool
