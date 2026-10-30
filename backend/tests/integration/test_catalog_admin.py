import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, update

from app.core.database import SessionFactory
from app.core.errors import CatalogUnavailableError
from app.domain.enums import CommanderLegal
from app.domain.scryfall import CatalogDraft
from app.models.catalog import CatalogCard
from app.models.catalog_sync import CatalogSync
from tests.integration.conftest import FakeCatalogSource, bearer, obj
from tests.integration.test_admin import register, register_admin

STATUS_URL = "/api/v1/admin/catalog/sync"
INTERVAL_URL = "/api/v1/admin/catalog/sync-interval"


def _draft(number: int, name_en: str) -> CatalogDraft:
    return CatalogDraft(
        oracle_id=UUID(f"00000000-0000-0000-0000-{number:012d}"),
        name_en=name_en,
        name_pt=None,
        mana_cost="{R}",
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


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    root = await register_admin(client)
    return bearer(root["access_token"])


async def _wait_until_idle(client: AsyncClient, headers: dict[str, str]) -> dict[str, object]:
    for _ in range(200):
        status = obj(await client.get(STATUS_URL, headers=headers))
        if status["running"] is False:
            return status
        await asyncio.sleep(0.05)
    message = "a atualização não terminou"
    raise AssertionError(message)


async def _card_count() -> int:
    async with SessionFactory() as session:
        return await session.scalar(select(func.count()).select_from(CatalogCard)) or 0


@pytest.mark.integration
@pytest.mark.parametrize(
    ("method", "url"),
    [("GET", STATUS_URL), ("POST", STATUS_URL), ("POST", INTERVAL_URL)],
)
async def test_catalog_admin_routes_need_an_admin(
    client: AsyncClient,
    method: str,
    url: str,
) -> None:
    body = {"days": 30} if url == INTERVAL_URL else None
    ada = await register(client, "ada")

    anonymous = await client.request(method, url, json=body)
    common = await client.request(method, url, json=body, headers=bearer(ada["access_token"]))

    assert anonymous.status_code == 401
    assert common.status_code == 403


@pytest.mark.integration
async def test_status_starts_with_three_months_and_nothing_synced(client: AsyncClient) -> None:
    headers = await _admin_headers(client)

    response = await client.get(STATUS_URL, headers=headers)

    assert response.status_code == 200
    assert obj(response) == {
        "interval_days": 90,
        "last_synced_at": None,
        "running": False,
        "last_error": None,
    }


@pytest.mark.integration
async def test_interval_can_be_changed_within_limits(client: AsyncClient) -> None:
    headers = await _admin_headers(client)

    changed = await client.post(INTERVAL_URL, json={"days": 30}, headers=headers)
    seen = await client.get(STATUS_URL, headers=headers)
    zero = await client.post(INTERVAL_URL, json={"days": 0}, headers=headers)
    huge = await client.post(INTERVAL_URL, json={"days": 4000}, headers=headers)
    text = await client.post(INTERVAL_URL, json={"days": "muito"}, headers=headers)

    assert changed.status_code == 200
    assert obj(changed)["interval_days"] == 30
    assert obj(seen)["interval_days"] == 30
    assert (zero.status_code, huge.status_code, text.status_code) == (422, 422, 422)


@pytest.mark.integration
async def test_forced_sync_loads_the_catalog_and_records_the_date(
    client: AsyncClient,
    catalog_source: FakeCatalogSource,
) -> None:
    catalog_source.drafts = [_draft(1, "Abrade"), _draft(2, "Sol Ring")]
    catalog_source.names = [(UUID(int=1), "Abrasão")]
    headers = await _admin_headers(client)

    response = await client.post(STATUS_URL, headers=headers)
    status = await _wait_until_idle(client, headers)

    assert response.status_code == 202
    assert status["last_error"] is None
    assert status["last_synced_at"] is not None
    assert await _card_count() == 2


@pytest.mark.integration
async def test_a_second_sync_is_refused_while_one_is_running(
    client: AsyncClient,
    catalog_source: FakeCatalogSource,
) -> None:
    catalog_source.drafts = [_draft(1, "Abrade")]
    catalog_source.gate = asyncio.Event()
    headers = await _admin_headers(client)

    first = await client.post(STATUS_URL, headers=headers)
    running = obj(await client.get(STATUS_URL, headers=headers))
    second = await client.post(STATUS_URL, headers=headers)
    catalog_source.gate.set()
    await _wait_until_idle(client, headers)
    third = await client.post(STATUS_URL, headers=headers)
    await _wait_until_idle(client, headers)

    assert first.status_code == 202
    assert running["running"] is True
    assert second.status_code == 409
    assert third.status_code == 202


@pytest.mark.integration
async def test_a_failed_sync_records_the_error_and_a_good_one_clears_it(
    client: AsyncClient,
    catalog_source: FakeCatalogSource,
) -> None:
    catalog_source.error = CatalogUnavailableError()
    headers = await _admin_headers(client)

    await client.post(STATUS_URL, headers=headers)
    failed = await _wait_until_idle(client, headers)
    catalog_source.error = None
    catalog_source.drafts = [_draft(1, "Abrade")]
    await client.post(STATUS_URL, headers=headers)
    recovered = await _wait_until_idle(client, headers)

    assert "CatalogUnavailableError" in str(failed["last_error"])
    assert failed["last_synced_at"] is None
    assert recovered["last_error"] is None
    assert recovered["last_synced_at"] is not None


@pytest.mark.integration
async def test_a_run_stuck_for_hours_can_be_started_again(
    client: AsyncClient,
    catalog_source: FakeCatalogSource,
) -> None:
    catalog_source.drafts = [_draft(1, "Abrade")]
    headers = await _admin_headers(client)
    await client.get(STATUS_URL, headers=headers)
    async with SessionFactory() as session:
        await session.execute(
            update(CatalogSync).values(running_since=datetime.now(UTC) - timedelta(hours=2))
        )
        await session.commit()

    stuck = obj(await client.get(STATUS_URL, headers=headers))
    response = await client.post(STATUS_URL, headers=headers)
    await _wait_until_idle(client, headers)

    assert stuck["running"] is False
    assert response.status_code == 202
    assert await _card_count() == 1
