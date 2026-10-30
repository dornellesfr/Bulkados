"""Modelos ORM.

Importe cada novo módulo de modelo neste arquivo para que o metadata
do SQLAlchemy fique visível para o Alembic.
"""

from app.models.base import Base, IntIdMixin, TimestampMixin
from app.models.catalog import CatalogCard
from app.models.copy import CardCopy, CardCopyGroup
from app.models.deck import Deck, DeckCard
from app.models.group import Group, GroupMember
from app.models.request import CardRequest
from app.models.user import User

__all__ = [
    "Base",
    "CardCopy",
    "CardCopyGroup",
    "CardRequest",
    "CatalogCard",
    "Deck",
    "DeckCard",
    "Group",
    "GroupMember",
    "IntIdMixin",
    "TimestampMixin",
    "User",
]
