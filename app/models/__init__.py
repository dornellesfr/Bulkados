"""Modelos ORM.

Importe cada novo módulo de modelo neste arquivo para que o metadata
do SQLAlchemy fique visível para o Alembic.
"""

from app.models.base import Base, IntIdMixin, TimestampMixin

__all__ = ["Base", "IntIdMixin", "TimestampMixin"]
