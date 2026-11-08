import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import bindparam, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.scryfall import CatalogDraft
from app.domain.search import normalize_search_text
from app.integrations.scryfall import CatalogSource
from app.models.catalog import CatalogCard

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 1000
_REFRESHED_COLUMNS = (
    "name_en",
    "search_en",
    "mana_cost",
    "image_url",
    "type_line",
    "oracle_text",
    "color_identity",
    "keywords",
    "is_basic",
    "any_number_allowed",
    "commander_legal",
    "can_be_commander",
    "partner_kind",
)


@dataclass(frozen=True, slots=True)
class SyncSummary:
    cards: int
    portuguese_names: int


async def sync_catalog(session: AsyncSession, source: CatalogSource) -> SyncSummary:
    """Copia o acervo do Scryfall para `catalog_cards`, confirmando a cada lote.

    Repetir a carga só atualiza: um nome em português já guardado não se perde, e o que
    foi gravado antes de uma falha continua valendo.
    """
    cards = 0
    async for drafts in _chunks(source.oracle_cards()):
        await _upsert_cards(session, drafts)
        await session.commit()
        cards += len(drafts)
    names = 0
    async for pairs in _chunks(source.portuguese_names()):
        await _set_portuguese_names(session, pairs)
        await session.commit()
        names += len(pairs)
    logger.info("catalogo sincronizado: %s cartas, %s nomes em portugues", cards, names)
    return SyncSummary(cards=cards, portuguese_names=names)


async def _chunks[T](items: AsyncIterator[T]) -> AsyncIterator[list[T]]:
    chunk: list[T] = []
    async for item in items:
        chunk.append(item)
        if len(chunk) == _CHUNK_SIZE:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


async def _upsert_cards(session: AsyncSession, drafts: list[CatalogDraft]) -> None:
    rows = {draft.oracle_id: _row(draft) for draft in drafts}
    statement = insert(CatalogCard).values(list(rows.values()))
    statement = statement.on_conflict_do_update(
        index_elements=[CatalogCard.oracle_id],
        set_={column: statement.excluded[column] for column in _REFRESHED_COLUMNS},
    )
    await session.execute(statement)


def _row(draft: CatalogDraft) -> dict[str, object]:
    return {
        "id": uuid4(),
        "oracle_id": draft.oracle_id,
        "name_en": draft.name_en,
        "name_pt": draft.name_pt,
        "search_en": normalize_search_text(draft.name_en),
        "search_pt": normalize_search_text(draft.name_pt) if draft.name_pt else None,
        "mana_cost": draft.mana_cost,
        "image_url": draft.image_url,
        "type_line": draft.type_line,
        "oracle_text": draft.oracle_text,
        "color_identity": list(draft.color_identity),
        "keywords": list(draft.keywords),
        "is_basic": draft.is_basic,
        "any_number_allowed": draft.any_number_allowed,
        "commander_legal": draft.commander_legal,
        "can_be_commander": draft.can_be_commander,
        "partner_kind": draft.partner_kind,
    }


async def _set_portuguese_names(session: AsyncSession, pairs: list[tuple[UUID, str]]) -> None:
    statement = (
        update(CatalogCard)
        .where(CatalogCard.oracle_id == bindparam("target"))
        .values(name_pt=bindparam("name"), search_pt=bindparam("search"))
    )
    connection = await session.connection()
    await connection.execute(
        statement,
        [
            {"target": oracle_id, "name": name, "search": normalize_search_text(name)}
            for oracle_id, name in pairs
        ],
    )
