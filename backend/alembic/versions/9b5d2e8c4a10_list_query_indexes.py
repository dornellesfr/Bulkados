"""Índices para os filtros que a API usa com mais frequência."""

from collections.abc import Sequence

from alembic import op

revision: str = "9b5d2e8c4a10"
down_revision: str | None = "f3a7c9d1e5b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_groups_owner_id", "groups", ["owner_id"])

    op.drop_index("ix_group_members_group_id", table_name="group_members")
    op.drop_index("ix_group_members_user_id", table_name="group_members")
    op.create_index(
        "ix_group_members_user_id_status",
        "group_members",
        ["user_id", "status"],
    )

    op.drop_index("ix_card_copies_holder_id", table_name="card_copies")
    op.create_index(
        "ix_card_copies_holder_id_state_catalog_card_id",
        "card_copies",
        ["holder_id", "state", "catalog_card_id"],
    )

    op.drop_index("ix_requests_group_id", table_name="requests")
    op.drop_index("ix_requests_requester_id", table_name="requests")
    op.drop_index("ix_requests_holder_id", table_name="requests")
    op.create_index(
        "ix_requests_group_id_status_holder_id",
        "requests",
        ["group_id", "status", "holder_id"],
    )
    op.create_index(
        "ix_requests_group_id_status_requester_id",
        "requests",
        ["group_id", "status", "requester_id"],
    )
    op.create_index("ix_requests_target_deck_id", "requests", ["target_deck_id"])
    op.create_index("ix_requests_source_deck_id", "requests", ["source_deck_id"])


def downgrade() -> None:
    op.drop_index("ix_requests_source_deck_id", table_name="requests")
    op.drop_index("ix_requests_target_deck_id", table_name="requests")
    op.drop_index("ix_requests_group_id_status_requester_id", table_name="requests")
    op.drop_index("ix_requests_group_id_status_holder_id", table_name="requests")
    op.create_index("ix_requests_group_id", "requests", ["group_id"])
    op.create_index("ix_requests_requester_id", "requests", ["requester_id"])
    op.create_index("ix_requests_holder_id", "requests", ["holder_id"])

    op.drop_index(
        "ix_card_copies_holder_id_state_catalog_card_id",
        table_name="card_copies",
    )
    op.create_index("ix_card_copies_holder_id", "card_copies", ["holder_id"])

    op.drop_index("ix_group_members_user_id_status", table_name="group_members")
    op.create_index("ix_group_members_user_id", "group_members", ["user_id"])
    op.create_index("ix_group_members_group_id", "group_members", ["group_id"])

    op.drop_index("ix_groups_owner_id", table_name="groups")
