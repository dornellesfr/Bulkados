import asyncio
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text

from app.api.deps import get_auth_provider, get_catalog_source, get_price_provider
from app.core.config import get_settings
from app.core.database import engine
from app.core.errors import InvalidCredentialsError, RegistrationRejectedError
from app.domain.scryfall import CatalogDraft
from app.integrations.auth import AuthSession
from app.main import create_app
from app.models import Base


class FakeAuth:
    def __init__(self) -> None:
        self.users: dict[str, tuple[str, UUID]] = {}

    async def sign_up(self, email: str, password: str, nick: str) -> UUID:
        del nick
        if email in self.users:
            raise RegistrationRejectedError
        user_id = uuid4()
        self.users[email] = (password, user_id)
        return user_id

    async def sign_in(self, email: str, password: str) -> AuthSession:
        record = self.users.get(email)
        if record is None or record[0] != password:
            raise InvalidCredentialsError
        return AuthSession(
            access_token=_token(record[1]),
            refresh_token=f"refresh-{record[1]}",
            expires_in=3600,
        )

    async def refresh(self, refresh_token: str) -> AuthSession:
        user_id = UUID(refresh_token.removeprefix("refresh-"))
        return AuthSession(
            access_token=_token(user_id),
            refresh_token=refresh_token,
            expires_in=3600,
        )

    async def request_password_reset(self, email: str) -> None:
        del email

    async def delete_user(self, user_id: UUID) -> None:
        self.users = {email: record for email, record in self.users.items() if record[1] != user_id}


class PriceStub:
    def __init__(self) -> None:
        self.cents: int | None = None
        self.calls: list[str] = []

    async def lowest_brl_cents(self, name_en: str) -> int | None:
        self.calls.append(name_en)
        return self.cents


class FakeCatalogSource:
    """Acervo falso: o que ele entrega, se trava num portão e se falha ficam a cargo do teste."""

    def __init__(self) -> None:
        self.drafts: list[CatalogDraft] = []
        self.names: list[tuple[UUID, str]] = []
        self.gate: asyncio.Event | None = None
        self.error: Exception | None = None

    async def oracle_cards(self) -> AsyncIterator[CatalogDraft]:
        if self.gate is not None:
            await self.gate.wait()
        if self.error is not None:
            raise self.error
        for draft in self.drafts:
            yield draft

    async def portuguese_names(self) -> AsyncIterator[tuple[UUID, str]]:
        for pair in self.names:
            yield pair


def _token(user_id: UUID) -> str:
    encoded = jwt.encode(
        {
            "sub": str(user_id),
            "aud": "authenticated",
            "iss": "https://example.supabase.co/auth/v1",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        "test-secret",
        algorithm="HS256",
    )
    if isinstance(encoded, str):
        return encoded
    return encoded.decode()


@pytest.fixture
def auth_provider() -> FakeAuth:
    return FakeAuth()


@pytest.fixture
def prices() -> PriceStub:
    return PriceStub()


@pytest.fixture
def catalog_source() -> FakeCatalogSource:
    return FakeCatalogSource()


@pytest.fixture
async def client(
    auth_provider: FakeAuth,
    prices: PriceStub,
    catalog_source: FakeCatalogSource,
) -> AsyncIterator[AsyncClient]:
    os.environ["SUPABASE_URL"] = "https://example.supabase.co"
    os.environ["SUPABASE_JWT_SECRET"] = "test-secret"
    get_settings.cache_clear()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.execute(
            text(
                "TRUNCATE requests, deck_cards, card_copy_groups, card_copies, "
                "decks, group_members, groups, catalog_cards, catalog_sync, users "
                "RESTART IDENTITY CASCADE"
            )
        )
    application = create_app()
    application.dependency_overrides[get_auth_provider] = lambda: auth_provider
    application.dependency_overrides[get_price_provider] = lambda: prices
    application.dependency_overrides[get_catalog_source] = lambda: catalog_source
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


def obj(response: Response) -> dict[str, object]:
    payload: object = response.json()
    assert isinstance(payload, dict)
    return {key: value for key, value in payload.items() if isinstance(key, str)}


def rows(response: Response) -> list[dict[str, object]]:
    payload: object = response.json()
    assert isinstance(payload, list)
    parsed: list[dict[str, object]] = []
    for item in payload:
        assert isinstance(item, dict)
        parsed.append({key: value for key, value in item.items() if isinstance(key, str)})
    return parsed


def bearer(token: object) -> dict[str, str]:
    assert isinstance(token, str)
    return {"Authorization": f"Bearer {token}"}
