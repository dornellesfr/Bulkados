from uuid import UUID, uuid4

from app.domain.deck_rules import DeckCardFact, evaluate_deck
from app.domain.enums import CommanderLegal, DeckFormat, DeckRole, PartnerKind


def card(
    *,
    name: str = "Sol Ring",
    role: DeckRole = DeckRole.main,
    price: int | None = 100,
    basic: bool = False,
    any_number: bool = False,
    colors: tuple[str, ...] = (),
    legal: CommanderLegal = CommanderLegal.legal,
    commander: bool = False,
    partner: PartnerKind | None = None,
    oracle: str = "",
    type_line: str = "Artifact",
    keywords: tuple[str, ...] = (),
) -> DeckCardFact:
    return DeckCardFact(
        card_copy_id=uuid4(),
        name_en=name,
        price_cents=price,
        is_basic=basic,
        any_number_allowed=any_number,
        color_identity=colors,
        commander_legal=legal,
        can_be_commander=commander,
        partner_kind=partner,
        oracle_text=oracle,
        type_line=type_line,
        keywords=keywords,
        role=role,
    )


def codes(cards: list[DeckCardFact], deck_format: DeckFormat = DeckFormat.commander_10) -> set[str]:
    return {warning.code for warning in evaluate_deck(cards, deck_format).warnings}


def test_size_warnings_follow_one_hundred_cards() -> None:
    under = [card(name=f"Card {index}") for index in range(99)]
    exact = [card(name=f"Card {index}") for index in range(100)]
    over = [card(name=f"Card {index}") for index in range(101)]

    assert "deck_under_100" in codes(under)
    assert "deck_over_100" not in codes(under)
    assert "deck_under_100" not in codes(exact)
    assert "deck_over_100" not in codes(exact)
    assert "deck_over_100" in codes(over)


def test_commander_10_budget_warns_only_above_the_caps() -> None:
    at_cap = [
        card(name="Main", price=1000),
        card(name="Commander", role=DeckRole.commander, commander=True, price=500),
    ]
    over = [
        card(name="Main", price=1001),
        card(name="Commander", role=DeckRole.commander, commander=True, price=501),
    ]

    assert "budget_main" not in codes(at_cap)
    assert "budget_commanders" not in codes(at_cap)
    assert {"budget_main", "budget_commanders"} <= codes(over)
    evaluation = evaluate_deck(over, DeckFormat.commander_10)
    assert evaluation.main_price_cents == 1001
    assert evaluation.commander_price_cents == 501


def test_other_formats_do_not_warn_about_budget() -> None:
    cards = [card(price=50_000), card(role=DeckRole.commander, commander=True, price=50_000)]

    assert "budget_main" not in codes(cards, DeckFormat.commander_100)
    assert "budget_commanders" not in codes(cards, DeckFormat.competitive)
    assert "budget_main" not in codes(cards, DeckFormat.commander_500)


def test_missing_price_is_excluded_from_the_sum() -> None:
    cards = [card(name="Unknown", price=None), card(name="Known", price=200)]
    evaluation = evaluate_deck(cards, DeckFormat.commander_10)

    assert evaluation.main_price_cents == 200
    assert any(
        warning.code == "missing_price" and warning.card_copy_id is not None
        for warning in evaluation.warnings
    )


def test_basic_land_can_repeat_and_does_not_warn_about_price() -> None:
    basics = [
        card(name="Island", basic=True, price=0, type_line="Basic Land — Island"),
        card(name="Island", basic=True, price=0, type_line="Basic Land — Island"),
    ]

    warnings = codes(basics)
    assert "duplicate_name" not in warnings
    assert "missing_price" not in warnings


def test_duplicate_name_warns_for_the_extra_copy() -> None:
    first = card(name="Sol Ring")
    second = card(name="Sol Ring")
    rats = [
        card(name="Relentless Rats", any_number=True),
        card(name="Relentless Rats", any_number=True),
    ]

    warnings = evaluate_deck([first, second], DeckFormat.commander_10).warnings
    duplicates = [warning for warning in warnings if warning.code == "duplicate_name"]
    assert len(duplicates) == 1
    assert duplicates[0].card_copy_id == second.card_copy_id
    assert "duplicate_name" not in codes(rats)


def test_color_identity_uses_the_commanders_union() -> None:
    commanders = [
        card(
            name="White",
            role=DeckRole.commander,
            commander=True,
            colors=("W",),
            type_line="Legendary Creature — Human",
        ),
        card(
            name="Blue",
            role=DeckRole.commander,
            commander=True,
            colors=("U",),
            partner=PartnerKind.partner,
            type_line="Legendary Creature — Human",
        ),
    ]
    commanders[0] = card(
        name="White",
        role=DeckRole.commander,
        commander=True,
        colors=("W",),
        partner=PartnerKind.partner,
        type_line="Legendary Creature — Human",
    )
    fitting = card(name="Azorius", colors=("W", "U"))
    outside = card(name="Black", colors=("B",))
    colorless = card(name="Sol Ring", colors=())

    warned = codes([*commanders, fitting, outside, colorless])
    assert "color_identity" in warned
    without_commander = codes([outside])
    assert "color_identity" not in without_commander
    assert "commander_pairing" in without_commander


def test_banned_card_warns_without_blocking_the_evaluation() -> None:
    banned = card(name="Griselbrand", legal=CommanderLegal.banned)
    evaluation = evaluate_deck([banned], DeckFormat.commander_10)

    assert evaluation.card_count == 1
    assert any(
        warning.code == "banned" and warning.card_copy_id == banned.card_copy_id
        for warning in evaluation.warnings
    )


def test_single_invalid_commander_is_illegal_and_not_a_pairing_warning() -> None:
    background = card(
        name="Haunted One",
        role=DeckRole.commander,
        partner=PartnerKind.background,
        type_line="Legendary Enchantment — Background",
    )

    warned = codes([background])
    assert "commander_illegal" in warned
    assert "commander_pairing" not in warned


def test_valid_commander_pairs() -> None:
    partner = card(
        name="Tymna",
        role=DeckRole.commander,
        commander=True,
        partner=PartnerKind.partner,
        type_line="Legendary Creature — Human",
    )
    other = card(
        name="Kamahl",
        role=DeckRole.commander,
        commander=True,
        partner=PartnerKind.partner,
        type_line="Legendary Creature — Human",
    )
    assert "commander_pairing" not in codes([partner, other])
    assert "commander_illegal" not in codes([partner, other])

    friends = [
        card(
            name="Friends A",
            role=DeckRole.commander,
            commander=True,
            partner=PartnerKind.friends_forever,
            type_line="Legendary Creature — Human",
        ),
        card(
            name="Friends B",
            role=DeckRole.commander,
            commander=True,
            partner=PartnerKind.friends_forever,
            type_line="Legendary Creature — Human",
        ),
    ]
    assert "commander_pairing" not in codes(friends)


def test_partner_with_requires_both_texts_to_point_at_each_other() -> None:
    left = card(
        name="Tymna the Weaver",
        role=DeckRole.commander,
        commander=True,
        partner=PartnerKind.partner_with,
        keywords=("Partner with Akroma, Vision of Ixidor",),
        type_line="Legendary Creature — Human",
    )
    right = card(
        name="Akroma, Vision of Ixidor",
        role=DeckRole.commander,
        commander=True,
        partner=PartnerKind.partner_with,
        keywords=("Partner with Tymna the Weaver",),
        type_line="Legendary Creature — Angel",
    )
    mismatch = card(
        name="Someone Else",
        role=DeckRole.commander,
        commander=True,
        partner=PartnerKind.partner_with,
        keywords=("Partner with Another Card",),
        type_line="Legendary Creature — Human",
    )

    assert "commander_pairing" not in codes([left, right])
    assert "commander_pairing" in codes([left, mismatch])


def test_background_and_doctor_pairs_are_valid() -> None:
    choose = card(
        name="Faceless One",
        role=DeckRole.commander,
        commander=True,
        partner=PartnerKind.choose_a_background,
        type_line="Legendary Creature — Avatar",
    )
    background = card(
        name="Haunted One",
        role=DeckRole.commander,
        partner=PartnerKind.background,
        type_line="Legendary Enchantment — Background",
    )
    doctor = card(
        name="The Fourth Doctor",
        role=DeckRole.commander,
        commander=True,
        type_line="Legendary Creature — Time Lord Doctor",
    )
    companion = card(
        name="Sarah Jane",
        role=DeckRole.commander,
        partner=PartnerKind.doctors_companion,
        type_line="Legendary Creature — Human",
        keywords=("Doctor's companion",),
    )

    assert "commander_pairing" not in codes([choose, background])
    assert "commander_illegal" not in codes([choose, background])
    assert "commander_pairing" not in codes([doctor, companion])
    assert "commander_illegal" not in codes([doctor, companion])


def test_two_legendary_creatures_without_partner_warn() -> None:
    left = card(
        name="Atraxa",
        role=DeckRole.commander,
        commander=True,
        type_line="Legendary Creature — Phyrexian Angel",
    )
    right = card(
        name="Kenrith",
        role=DeckRole.commander,
        commander=True,
        type_line="Legendary Creature — Human",
    )

    assert "commander_pairing" in codes([left, right])
    assert isinstance(left.card_copy_id, UUID)
