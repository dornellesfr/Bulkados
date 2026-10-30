from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.domain.cards import is_doctor, partner_with_name
from app.domain.enums import CommanderLegal, DeckFormat, DeckRole, PartnerKind

COMMANDER_10_MAIN_LIMIT_CENTS = 1000
COMMANDER_10_COMMANDER_LIMIT_CENTS = 500
COMMANDER_SIZE = 100


@dataclass(frozen=True, slots=True)
class DeckCardFact:
    card_copy_id: UUID
    name_en: str
    price_cents: int | None
    is_basic: bool
    any_number_allowed: bool
    color_identity: tuple[str, ...]
    commander_legal: CommanderLegal
    can_be_commander: bool
    partner_kind: PartnerKind | None
    oracle_text: str
    type_line: str
    keywords: tuple[str, ...]
    role: DeckRole


@dataclass(frozen=True, slots=True)
class DeckWarning:
    code: str
    message: str
    card_copy_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class DeckEvaluation:
    card_count: int
    main_price_cents: int
    commander_price_cents: int
    warnings: tuple[DeckWarning, ...]


def evaluate_deck(cards: Sequence[DeckCardFact], deck_format: DeckFormat) -> DeckEvaluation:
    """Avisos calculados na leitura. Nenhum deles impede a escrita do deck."""
    commanders = [card for card in cards if card.role is DeckRole.commander]
    main_cards = [card for card in cards if card.role is DeckRole.main]
    main_price = _priced_sum(main_cards)
    commander_price = _priced_sum(commanders)
    warnings: list[DeckWarning] = []
    warnings.extend(_size_warnings(len(cards)))
    warnings.extend(_duplicate_warnings(cards))
    warnings.extend(_color_warnings(cards, commanders))
    warnings.extend(_banned_warnings(cards))
    warnings.extend(_commander_illegal_warnings(commanders))
    if not _pairing_is_valid(commanders):
        if len(commanders) != 1:
            warnings.append(
                DeckWarning(
                    code="commander_pairing",
                    message="A combinação de comandantes não é válida.",
                )
            )
    warnings.extend(_missing_price_warnings(cards))
    warnings.extend(_budget_warnings(deck_format, main_price, commander_price))
    return DeckEvaluation(
        card_count=len(cards),
        main_price_cents=main_price,
        commander_price_cents=commander_price,
        warnings=tuple(warnings),
    )


def _priced_sum(cards: Sequence[DeckCardFact]) -> int:
    return sum(card.price_cents for card in cards if card.price_cents is not None)


def _size_warnings(card_count: int) -> list[DeckWarning]:
    if card_count > COMMANDER_SIZE:
        return [DeckWarning(code="deck_over_100", message="O deck tem mais de 100 cartas.")]
    if card_count < COMMANDER_SIZE:
        return [DeckWarning(code="deck_under_100", message="O deck tem menos de 100 cartas.")]
    return []


def _duplicate_warnings(cards: Sequence[DeckCardFact]) -> list[DeckWarning]:
    grouped: dict[str, list[DeckCardFact]] = {}
    for card in cards:
        if card.is_basic or card.any_number_allowed:
            continue
        grouped.setdefault(card.name_en.casefold(), []).append(card)
    warnings: list[DeckWarning] = []
    for copies in grouped.values():
        for extra in copies[1:]:
            warnings.append(
                DeckWarning(
                    code="duplicate_name",
                    message=f"Há outra carta com o nome {extra.name_en}.",
                    card_copy_id=extra.card_copy_id,
                )
            )
    return warnings


def _color_warnings(
    cards: Sequence[DeckCardFact],
    commanders: Sequence[DeckCardFact],
) -> list[DeckWarning]:
    if not commanders:
        return []
    allowed: set[str] = set()
    for commander in commanders:
        allowed.update(color.upper() for color in commander.color_identity)
    warnings: list[DeckWarning] = []
    for card in cards:
        identity = {color.upper() for color in card.color_identity}
        if not identity <= allowed:
            warnings.append(
                DeckWarning(
                    code="color_identity",
                    message="A identidade de cor não cabe na dos comandantes.",
                    card_copy_id=card.card_copy_id,
                )
            )
    return warnings


def _banned_warnings(cards: Sequence[DeckCardFact]) -> list[DeckWarning]:
    return [
        DeckWarning(
            code="banned",
            message="Carta banida no Commander.",
            card_copy_id=card.card_copy_id,
        )
        for card in cards
        if card.commander_legal is CommanderLegal.banned
    ]


def _commander_illegal_warnings(commanders: Sequence[DeckCardFact]) -> list[DeckWarning]:
    warnings: list[DeckWarning] = []
    for commander in commanders:
        if commander.can_be_commander:
            continue
        if _partner_kind_sustains(commander, commanders):
            continue
        warnings.append(
            DeckWarning(
                code="commander_illegal",
                message="Esta carta não pode ser comandante.",
                card_copy_id=commander.card_copy_id,
            )
        )
    return warnings


def _missing_price_warnings(cards: Sequence[DeckCardFact]) -> list[DeckWarning]:
    return [
        DeckWarning(
            code="missing_price",
            message="Preço desconhecido; esta carta não entra na soma.",
            card_copy_id=card.card_copy_id,
        )
        for card in cards
        if not card.is_basic and card.price_cents is None
    ]


def _budget_warnings(
    deck_format: DeckFormat,
    main_price_cents: int,
    commander_price_cents: int,
) -> list[DeckWarning]:
    """Teto por formato. Commander 100, 200 e 500 ficam sem teto até a regra existir."""
    if deck_format is not DeckFormat.commander_10:
        return []
    warnings: list[DeckWarning] = []
    if main_price_cents > COMMANDER_10_MAIN_LIMIT_CENTS:
        warnings.append(
            DeckWarning(
                code="budget_main",
                message="A soma das cartas passa de R$ 10.",
            )
        )
    if commander_price_cents > COMMANDER_10_COMMANDER_LIMIT_CENTS:
        warnings.append(
            DeckWarning(
                code="budget_commanders",
                message="A soma dos comandantes passa de R$ 5.",
            )
        )
    return warnings


def _pairing_is_valid(commanders: Sequence[DeckCardFact]) -> bool:
    if len(commanders) == 1:
        return commanders[0].can_be_commander
    if len(commanders) != 2:
        return False
    left, right = commanders
    if left.partner_kind is PartnerKind.partner and right.partner_kind is PartnerKind.partner:
        return True
    if (
        left.partner_kind is PartnerKind.friends_forever
        and right.partner_kind is PartnerKind.friends_forever
    ):
        return True
    if (
        left.partner_kind is PartnerKind.partner_with
        and right.partner_kind is PartnerKind.partner_with
        and _names_point_at_each_other(left, right)
    ):
        return True
    kinds = {left.partner_kind, right.partner_kind}
    if kinds == {PartnerKind.choose_a_background, PartnerKind.background}:
        return True
    return _is_doctor_pair(left, right)


def _partner_kind_sustains(card: DeckCardFact, commanders: Sequence[DeckCardFact]) -> bool:
    if len(commanders) != 2:
        return False
    other = commanders[0] if commanders[1].card_copy_id == card.card_copy_id else commanders[1]
    kind = card.partner_kind
    if kind is PartnerKind.background:
        return other.partner_kind is PartnerKind.choose_a_background
    if kind is PartnerKind.choose_a_background:
        return other.partner_kind is PartnerKind.background
    if kind is PartnerKind.doctors_companion:
        return is_doctor(other.type_line, other.keywords)
    if kind is PartnerKind.partner:
        return other.partner_kind is PartnerKind.partner
    if kind is PartnerKind.friends_forever:
        return other.partner_kind is PartnerKind.friends_forever
    if kind is PartnerKind.partner_with:
        return other.partner_kind is PartnerKind.partner_with and _names_point_at_each_other(
            card, other
        )
    return False


def _is_doctor_pair(left: DeckCardFact, right: DeckCardFact) -> bool:
    left_is_doctor = is_doctor(left.type_line, left.keywords)
    right_is_doctor = is_doctor(right.type_line, right.keywords)
    if left_is_doctor and right.partner_kind is PartnerKind.doctors_companion:
        return True
    return right_is_doctor and left.partner_kind is PartnerKind.doctors_companion


def _names_point_at_each_other(left: DeckCardFact, right: DeckCardFact) -> bool:
    left_target = partner_with_name(left.keywords, left.oracle_text)
    right_target = partner_with_name(right.keywords, right.oracle_text)
    if left_target is None or right_target is None:
        return False
    return (
        left_target.casefold() == right.name_en.casefold()
        and right_target.casefold() == left.name_en.casefold()
    )
