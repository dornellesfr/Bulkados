import re
from collections.abc import Sequence

from app.domain.enums import PartnerKind

BASIC_LAND_NAMES: frozenset[str] = frozenset(
    {
        "Plains",
        "Island",
        "Swamp",
        "Mountain",
        "Forest",
        "Wastes",
        "Snow-Covered Plains",
        "Snow-Covered Island",
        "Snow-Covered Swamp",
        "Snow-Covered Mountain",
        "Snow-Covered Forest",
    }
)

_ANY_NUMBER = "a deck can have any number of cards named"
_CAN_BE_COMMANDER = "can be your commander"
_PARTNER_WITH = re.compile(r"partner with\s+([^(\n]+)", re.IGNORECASE)
_DOCTOR = re.compile(r"\bDoctor\b")


def is_basic_land(name_en: str, type_line: str) -> bool:
    if name_en in BASIC_LAND_NAMES:
        return True
    lowered = type_line.lower()
    return "basic" in lowered and "land" in lowered


def allows_any_number(oracle_text: str) -> bool:
    return _ANY_NUMBER in oracle_text.lower()


def can_be_commander(type_line: str, oracle_text: str) -> bool:
    if _is_legendary_creature(type_line):
        return True
    return _CAN_BE_COMMANDER in oracle_text.lower()


def is_doctor(type_line: str, keywords: Sequence[str]) -> bool:
    if not _is_legendary_creature(type_line):
        return False
    if any(keyword.casefold() == "doctor" for keyword in keywords):
        return True
    return _DOCTOR.search(type_line) is not None


def partner_kind_of(
    keywords: Sequence[str],
    oracle_text: str,
    type_line: str,
) -> PartnerKind | None:
    lowered_keywords = [keyword.casefold() for keyword in keywords]
    if any(keyword.startswith("partner with") for keyword in lowered_keywords):
        return PartnerKind.partner_with
    if _oracle_line_starts_with(oracle_text, "partner with"):
        return PartnerKind.partner_with
    if "partner" in lowered_keywords or _oracle_line_starts_with(oracle_text, "partner"):
        return PartnerKind.partner
    if "friends forever" in lowered_keywords or _oracle_line_starts_with(
        oracle_text, "friends forever"
    ):
        return PartnerKind.friends_forever
    if "choose a background" in lowered_keywords or _oracle_line_starts_with(
        oracle_text, "choose a background"
    ):
        return PartnerKind.choose_a_background
    if "doctor's companion" in lowered_keywords or _oracle_line_starts_with(
        oracle_text, "doctor's companion"
    ):
        return PartnerKind.doctors_companion
    if "background" in lowered_keywords or "background" in type_line.casefold():
        return PartnerKind.background
    return None


def partner_with_name(keywords: Sequence[str], oracle_text: str) -> str | None:
    for keyword in keywords:
        if keyword.casefold().startswith("partner with "):
            return keyword.split(" ", 2)[2].strip()
    match = _PARTNER_WITH.search(oracle_text)
    if match is None:
        return None
    return match.group(1).strip().rstrip(".")


def price_is_free_basic(name_en: str, is_basic: bool) -> bool:
    return is_basic or name_en in BASIC_LAND_NAMES


def _is_legendary_creature(type_line: str) -> bool:
    lowered = type_line.casefold()
    return "legendary" in lowered and "creature" in lowered


def _oracle_line_starts_with(oracle_text: str, prefix: str) -> bool:
    for line in oracle_text.splitlines():
        if line.strip().casefold().startswith(prefix):
            return True
    return False
