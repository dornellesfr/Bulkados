import pytest
from httpx import AsyncClient
from sqlalchemy import select, text

from app.core.database import SessionFactory
from app.models.user import User
from tests.integration.conftest import FakeAuth, bearer, obj

USERS_URL = "/api/v1/admin/users"


async def register(client: AsyncClient, nick: str) -> dict[str, object]:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": f"{nick}@example.com", "password": "password123", "nick": nick},
    )
    assert response.status_code == 201, response.text
    return obj(response)


async def register_admin(client: AsyncClient, nick: str = "root") -> dict[str, object]:
    created = await register(client, nick)
    async with SessionFactory() as session:
        await session.execute(
            text("UPDATE users SET level = 0 WHERE nick_normalized = :nick"),
            {"nick": nick},
        )
        await session.commit()
    return created


def new_user(nick: str, **extra: object) -> dict[str, object]:
    return {"email": f"{nick}@example.com", "password": "password123", "nick": nick, **extra}


async def level_of(nick: str) -> int:
    async with SessionFactory() as session:
        return (await session.scalars(select(User.level).where(User.nick == nick))).one()


@pytest.mark.integration
async def test_public_registration_creates_a_common_user(client: AsyncClient) -> None:
    await register(client, "ada")

    assert await level_of("ada") == 1


@pytest.mark.integration
async def test_admin_route_requires_a_token(client: AsyncClient) -> None:
    response = await client.post(USERS_URL, json=new_user("maria"))

    assert response.status_code == 401


@pytest.mark.integration
async def test_common_user_cannot_create_users(
    client: AsyncClient,
    auth_provider: FakeAuth,
) -> None:
    ada = await register(client, "ada")

    response = await client.post(
        USERS_URL, json=new_user("maria"), headers=bearer(ada["access_token"])
    )

    assert response.status_code == 403
    assert "maria@example.com" not in auth_provider.users


@pytest.mark.integration
async def test_admin_creates_a_common_user_who_can_log_in(client: AsyncClient) -> None:
    root = await register_admin(client)

    response = await client.post(
        USERS_URL, json=new_user("maria"), headers=bearer(root["access_token"])
    )

    assert response.status_code == 201, response.text
    assert obj(response)["nick"] == "maria"
    assert obj(response)["level"] == 1
    login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "maria", "password": "password123"},
    )
    assert login.status_code == 200


@pytest.mark.integration
async def test_admin_creates_another_admin(client: AsyncClient) -> None:
    root = await register_admin(client)

    created = await client.post(
        USERS_URL,
        json=new_user("second", level=0),
        headers=bearer(root["access_token"]),
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "second", "password": "password123"},
    )
    second_token = obj(login)["access_token"]
    again = await client.post(USERS_URL, json=new_user("third"), headers=bearer(second_token))

    assert created.status_code == 201, created.text
    assert obj(created)["level"] == 0
    assert again.status_code == 201, again.text


@pytest.mark.integration
async def test_admin_cannot_reuse_a_nick_or_invent_a_level(client: AsyncClient) -> None:
    root = await register_admin(client)
    headers = bearer(root["access_token"])
    await client.post(USERS_URL, json=new_user("maria"), headers=headers)

    taken = await client.post(USERS_URL, json=new_user("Maria"), headers=headers)
    bad_level = await client.post(USERS_URL, json=new_user("joao", level=2), headers=headers)

    assert taken.status_code == 409
    assert bad_level.status_code == 422


@pytest.mark.integration
async def test_public_registration_cannot_take_the_admin_nick(
    client: AsyncClient,
    auth_provider: FakeAuth,
) -> None:
    for nick in ("bulkados", "Bulkados"):
        response = await client.post("/api/v1/auth/register", json=new_user(nick))

        assert response.status_code == 409
        assert obj(response) == {"detail": "nick already taken"}
    assert auth_provider.users == {}
