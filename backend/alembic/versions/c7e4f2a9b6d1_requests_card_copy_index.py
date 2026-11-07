"""Índice para apagar e carregar pedidos por cópia."""

from collections.abc import Sequence

from alembic import op

revision: str = "c7e4f2a9b6d1"
down_revision: str | None = "9b5d2e8c4a10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_requests_card_copy_id", "requests", ["card_copy_id"])


def downgrade() -> None:
    op.drop_index("ix_requests_card_copy_id", table_name="requests")
