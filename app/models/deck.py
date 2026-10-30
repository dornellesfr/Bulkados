from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import DeckFormat, DeckRole
from app.models.base import Base, CreatedAtMixin
from app.models.enums import str_enum


class Deck(CreatedAtMixin, Base):
    __tablename__ = "decks"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    group_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    format: Mapped[DeckFormat] = mapped_column(str_enum(DeckFormat, "deck_format"), nullable=False)


class DeckCard(Base):
    __tablename__ = "deck_cards"

    deck_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("decks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    card_copy_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("card_copies.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[DeckRole] = mapped_column(str_enum(DeckRole, "deck_role"), nullable=False)
