"""Nome e sobrenome da pessoa, para não identificar a casa pelo e-mail.

Revision ID: a91c4e2b6d08
Revises: e4b8c1a07d92
Create Date: 2026-11-05

"""

from alembic import op

revision = "a91c4e2b6d08"
down_revision = "e4b8c1a07d92"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN first_name TEXT;")
    op.execute("ALTER TABLE users ADD COLUMN last_name TEXT;")
    op.execute(
        "UPDATE users SET "
        "first_name = left("
        "COALESCE(NULLIF(btrim(split_part(email, '@', 1)), ''), 'Pessoa'), 80"
        "), "
        "last_name = 'a definir' "
        "WHERE first_name IS NULL;"
    )
    op.execute("ALTER TABLE users ALTER COLUMN first_name SET NOT NULL;")
    op.execute("ALTER TABLE users ALTER COLUMN last_name SET NOT NULL;")
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT ck_users_first_name "
        "CHECK (char_length(btrim(first_name)) BETWEEN 1 AND 80);"
    )
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT ck_users_last_name "
        "CHECK (char_length(btrim(last_name)) BETWEEN 1 AND 80);"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP CONSTRAINT ck_users_last_name;")
    op.execute("ALTER TABLE users DROP CONSTRAINT ck_users_first_name;")
    op.execute("ALTER TABLE users DROP COLUMN last_name;")
    op.execute("ALTER TABLE users DROP COLUMN first_name;")
