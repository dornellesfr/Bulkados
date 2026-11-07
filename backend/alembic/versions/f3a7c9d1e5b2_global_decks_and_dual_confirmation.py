"""Decks globais da pessoa e confirmação dupla no encontro.

Revision ID: f3a7c9d1e5b2
Revises: a91c4e2b6d08
Create Date: 2026-11-06

"""

import sqlalchemy as sa
from alembic import op

revision = "f3a7c9d1e5b2"
down_revision = "a91c4e2b6d08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "requests",
        sa.Column("as_commander", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "requests",
        sa.Column("requester_confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "requests",
        sa.Column("holder_confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.drop_constraint("fk_decks_group_id_groups", "decks", type_="foreignkey")
    op.drop_index("ix_decks_group_id", table_name="decks")
    op.drop_column("decks", "group_id")


def downgrade() -> None:
    op.add_column("decks", sa.Column("group_id", sa.Uuid(), nullable=True))
    op.execute(
        """
        UPDATE decks
        SET group_id = (
            SELECT group_members.group_id
            FROM group_members
            WHERE group_members.user_id = decks.owner_id
            ORDER BY group_members.created_at
            LIMIT 1
        )
        """
    )
    op.alter_column("decks", "group_id", nullable=False)
    op.create_index("ix_decks_group_id", "decks", ["group_id"])
    op.create_foreign_key(
        "fk_decks_group_id_groups",
        "decks",
        "groups",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_column("requests", "holder_confirmed_at")
    op.drop_column("requests", "requester_confirmed_at")
    op.drop_column("requests", "as_commander")
