from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, SmallInteger, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.identity import USER_LEVEL
from app.models.base import Base, CreatedAtMixin


class User(CreatedAtMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(first_name)) BETWEEN 1 AND 80",
            name="ck_users_first_name",
        ),
        CheckConstraint(
            "char_length(btrim(last_name)) BETWEEN 1 AND 80",
            name="ck_users_last_name",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[int] = mapped_column(
        SmallInteger,
        default=USER_LEVEL,
        server_default=text(str(USER_LEVEL)),
        nullable=False,
    )
