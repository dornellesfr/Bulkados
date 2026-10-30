from collections.abc import AsyncIterator, Iterator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_db_session
from app.main import create_app


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_exposes_health_routes(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    payload: object = response.json()
    assert isinstance(payload, dict)
    paths: object = payload["paths"]
    assert isinstance(paths, dict)
    assert "/api/v1/health" in paths
    assert "/api/v1/ready" in paths


def test_unknown_route_returns_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404


@pytest.fixture
def client_with_database() -> Iterator[TestClient]:
    application = create_app()

    async def available_session() -> AsyncIterator[AsyncMock]:
        yield AsyncMock()

    application.dependency_overrides[get_db_session] = available_session
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def client_without_database() -> Iterator[TestClient]:
    application = create_app()

    async def unavailable_session() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.execute.side_effect = SQLAlchemyError("database down")
        yield session

    application.dependency_overrides[get_db_session] = unavailable_session
    with TestClient(application) as test_client:
        yield test_client


def test_ready_returns_ok_when_database_responds(client_with_database: TestClient) -> None:
    response = client_with_database.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_ready_returns_service_unavailable_when_database_is_down(
    client_without_database: TestClient,
) -> None:
    response = client_without_database.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "database unavailable"}
