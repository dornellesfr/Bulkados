from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.database import SessionFactory
from app.domain.enums import CommanderLegal
from app.models.catalog import CatalogCard
from tests.integration.conftest import FakeAuth, PriceStub, bearer, obj, rows


async def register(client: AsyncClient, nick: str) -> dict[str, object]:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": f"{nick}@example.com", "password": "password123", "nick": nick},
    )
    assert response.status_code == 201, response.text
    return obj(response)


def holder_nick(copy: dict[str, object]) -> object:
    holder = copy["holder"]
    assert isinstance(holder, dict)
    return holder["nick"]


async def create_group(client: AsyncClient, token: object, name: str = "Mesa") -> dict[str, object]:
    response = await client.post(
        "/api/v1/groups",
        json={"name": name},
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    return obj(response)


async def insert_catalog(name: str, *, basic: bool = False) -> str:
    async with SessionFactory() as session:
        card = CatalogCard(
            name_en=name,
            name_pt=None,
            type_line="Basic Land — Island" if basic else "Artifact",
            oracle_text="",
            color_identity=[],
            keywords=[],
            is_basic=basic,
            any_number_allowed=False,
            commander_legal=CommanderLegal.legal,
            can_be_commander=False,
            partner_kind=None,
            oracle_id=uuid4(),
        )
        session.add(card)
        await session.commit()
        return str(card.oracle_id)


@pytest.mark.integration
async def test_duplicate_nick_rejects_the_whole_registration(
    client: AsyncClient,
    auth_provider: FakeAuth,
) -> None:
    await register(client, "ada")

    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "password": "password123", "nick": "Ada"},
    )

    assert response.status_code == 409
    assert obj(response) == {"detail": "nick already taken"}
    assert "other@example.com" not in auth_provider.users


@pytest.mark.integration
async def test_login_hides_email_for_nick_and_uses_the_same_error(client: AsyncClient) -> None:
    await register(client, "ada")

    by_nick = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "Ada", "password": "password123"},
    )
    by_email = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "ada@example.com", "password": "password123"},
    )
    wrong_password = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "ada", "password": "nope-nope"},
    )
    unknown_nick = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "nobody", "password": "nope-nope"},
    )

    nick_body = obj(by_nick)
    assert by_nick.status_code == 200
    assert "email" not in nick_body
    assert by_email.status_code == 200
    assert obj(by_email)["email"] == "ada@example.com"
    assert wrong_password.status_code == 401
    assert unknown_nick.status_code == 401
    assert obj(wrong_password) == obj(unknown_nick)

    me = await client.get("/api/v1/me", headers=bearer(nick_body["access_token"]))
    assert me.status_code == 200
    assert set(obj(me)) == {"id", "nick"}
    assert obj(me)["nick"] == "ada"


@pytest.mark.integration
async def test_forgot_password_returns_the_same_message(client: AsyncClient) -> None:
    await register(client, "ada")
    known = await client.post("/api/v1/auth/forgot-password", json={"identifier": "ada"})
    unknown = await client.post("/api/v1/auth/forgot-password", json={"identifier": "nobody"})

    assert known.status_code == 200
    assert obj(known) == obj(unknown)


@pytest.mark.integration
async def test_invite_without_acceptance_hides_the_group(client: AsyncClient) -> None:
    ada = await register(client, "ada")
    grace = await register(client, "grace")
    group = await create_group(client, ada["access_token"])

    invited = await client.post(
        f"/api/v1/groups/{group['id']}/invitations",
        json={"nick": "grace"},
        headers=bearer(ada["access_token"]),
    )
    hidden = await client.get(
        f"/api/v1/groups/{group['id']}/copies",
        headers=bearer(grace["access_token"]),
    )
    accepted = await client.post(
        f"/api/v1/invitations/{obj(invited)['invitation_id']}/accept",
        headers=bearer(grace["access_token"]),
    )
    visible = await client.get(
        f"/api/v1/groups/{group['id']}/copies",
        headers=bearer(grace["access_token"]),
    )

    assert invited.status_code == 201
    assert hidden.status_code == 404
    assert accepted.status_code == 200
    assert visible.status_code == 200


@pytest.mark.integration
async def test_second_bulk_request_conflicts(client: AsyncClient) -> None:
    ada = await register(client, "ada")
    grace = await register(client, "grace")
    linus = await register(client, "linus")
    group = await create_group(client, ada["access_token"])
    for person in (grace, linus):
        invited = await client.post(
            f"/api/v1/groups/{group['id']}/invitations",
            json={"nick": person["nick"]},
            headers=bearer(ada["access_token"]),
        )
        await client.post(
            f"/api/v1/invitations/{obj(invited)['invitation_id']}/accept",
            headers=bearer(person["access_token"]),
        )
    oracle_id = await insert_catalog("Sol Ring")
    created = await client.post(
        f"/api/v1/groups/{group['id']}/copies",
        json={"oracle_id": oracle_id, "quantity": 1},
        headers=bearer(ada["access_token"]),
    )
    copy_id = rows(created)[0]["id"]
    grace_deck = obj(
        await client.post(
            f"/api/v1/groups/{group['id']}/decks",
            json={"name": "Grace", "format": "commander_10"},
            headers=bearer(grace["access_token"]),
        )
    )
    linus_deck = obj(
        await client.post(
            f"/api/v1/groups/{group['id']}/decks",
            json={"name": "Linus", "format": "commander_10"},
            headers=bearer(linus["access_token"]),
        )
    )

    first = await client.post(
        f"/api/v1/decks/{grace_deck['id']}/requests",
        json={"card_copy_id": copy_id},
        headers=bearer(grace["access_token"]),
    )
    second = await client.post(
        f"/api/v1/decks/{linus_deck['id']}/requests",
        json={"card_copy_id": copy_id},
        headers=bearer(linus["access_token"]),
    )

    assert created.status_code == 201
    assert first.status_code == 201
    assert obj(first)["status"] == "awaiting_handoff"
    assert second.status_code == 409


@pytest.mark.integration
async def test_lock_is_visible_from_another_group(client: AsyncClient) -> None:
    ada = await register(client, "ada")
    grace = await register(client, "grace")
    group_one = await create_group(client, ada["access_token"], "Um")
    group_two = await create_group(client, ada["access_token"], "Dois")
    invited = await client.post(
        f"/api/v1/groups/{group_two['id']}/invitations",
        json={"nick": "grace"},
        headers=bearer(ada["access_token"]),
    )
    await client.post(
        f"/api/v1/invitations/{obj(invited)['invitation_id']}/accept",
        headers=bearer(grace["access_token"]),
    )
    ada_deck = obj(
        await client.post(
            f"/api/v1/groups/{group_one['id']}/decks",
            json={"name": "Ada", "format": "commander_10"},
            headers=bearer(ada["access_token"]),
        )
    )
    grace_deck = obj(
        await client.post(
            f"/api/v1/groups/{group_two['id']}/decks",
            json={"name": "Grace", "format": "commander_10"},
            headers=bearer(grace["access_token"]),
        )
    )
    oracle_id = await insert_catalog("Sol Ring")
    created = rows(
        await client.post(
            f"/api/v1/decks/{ada_deck['id']}/copies",
            json={"oracle_id": oracle_id, "quantity": 1},
            headers=bearer(ada["access_token"]),
        )
    )
    copy_id = created[0]["id"]

    blocked = await client.post(
        f"/api/v1/decks/{grace_deck['id']}/requests",
        json={"card_copy_id": copy_id},
        headers=bearer(grace["access_token"]),
    )
    visible = rows(
        await client.get(
            f"/api/v1/groups/{group_two['id']}/copies",
            headers=bearer(grace["access_token"]),
        )
    )
    await client.post(
        f"/api/v1/decks/{ada_deck['id']}/cards/{copy_id}/unlock",
        headers=bearer(ada["access_token"]),
    )
    opened = await client.post(
        f"/api/v1/decks/{grace_deck['id']}/requests",
        json={"card_copy_id": copy_id},
        headers=bearer(grace["access_token"]),
    )

    assert blocked.status_code == 409
    assert visible[0]["visibility"] == "in_use_elsewhere"
    assert visible[0]["deck"] is None
    assert opened.status_code == 201
    assert obj(opened)["status"] == "pending_acceptance"


@pytest.mark.integration
async def test_leaving_takes_only_cards_from_the_leavers_house(client: AsyncClient) -> None:
    ada = await register(client, "ada")
    grace = await register(client, "grace")
    shared = await create_group(client, ada["access_token"], "Compartilhado")
    private = await create_group(client, ada["access_token"], "So Ada")
    invited = await client.post(
        f"/api/v1/groups/{shared['id']}/invitations",
        json={"nick": "grace"},
        headers=bearer(ada["access_token"]),
    )
    await client.post(
        f"/api/v1/invitations/{obj(invited)['invitation_id']}/accept",
        headers=bearer(grace["access_token"]),
    )
    oracle_id = await insert_catalog("Sol Ring")
    await client.post(
        f"/api/v1/groups/{shared['id']}/copies",
        json={"oracle_id": oracle_id, "quantity": 1},
        headers=bearer(ada["access_token"]),
    )
    await client.post(
        f"/api/v1/groups/{shared['id']}/copies",
        json={"oracle_id": oracle_id, "quantity": 1},
        headers=bearer(grace["access_token"]),
    )

    left = await client.post(
        f"/api/v1/groups/{shared['id']}/leave",
        headers=bearer(ada["access_token"]),
    )
    shared_copies = rows(
        await client.get(
            f"/api/v1/groups/{shared['id']}/copies",
            headers=bearer(grace["access_token"]),
        )
    )
    private_copies = rows(
        await client.get(
            f"/api/v1/groups/{private['id']}/copies",
            headers=bearer(ada["access_token"]),
        )
    )
    groups = rows(await client.get("/api/v1/groups", headers=bearer(grace["access_token"])))

    assert left.status_code == 204
    assert [holder_nick(copy) for copy in shared_copies] == ["grace"]
    assert [holder_nick(copy) for copy in private_copies] == ["ada"]
    shared_group = next(group for group in groups if group["id"] == shared["id"])
    assert shared_group["owner_id"] == grace["id"]


@pytest.mark.integration
async def test_commander_10_over_budget_warns_and_keeps_the_deck(
    client: AsyncClient,
    prices: PriceStub,
) -> None:
    ada = await register(client, "ada")
    group = await create_group(client, ada["access_token"])
    deck = obj(
        await client.post(
            f"/api/v1/groups/{group['id']}/decks",
            json={"name": "Dez", "format": "commander_10"},
            headers=bearer(ada["access_token"]),
        )
    )
    prices.cents = 1500
    oracle_id = await insert_catalog("Sol Ring")
    created = await client.post(
        f"/api/v1/decks/{deck['id']}/copies",
        json={"oracle_id": oracle_id, "quantity": 1},
        headers=bearer(ada["access_token"]),
    )
    detail = obj(
        await client.get(
            f"/api/v1/decks/{deck['id']}",
            headers=bearer(ada["access_token"]),
        )
    )

    assert created.status_code == 201
    assert prices.calls == ["Sol Ring"]
    assert detail["card_count"] == 1
    assert detail["main_price_cents"] == 1500
    warnings = detail["warnings"]
    assert isinstance(warnings, list)
    assert any(
        isinstance(warning, dict) and warning.get("code") == "budget_main" for warning in warnings
    )


@pytest.mark.integration
async def test_basic_land_is_free_and_skips_the_price_provider(
    client: AsyncClient,
    prices: PriceStub,
) -> None:
    ada = await register(client, "ada")
    group = await create_group(client, ada["access_token"])
    prices.cents = 999
    oracle_id = await insert_catalog("Island", basic=True)
    created = rows(
        await client.post(
            f"/api/v1/groups/{group['id']}/copies",
            json={"oracle_id": oracle_id, "quantity": 2},
            headers=bearer(ada["access_token"]),
        )
    )

    assert prices.calls == []
    assert [copy["price_cents"] for copy in created] == [0, 0]
