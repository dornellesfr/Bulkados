from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, SmallInteger, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

DEFAULT_INTERVAL_DAYS = 90


class CatalogSync(Base):
    """Estado da atualização do acervo. Sempre uma única linha, com id 1."""

    __tablename__ = "catalog_sync"
    __table_args__ = (
        CheckConstraint("id = 1", name="single_row"),
        CheckConstraint("interval_days >= 1", name="interval_positive"),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    interval_days: Mapped[int] = mapped_column(
        Integer,
        default=DEFAULT_INTERVAL_DAYS,
        server_default=text(str(DEFAULT_INTERVAL_DAYS)),
        nullable=False,
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    running_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
