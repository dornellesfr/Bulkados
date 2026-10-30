from uuid import UUID, uuid4

from sqlalchemy import SmallInteger, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.identity import USER_LEVEL
from app.models.base import Base, CreatedAtMixin


class User(CreatedAtMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    nick: Mapped[str] = mapped_column(String(20), nullable=False)
    nick_normalized: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    level: Mapped[int] = mapped_column(
        SmallInteger,
        default=USER_LEVEL,
        server_default=text(str(USER_LEVEL)),
        nullable=False,
    )
