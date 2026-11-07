from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import RequestSource, RequestStatus
from app.models.base import Base, CreatedAtMixin
from app.models.enums import str_enum


class CardRequest(CreatedAtMixin, Base):
    __tablename__ = "requests"
    __table_args__ = (
        Index(
            "uq_requests_one_open_per_copy",
            "card_copy_id",
            unique=True,
            postgresql_where=text("status IN ('pending_acceptance', 'awaiting_handoff')"),
        ),
        Index("ix_requests_group_id_status_holder_id", "group_id", "status", "holder_id"),
        Index("ix_requests_group_id_status_requester_id", "group_id", "status", "requester_id"),
        Index("ix_requests_card_copy_id", "card_copy_id"),
        Index("ix_requests_target_deck_id", "target_deck_id"),
        Index("ix_requests_source_deck_id", "source_deck_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    card_copy_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("card_copies.id", ondelete="CASCADE"),
        nullable=False,
    )
    group_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    requester_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    holder_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    source: Mapped[RequestSource] = mapped_column(
        str_enum(RequestSource, "request_source"),
        nullable=False,
    )
    source_deck_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("decks.id", ondelete="CASCADE"),
        nullable=True,
    )
    target_deck_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("decks.id", ondelete="CASCADE"),
        nullable=False,
    )
    as_commander: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    status: Mapped[RequestStatus] = mapped_column(
        str_enum(RequestStatus, "request_status"),
        nullable=False,
    )
    requester_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    holder_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
