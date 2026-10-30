"""Estado da atualização do acervo.

Revision ID: d6e0b3c5f1a7
Revises: c41f9a27d8b6
Create Date: 2026-10-30

"""

from alembic import op

revision = "d6e0b3c5f1a7"
down_revision = "c41f9a27d8b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE catalog_sync ("
        "id SMALLINT NOT NULL, "
        "interval_days INTEGER DEFAULT 90 NOT NULL, "
        "last_synced_at TIMESTAMP WITH TIME ZONE, "
        "running_since TIMESTAMP WITH TIME ZONE, "
        "last_error TEXT, "
        "CONSTRAINT pk_catalog_sync PRIMARY KEY (id), "
        "CONSTRAINT ck_catalog_sync_single_row CHECK (id = 1), "
        "CONSTRAINT ck_catalog_sync_interval_positive CHECK (interval_days >= 1)"
        ");"
    )


def downgrade() -> None:
    op.execute("DROP TABLE catalog_sync;")
