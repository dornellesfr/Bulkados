from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Uuid, text
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
        index=True,
    )
    requester_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    holder_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
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
    status: Mapped[RequestStatus] = mapped_column(
        str_enum(RequestStatus, "request_status"),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
