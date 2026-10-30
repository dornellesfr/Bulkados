from uuid import UUID

from app.domain.enums import CommanderLegal, PartnerKind
from app.domain.scryfall import catalog_draft_from_scryfall


def test_parses_rules_fields_from_a_scryfall_card() -> None:
    draft = catalog_draft_from_scryfall(
        {
            "oracle_id": "00000000-0000-0000-0000-000000000001",
            "name": "Sol Ring",
            "mana_cost": "{1}",
            "type_line": "Artifact",
            "oracle_text": "Tap: Add {C}{C}.",
            "color_identity": [],
            "keywords": [],
            "legalities": {"commander": "legal"},
            "lang": "en",
        }
    )

    assert draft is not None
    assert draft.oracle_id == UUID("00000000-0000-0000-0000-000000000001")
    assert draft.mana_cost == "{1}"
    assert draft.can_be_commander is False
    assert draft.commander_legal is CommanderLegal.legal
    assert draft.partner_kind is None
    assert draft.is_basic is False


def test_portuguese_print_keeps_the_english_name() -> None:
    draft = catalog_draft_from_scryfall(
        {
            "oracle_id": "00000000-0000-0000-0000-000000000002",
            "name": "Lightning Bolt",
            "printed_name": "Raio",
            "lang": "pt",
            "type_line": "Instant",
            "oracle_text": "Lightning Bolt deals 3 damage to any target.",
            "color_identity": ["R"],
            "keywords": [],
            "legalities": {"commander": "legal"},
        }
    )

    assert draft is not None
    assert draft.name_en == "Lightning Bolt"
    assert draft.name_pt == "Raio"


def test_derives_commander_pairing_and_basic_land() -> None:
    basic = catalog_draft_from_scryfall(
        {
            "oracle_id": "00000000-0000-0000-0000-000000000003",
            "name": "Snow-Covered Island",
            "type_line": "Basic Snow Land — Island",
            "oracle_text": "({T}: Add {U}.)",
            "color_identity": ["U"],
            "keywords": [],
            "legalities": {"commander": "legal"},
        }
    )
    partner = catalog_draft_from_scryfall(
        {
            "oracle_id": "00000000-0000-0000-0000-000000000004",
            "name": "Tymna the Weaver",
            "type_line": "Legendary Creature — Human Cleric",
            "oracle_text": "Partner with Akroma, Vision of Ixidor",
            "keywords": ["Partner with Akroma, Vision of Ixidor"],
            "color_identity": ["W", "B"],
            "legalities": {"commander": "legal"},
        }
    )
    background = catalog_draft_from_scryfall(
        {
            "oracle_id": "00000000-0000-0000-0000-000000000005",
            "name": "Haunted One",
            "type_line": "Legendary Enchantment — Background",
            "oracle_text": "Commander creatures you own have menace.",
            "keywords": ["Background"],
            "color_identity": ["B"],
            "legalities": {"commander": "legal"},
        }
    )
    any_number = catalog_draft_from_scryfall(
        {
            "oracle_id": "00000000-0000-0000-0000-000000000006",
            "name": "Relentless Rats",
            "type_line": "Creature — Rat",
            "oracle_text": "A deck can have any number of cards named Relentless Rats.",
            "keywords": [],
            "color_identity": ["B"],
            "legalities": {"commander": "banned"},
        }
    )
    text_commander = catalog_draft_from_scryfall(
        {
            "oracle_id": "00000000-0000-0000-0000-000000000007",
            "name": "The Prismatic Piper",
            "type_line": "Legendary Creature — Shapeshifter",
            "oracle_text": "This card can be your commander.",
            "keywords": [],
            "color_identity": [],
            "legalities": {"commander": "legal"},
        }
    )

    assert basic is not None and basic.is_basic is True
    assert partner is not None and partner.partner_kind is PartnerKind.partner_with
    assert partner.can_be_commander is True
    assert background is not None and background.partner_kind is PartnerKind.background
    assert background.can_be_commander is False
    assert any_number is not None and any_number.any_number_allowed is True
    assert any_number.commander_legal is CommanderLegal.banned
    assert text_commander is not None and text_commander.can_be_commander is True


def test_skips_objects_without_an_oracle_id() -> None:
    assert catalog_draft_from_scryfall({"name": "Token"}) is None
