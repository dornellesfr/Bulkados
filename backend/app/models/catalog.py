from uuid import UUID, uuid4

from sqlalchemy import Boolean, Index, String, Text, Uuid
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import CommanderLegal, PartnerKind
from app.models.base import Base
from app.models.enums import str_enum


class CatalogCard(Base):
    __tablename__ = "catalog_cards"
    __table_args__ = (
        Index(
            "ix_catalog_cards_search_en",
            "search_en",
            postgresql_ops={"search_en": "text_pattern_ops"},
        ),
        Index(
            "ix_catalog_cards_search_pt",
            "search_pt",
            postgresql_ops={"search_pt": "text_pattern_ops"},
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    oracle_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(512), nullable=False)
    name_pt: Mapped[str | None] = mapped_column(String(512), nullable=True)
    search_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_pt: Mapped[str | None] = mapped_column(Text, nullable=True)
    mana_cost: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    type_line: Mapped[str] = mapped_column(Text, nullable=False)
    oracle_text: Mapped[str] = mapped_column(Text, nullable=False)
    color_identity: Mapped[list[str]] = mapped_column(ARRAY(String(8)), nullable=False)
    keywords: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    is_basic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    any_number_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    commander_legal: Mapped[CommanderLegal] = mapped_column(
        str_enum(CommanderLegal, "commander_legal"),
        nullable=False,
    )
    can_be_commander: Mapped[bool] = mapped_column(Boolean, nullable=False)
    partner_kind: Mapped[PartnerKind | None] = mapped_column(
        str_enum(PartnerKind, "partner_kind"),
        nullable=True,
    )
