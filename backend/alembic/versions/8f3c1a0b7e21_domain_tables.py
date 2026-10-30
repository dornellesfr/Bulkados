# ruff: noqa: E501
"""Tabelas do domínio.

Revision ID: 8f3c1a0b7e21
Revises:
Create Date: 2026-10-30

"""

from alembic import op

revision = "8f3c1a0b7e21"
down_revision = None
branch_labels = None
depends_on = None

_STATEMENTS = (
    "CREATE TABLE catalog_cards (\n\tid UUID NOT NULL, \n\toracle_id UUID NOT NULL, \n\tname_en VARCHAR(512) NOT NULL, \n\tname_pt VARCHAR(512), \n\ttype_line TEXT NOT NULL, \n\toracle_text TEXT NOT NULL, \n\tcolor_identity VARCHAR(8)[] NOT NULL, \n\tkeywords TEXT[] NOT NULL, \n\tis_basic BOOLEAN NOT NULL, \n\tany_number_allowed BOOLEAN NOT NULL, \n\tcommander_legal VARCHAR(32) NOT NULL, \n\tcan_be_commander BOOLEAN NOT NULL, \n\tpartner_kind VARCHAR(32), \n\tCONSTRAINT pk_catalog_cards PRIMARY KEY (id), \n\tCONSTRAINT uq_catalog_cards_oracle_id UNIQUE (oracle_id), \n\tCONSTRAINT ck_catalog_cards_commander_legal CHECK (commander_legal IN ('legal', 'banned', 'not_legal')), \n\tCONSTRAINT ck_catalog_cards_partner_kind CHECK (partner_kind IN ('partner', 'partner_with', 'friends_forever', 'background', 'choose_a_background', 'doctors_companion'))\n);",
    "CREATE TABLE users (\n\tid UUID NOT NULL, \n\temail VARCHAR(320) NOT NULL, \n\tnick VARCHAR(20) NOT NULL, \n\tnick_normalized VARCHAR(20) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_users PRIMARY KEY (id), \n\tCONSTRAINT uq_users_email UNIQUE (email), \n\tCONSTRAINT uq_users_nick_normalized UNIQUE (nick_normalized)\n);",
    "CREATE TABLE groups (\n\tid UUID NOT NULL, \n\tname VARCHAR(80) NOT NULL, \n\towner_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_groups PRIMARY KEY (id), \n\tCONSTRAINT fk_groups_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id)\n);",
    "CREATE TABLE decks (\n\tid UUID NOT NULL, \n\tgroup_id UUID NOT NULL, \n\towner_id UUID NOT NULL, \n\tname VARCHAR(80) NOT NULL, \n\tformat VARCHAR(32) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_decks PRIMARY KEY (id), \n\tCONSTRAINT fk_decks_group_id_groups FOREIGN KEY(group_id) REFERENCES groups (id) ON DELETE CASCADE, \n\tCONSTRAINT fk_decks_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id), \n\tCONSTRAINT ck_decks_deck_format CHECK (format IN ('commander_10', 'commander_100', 'commander_200', 'commander_500', 'competitive'))\n);",
    "CREATE INDEX ix_decks_group_id ON decks (group_id);",
    "CREATE INDEX ix_decks_owner_id ON decks (owner_id);",
    "CREATE TABLE group_members (\n\tid UUID NOT NULL, \n\tgroup_id UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\tstatus VARCHAR(32) NOT NULL, \n\tinvited_by UUID, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_group_members PRIMARY KEY (id), \n\tCONSTRAINT uq_group_members_group_id_user_id UNIQUE (group_id, user_id), \n\tCONSTRAINT fk_group_members_group_id_groups FOREIGN KEY(group_id) REFERENCES groups (id) ON DELETE CASCADE, \n\tCONSTRAINT fk_group_members_user_id_users FOREIGN KEY(user_id) REFERENCES users (id), \n\tCONSTRAINT ck_group_members_membership_status CHECK (status IN ('invited', 'accepted')), \n\tCONSTRAINT fk_group_members_invited_by_users FOREIGN KEY(invited_by) REFERENCES users (id)\n);",
    "CREATE INDEX ix_group_members_group_id ON group_members (group_id);",
    "CREATE INDEX ix_group_members_user_id ON group_members (user_id);",
    "CREATE TABLE card_copies (\n\tid UUID NOT NULL, \n\tcatalog_card_id UUID NOT NULL, \n\tholder_id UUID NOT NULL, \n\tadded_by_id UUID NOT NULL, \n\tprice_cents INTEGER, \n\tprice_fetched_at TIMESTAMP WITH TIME ZONE, \n\tstate VARCHAR(32) NOT NULL, \n\tlocked BOOLEAN NOT NULL, \n\tdeck_id UUID, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_card_copies PRIMARY KEY (id), \n\tCONSTRAINT ck_card_copies_state_lock_deck CHECK ((state = 'available' AND deck_id IS NULL AND locked = false) OR (state = 'reserved' AND locked = true) OR (state = 'in_deck' AND deck_id IS NOT NULL)), \n\tCONSTRAINT fk_card_copies_catalog_card_id_catalog_cards FOREIGN KEY(catalog_card_id) REFERENCES catalog_cards (id), \n\tCONSTRAINT fk_card_copies_holder_id_users FOREIGN KEY(holder_id) REFERENCES users (id), \n\tCONSTRAINT fk_card_copies_added_by_id_users FOREIGN KEY(added_by_id) REFERENCES users (id), \n\tCONSTRAINT ck_card_copies_copy_state CHECK (state IN ('available', 'reserved', 'in_deck')), \n\tCONSTRAINT fk_card_copies_deck_id_decks FOREIGN KEY(deck_id) REFERENCES decks (id) ON DELETE SET NULL\n);",
    "CREATE INDEX ix_card_copies_catalog_card_id ON card_copies (catalog_card_id);",
    "CREATE INDEX ix_card_copies_deck_id ON card_copies (deck_id);",
    "CREATE INDEX ix_card_copies_holder_id ON card_copies (holder_id);",
    "CREATE TABLE card_copy_groups (\n\tcard_copy_id UUID NOT NULL, \n\tgroup_id UUID NOT NULL, \n\tCONSTRAINT pk_card_copy_groups PRIMARY KEY (card_copy_id, group_id), \n\tCONSTRAINT fk_card_copy_groups_card_copy_id_card_copies FOREIGN KEY(card_copy_id) REFERENCES card_copies (id) ON DELETE CASCADE, \n\tCONSTRAINT fk_card_copy_groups_group_id_groups FOREIGN KEY(group_id) REFERENCES groups (id) ON DELETE CASCADE\n);",
    "CREATE INDEX ix_card_copy_groups_group_id ON card_copy_groups (group_id);",
    "CREATE TABLE deck_cards (\n\tdeck_id UUID NOT NULL, \n\tcard_copy_id UUID NOT NULL, \n\trole VARCHAR(32) NOT NULL, \n\tCONSTRAINT pk_deck_cards PRIMARY KEY (card_copy_id), \n\tCONSTRAINT fk_deck_cards_deck_id_decks FOREIGN KEY(deck_id) REFERENCES decks (id) ON DELETE CASCADE, \n\tCONSTRAINT fk_deck_cards_card_copy_id_card_copies FOREIGN KEY(card_copy_id) REFERENCES card_copies (id) ON DELETE CASCADE, \n\tCONSTRAINT ck_deck_cards_deck_role CHECK (role IN ('commander', 'main'))\n);",
    "CREATE INDEX ix_deck_cards_deck_id ON deck_cards (deck_id);",
    "CREATE TABLE requests (\n\tid UUID NOT NULL, \n\tcard_copy_id UUID NOT NULL, \n\tgroup_id UUID NOT NULL, \n\trequester_id UUID NOT NULL, \n\tholder_id UUID NOT NULL, \n\tsource VARCHAR(32) NOT NULL, \n\tsource_deck_id UUID, \n\ttarget_deck_id UUID NOT NULL, \n\tstatus VARCHAR(32) NOT NULL, \n\tresolved_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_requests PRIMARY KEY (id), \n\tCONSTRAINT fk_requests_card_copy_id_card_copies FOREIGN KEY(card_copy_id) REFERENCES card_copies (id) ON DELETE CASCADE, \n\tCONSTRAINT fk_requests_group_id_groups FOREIGN KEY(group_id) REFERENCES groups (id) ON DELETE CASCADE, \n\tCONSTRAINT fk_requests_requester_id_users FOREIGN KEY(requester_id) REFERENCES users (id), \n\tCONSTRAINT fk_requests_holder_id_users FOREIGN KEY(holder_id) REFERENCES users (id), \n\tCONSTRAINT ck_requests_request_source CHECK (source IN ('bulk', 'deck')), \n\tCONSTRAINT fk_requests_source_deck_id_decks FOREIGN KEY(source_deck_id) REFERENCES decks (id) ON DELETE CASCADE, \n\tCONSTRAINT fk_requests_target_deck_id_decks FOREIGN KEY(target_deck_id) REFERENCES decks (id) ON DELETE CASCADE, \n\tCONSTRAINT ck_requests_request_status CHECK (status IN ('pending_acceptance', 'awaiting_handoff', 'completed', 'cancelled', 'rejected'))\n);",
    "CREATE INDEX ix_requests_holder_id ON requests (holder_id);",
    "CREATE INDEX ix_requests_requester_id ON requests (requester_id);",
    "CREATE UNIQUE INDEX uq_requests_one_open_per_copy ON requests (card_copy_id) WHERE status IN ('pending_acceptance', 'awaiting_handoff');",
    "CREATE INDEX ix_requests_group_id ON requests (group_id);",
)

_DROP = (
    "requests",
    "deck_cards",
    "card_copy_groups",
    "card_copies",
    "group_members",
    "decks",
    "groups",
    "catalog_cards",
    "users",
)


def upgrade() -> None:
    for statement in _STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for table in _DROP:
        op.execute(f"DROP TABLE IF EXISTS {table}")
