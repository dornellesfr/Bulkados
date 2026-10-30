from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import select

from app.core.config import Environment, Settings
from app.core.database import SessionFactory
from app.models.user import User
from app.services.admin_bootstrap import DEVELOPMENT_ADMIN_PASSWORD, ensure_admin
from tests.integration.conftest import FakeAuth

EMAIL = "admin@example.com"


def _settings(
    *,
    environment: Environment = "development",
    email: str = EMAIL,
    password: str = "",
) -> Settings:
    return Settings(
        environment=environment,
        admin_email=email,
        admin_password=SecretStr(password),
        supabase_url="https://example.supabase.co",
        supabase_jwt_secret=SecretStr("test-secret"),
    )


async def _ensure(auth: FakeAuth, settings: Settings) -> None:
    async with SessionFactory() as session:
        await ensure_admin(session, auth, settings)
        await session.commit()


async def _users() -> list[User]:
    async with SessionFactory() as session:
        return list((await session.scalars(select(User))).all())


@pytest.mark.integration
@pytest.mark.usefixtures("client")
async def test_creates_the_admin_with_the_development_password(auth_provider: FakeAuth) -> None:
    await _ensure(auth_provider, _settings())

    [admin] = await _users()
    assert (admin.nick, admin.email, admin.level) == ("bulkados", EMAIL, 0)
    assert auth_provider.users[EMAIL][0] == DEVELOPMENT_ADMIN_PASSWORD


@pytest.mark.integration
@pytest.mark.usefixtures("client")
async def test_a_second_start_changes_nothing(auth_provider: FakeAuth) -> None:
    await _ensure(auth_provider, _settings())
    [first] = await _users()

    await _ensure(auth_provider, _settings())

    [second] = await _users()
    assert second.id == first.id
    assert len(auth_provider.users) == 1


@pytest.mark.integration
@pytest.mark.usefixtures("client")
async def test_a_configured_password_wins(auth_provider: FakeAuth) -> None:
    await _ensure(auth_provider, _settings(password="a-much-better-pass"))

    assert auth_provider.users[EMAIL][0] == "a-much-better-pass"


@pytest.mark.integration
@pytest.mark.usefixtures("client")
async def test_without_email_or_outside_development_without_password_nothing_is_created(
    auth_provider: FakeAuth,
) -> None:
    await _ensure(auth_provider, _settings(email=""))
    await _ensure(auth_provider, _settings(environment="production"))

    assert await _users() == []
    assert auth_provider.users == {}


@pytest.mark.integration
@pytest.mark.usefixtures("client")
async def test_never_promotes_an_existing_common_user(auth_provider: FakeAuth) -> None:
    async with SessionFactory() as session:
        session.add(
            User(
                id=uuid4(),
                email="squatter@example.com",
                nick="bulkados",
                nick_normalized="bulkados",
            )
        )
        await session.commit()

    await _ensure(auth_provider, _settings())

    [user] = await _users()
    assert user.level == 1
    assert auth_provider.users == {}


@pytest.mark.integration
@pytest.mark.usefixtures("client")
async def test_reuses_an_account_that_already_exists_in_the_auth_provider(
    auth_provider: FakeAuth,
) -> None:
    existing_id = uuid4()
    auth_provider.users[EMAIL] = (DEVELOPMENT_ADMIN_PASSWORD, existing_id)

    await _ensure(auth_provider, _settings())

    [admin] = await _users()
    assert admin.id == existing_id
    assert admin.level == 0


@pytest.mark.integration
@pytest.mark.usefixtures("client")
async def test_skips_when_the_provider_has_the_email_with_another_password(
    auth_provider: FakeAuth,
) -> None:
    auth_provider.users[EMAIL] = ("someone-elses-password", uuid4())

    await _ensure(auth_provider, _settings())

    assert await _users() == []
