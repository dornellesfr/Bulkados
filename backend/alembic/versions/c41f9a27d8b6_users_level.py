"""Nível de acesso do usuário (0 = admin, 1 = usuário comum).

Revision ID: c41f9a27d8b6
Revises: b7d2e4a91c35
Create Date: 2026-10-30

"""

from alembic import op

revision = "c41f9a27d8b6"
down_revision = "b7d2e4a91c35"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN level SMALLINT DEFAULT 1 NOT NULL;")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN level;")
