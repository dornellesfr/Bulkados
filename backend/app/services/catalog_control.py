import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import SessionFactory
from app.integrations.scryfall import CatalogSource, scryfall_client
from app.models.catalog_sync import CatalogSync
from app.schemas.admin import CatalogSyncStatus
from app.services.catalog_sync import sync_catalog

logger = logging.getLogger(__name__)

# Uma carga leva minutos. Passado esse prazo, uma execução "em andamento" é dada como morta
# (o processo caiu no meio) e pode ser refeita.
STALE_AFTER = timedelta(hours=1)
_ERROR_LIMIT = 500
# De quanto em quanto tempo o servidor confere se a atualização venceu. O intervalo é em dias,
# então a conferência não precisa ser frequente.
CHECK_EVERY_SECONDS = 6 * 60 * 60

_tasks: set[asyncio.Task[None]] = set()


async def get_status(session: AsyncSession) -> CatalogSyncStatus:
    row = await _row(session)
    running = row.running_since is not None and row.running_since > _stale_before()
    return CatalogSyncStatus(
        interval_days=row.interval_days,
        last_synced_at=row.last_synced_at,
        running=running,
        last_error=row.last_error,
    )


async def set_interval(session: AsyncSession, days: int) -> CatalogSyncStatus:
    await _row(session)
    await session.execute(update(CatalogSync).where(CatalogSync.id == 1).values(interval_days=days))
    return await get_status(session)


async def is_due(session: AsyncSession) -> bool:
    """Nunca atualizado, ou o intervalo configurado já passou desde a última atualização."""
    row = await _row(session)
    if row.last_synced_at is None:
        return True
    return datetime.now(UTC) >= row.last_synced_at + timedelta(days=row.interval_days)


async def sync_if_due(source: CatalogSource) -> bool:
    async with SessionFactory() as session:
        due = await is_due(session)
        await session.commit()
    return due and await start_sync(source)


async def run_scheduler() -> None:
    """Atualiza o acervo na primeira subida e sempre que o intervalo vence."""
    if get_settings().environment == "test":
        return
    source = scryfall_client()
    while True:
        try:
            if await sync_if_due(source):
                logger.info("catálogo: atualização iniciada pelo agendamento")
        except Exception:
            logger.exception("catálogo: falha ao conferir o agendamento")
        await asyncio.sleep(CHECK_EVERY_SECONDS)


async def stop_syncs() -> None:
    """Interrompe as atualizações em andamento, para o estado ficar registrado."""
    tasks = list(_tasks)
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    if any(task.cancelled() for task in tasks):
        await _finish("interrompida antes de terminar")


async def start_sync(source: CatalogSource) -> bool:
    """Reserva a execução e a inicia em segundo plano. Falso se já houver uma em andamento."""
    if not await _claim():
        return False
    task = asyncio.create_task(run_claimed_sync(source))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return True


async def run_claimed_sync(source: CatalogSource) -> None:
    """Roda a carga e registra o resultado. Quem chama já reservou a execução."""
    error: str | None = None
    try:
        async with SessionFactory() as session:
            await sync_catalog(session, source)
    except Exception as exc:
        logger.exception("catálogo: falha na atualização")
        error = f"{type(exc).__name__}: {exc}"[:_ERROR_LIMIT]
    await _finish(error)


async def _claim() -> bool:
    async with SessionFactory() as session:
        await _row(session)
        claimed = await session.execute(
            update(CatalogSync)
            .where(
                CatalogSync.id == 1,
                or_(
                    CatalogSync.running_since.is_(None), CatalogSync.running_since < _stale_before()
                ),
            )
            .values(running_since=func.now())
            .returning(CatalogSync.id)
        )
        won = claimed.first() is not None
        await session.commit()
        return won


async def _finish(error: str | None) -> None:
    values: dict[str, object] = {"running_since": None, "last_error": error}
    if error is None:
        values["last_synced_at"] = func.now()
    async with SessionFactory() as session:
        await session.execute(update(CatalogSync).where(CatalogSync.id == 1).values(**values))
        await session.commit()


async def _row(session: AsyncSession) -> CatalogSync:
    await session.execute(insert(CatalogSync).values(id=1).on_conflict_do_nothing())
    row = await session.get(CatalogSync, 1, populate_existing=True)
    assert row is not None
    return row


def _stale_before() -> datetime:
    return datetime.now(UTC) - STALE_AFTER
