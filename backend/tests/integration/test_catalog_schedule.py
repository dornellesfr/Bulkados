import asyncio
from uuid import UUID

import pytest
from sqlalchemy import func, select, text

from app.core.database import SessionFactory
from app.domain.enums import CommanderLegal
from app.domain.scryfall import CatalogDraft
from app.models.catalog import CatalogCard
from app.schemas.admin import CatalogSyncStatus
from app.services import catalog_control
from tests.integration.conftest import FakeCatalogSource


def _draft() -> CatalogDraft:
    return CatalogDraft(
        oracle_id=UUID(int=1),
        name_en="Abrade",
        name_pt=None,
        mana_cost="{1}{R}",
        image_url=None,
        type_line="Instant",
        oracle_text="",
        color_identity=("R",),
        keywords=(),
        is_basic=False,
        any_number_allowed=False,
        commander_legal=CommanderLegal.legal,
        can_be_commander=False,
        partner_kind=None,
    )


async def _synced_days_ago(days: int, interval_days: int | None = None) -> None:
    async with SessionFactory() as session:
        await catalog_control.get_status(session)
        await session.execute(
            text("UPDATE catalog_sync SET last_synced_at = now() - make_interval(days => :days)"),
            {"days": days},
        )
        if interval_days is not None:
            await catalog_control.set_interval(session, interval_days)
        await session.commit()


async def _due() -> bool:
    async with SessionFactory() as session:
        due = await catalog_control.is_due(session)
        await session.commit()
        return due


async def _wait_until_idle() -> None:
    for _ in range(200):
        async with SessionFactory() as session:
            status = await catalog_control.get_status(session)
            await session.commit()
        if not status.running:
            return
        await asyncio.sleep(0.05)
    message = "a atualização não terminou"
    raise AssertionError(message)


async def _status() -> CatalogSyncStatus:
    async with SessionFactory() as session:
        status = await catalog_control.get_status(session)
        await session.commit()
        return status


@pytest.mark.integration
@pytest.mark.usefixtures("client")
async def test_a_catalog_never_synced_is_due() -> None:
    assert await _due() is True


@pytest.mark.integration
@pytest.mark.usefixtures("client")
async def test_it_becomes_due_only_after_the_interval() -> None:
    await _synced_days_ago(10)
    assert await _due() is False

    await _synced_days_ago(91)
    assert await _due() is True

    await _synced_days_ago(10, interval_days=5)
    assert await _due() is True


@pytest.mark.integration
@pytest.mark.usefixtures("client")
async def test_sync_if_due_loads_once_and_then_waits_for_the_interval(
    catalog_source: FakeCatalogSource,
) -> None:
    catalog_source.drafts = [_draft()]

    first = await catalog_control.sync_if_due(catalog_source)
    await _wait_until_idle()
    second = await catalog_control.sync_if_due(catalog_source)

    async with SessionFactory() as session:
        total = await session.scalar(select(func.count()).select_from(CatalogCard))
    assert (first, second) == (True, False)
    assert total == 1
    assert (await _status()).last_synced_at is not None


@pytest.mark.integration
@pytest.mark.usefixtures("client")
async def test_sync_if_due_does_not_start_a_second_run(
    catalog_source: FakeCatalogSource,
) -> None:
    catalog_source.gate = asyncio.Event()

    first = await catalog_control.sync_if_due(catalog_source)
    second = await catalog_control.sync_if_due(catalog_source)
    catalog_source.gate.set()
    await _wait_until_idle()

    assert (first, second) == (True, False)


@pytest.mark.integration
@pytest.mark.usefixtures("client")
async def test_stopping_records_that_the_run_was_interrupted(
    catalog_source: FakeCatalogSource,
) -> None:
    catalog_source.gate = asyncio.Event()
    await catalog_control.start_sync(catalog_source)

    await catalog_control.stop_syncs()

    status = await _status()
    assert status.running is False
    assert status.last_synced_at is None
    assert "interrompida" in str(status.last_error)


@pytest.mark.integration
@pytest.mark.usefixtures("client")
async def test_the_scheduler_does_nothing_in_the_test_environment() -> None:
    await asyncio.wait_for(catalog_control.run_scheduler(), timeout=2)

    assert (await _status()).last_synced_at is None
