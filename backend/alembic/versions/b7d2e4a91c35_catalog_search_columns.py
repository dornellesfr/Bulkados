"""Colunas de busca, custo e imagem em catalog_cards.

Revision ID: b7d2e4a91c35
Revises: 8f3c1a0b7e21
Create Date: 2026-10-30

"""

from alembic import op

revision = "b7d2e4a91c35"
down_revision = "8f3c1a0b7e21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE catalog_cards "
        "ADD COLUMN search_en TEXT, "
        "ADD COLUMN search_pt TEXT, "
        "ADD COLUMN mana_cost TEXT, "
        "ADD COLUMN image_url TEXT;"
    )
    op.execute(
        "CREATE INDEX ix_catalog_cards_search_en ON catalog_cards (search_en text_pattern_ops);"
    )
    op.execute(
        "CREATE INDEX ix_catalog_cards_search_pt ON catalog_cards (search_pt text_pattern_ops);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX ix_catalog_cards_search_pt;")
    op.execute("DROP INDEX ix_catalog_cards_search_en;")
    op.execute(
        "ALTER TABLE catalog_cards "
        "DROP COLUMN image_url, "
        "DROP COLUMN mana_cost, "
        "DROP COLUMN search_pt, "
        "DROP COLUMN search_en;"
    )
