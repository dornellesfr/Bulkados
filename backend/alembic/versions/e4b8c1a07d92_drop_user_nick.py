"""Remove o nick. A pessoa passa a ser identificada pelo e-mail.

Revision ID: e4b8c1a07d92
Revises: d6e0b3c5f1a7
Create Date: 2026-11-05

"""

from alembic import op

revision = "e4b8c1a07d92"
down_revision = "d6e0b3c5f1a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN nick_normalized;")
    op.execute("ALTER TABLE users DROP COLUMN nick;")


def downgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN nick VARCHAR(20);")
    op.execute("ALTER TABLE users ADD COLUMN nick_normalized VARCHAR(20);")
    op.execute(
        "UPDATE users SET nick = split_part(email, '@', 1), "
        "nick_normalized = lower(split_part(email, '@', 1));"
    )
    op.execute("ALTER TABLE users ALTER COLUMN nick SET NOT NULL;")
    op.execute("ALTER TABLE users ALTER COLUMN nick_normalized SET NOT NULL;")
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT uq_users_nick_normalized UNIQUE (nick_normalized);"
    )
