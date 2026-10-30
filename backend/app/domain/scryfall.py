from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from app.domain.cards import (
    allows_any_number,
    can_be_commander,
    is_basic_land,
    partner_kind_of,
)
from app.domain.enums import CommanderLegal, PartnerKind


@dataclass(frozen=True, slots=True)
class CatalogDraft:
    oracle_id: UUID
    name_en: str
    name_pt: str | None
    mana_cost: str | None
    type_line: str
    oracle_text: str
    color_identity: tuple[str, ...]
    keywords: tuple[str, ...]
    is_basic: bool
    any_number_allowed: bool
    commander_legal: CommanderLegal
    can_be_commander: bool
    partner_kind: PartnerKind | None


def catalog_draft_from_scryfall(payload: Mapping[str, object]) -> CatalogDraft | None:
    oracle_raw = payload.get("oracle_id")
    name_en = payload.get("name")
    if not isinstance(oracle_raw, str) or not isinstance(name_en, str) or not name_en:
        return None
    try:
        oracle_id = UUID(oracle_raw)
    except ValueError:
        return None

    faces = _faces(payload)
    type_line = _text(payload, "type_line") or _join_faces(faces, "type_line")
    oracle_text = _text(payload, "oracle_text") or _join_faces(faces, "oracle_text")
    mana_cost = _text(payload, "mana_cost") or _join_faces(faces, "mana_cost") or None
    keywords = tuple(_string_list(payload, "keywords"))
    color_identity = tuple(_string_list(payload, "color_identity"))
    lang = _text(payload, "lang")
    printed_name = _text(payload, "printed_name")
    name_pt = printed_name if lang == "pt" and printed_name else None
    legal = _commander_legal(payload)
    return CatalogDraft(
        oracle_id=oracle_id,
        name_en=name_en,
        name_pt=name_pt,
        mana_cost=mana_cost or None,
        type_line=type_line,
        oracle_text=oracle_text,
        color_identity=color_identity,
        keywords=keywords,
        is_basic=is_basic_land(name_en, type_line),
        any_number_allowed=allows_any_number(oracle_text),
        commander_legal=legal,
        can_be_commander=can_be_commander(type_line, oracle_text),
        partner_kind=partner_kind_of(keywords, oracle_text, type_line),
    )


def _commander_legal(payload: Mapping[str, object]) -> CommanderLegal:
    legalities = payload.get("legalities")
    if not isinstance(legalities, dict):
        return CommanderLegal.not_legal
    raw = legalities.get("commander")
    if raw == "legal":
        return CommanderLegal.legal
    if raw == "banned":
        return CommanderLegal.banned
    return CommanderLegal.not_legal


def _faces(payload: Mapping[str, object]) -> list[Mapping[str, object]]:
    raw = payload.get("card_faces")
    if not isinstance(raw, list):
        return []
    faces: list[Mapping[str, object]] = []
    for item in raw:
        if isinstance(item, dict):
            faces.append({str(key): value for key, value in item.items()})
    return faces


def _join_faces(faces: list[Mapping[str, object]], key: str) -> str:
    parts = [text for face in faces if (text := _text(face, key))]
    return "\n".join(parts)


def _text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if isinstance(value, str):
        return value
    return ""


def _string_list(payload: Mapping[str, object], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
