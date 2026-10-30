from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import CopyState
from app.models.base import Base, CreatedAtMixin
from app.models.enums import str_enum


class CardCopy(CreatedAtMixin, Base):
    __tablename__ = "card_copies"
    __table_args__ = (
        CheckConstraint(
            "("
            "state = 'available' AND deck_id IS NULL AND locked = false"
            ") OR ("
            "state = 'reserved' AND locked = true"
            ") OR ("
            "state = 'in_deck' AND deck_id IS NOT NULL"
            ")",
            name="state_lock_deck",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    catalog_card_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("catalog_cards.id"),
        nullable=False,
        index=True,
    )
    holder_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    added_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    state: Mapped[CopyState] = mapped_column(str_enum(CopyState, "copy_state"), nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    deck_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("decks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


class CardCopyGroup(Base):
    __tablename__ = "card_copy_groups"

    card_copy_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("card_copies.id", ondelete="CASCADE"),
        primary_key=True,
    )
    group_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("groups.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
