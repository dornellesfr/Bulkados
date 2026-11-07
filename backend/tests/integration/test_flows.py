from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.database import SessionFactory
from app.domain.enums import CommanderLegal
from app.models.catalog import CatalogCard
from tests.integration.conftest import FakeAuth, PriceStub, bearer, obj, rows


def registration(label: str) -> dict[str, str]:
    return {
        "email": f"{label}@example.com",
        "password": "password123",
        "first_name": label.capitalize(),
        "last_name": "Silva",
    }


def identity(person: dict[str, object]) -> dict[str, object]:
    return {
        "id": person["id"],
        "email": person["email"],
        "first_name": person["first_name"],
        "last_name": person["last_name"],
    }


async def register(client: AsyncClient, label: str) -> dict[str, object]:
    response = await client.post("/api/v1/auth/register", json=registration(label))
    assert response.status_code == 201, response.text
    return obj(response)


def holder_email(copy: dict[str, object]) -> object:
    holder = copy["holder"]
    assert isinstance(holder, dict)
    return holder["email"]


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
async def test_duplicate_email_rejects_the_whole_registration(
    client: AsyncClient,
    auth_provider: FakeAuth,
) -> None:
    await register(client, "ada")

    response = await client.post(
        "/api/v1/auth/register",
        json={**registration("ada"), "email": "Ada@example.com"},
    )

    assert response.status_code == 409
    assert obj(response) == {"detail": "Já existe uma conta com esse e-mail."}
    assert list(auth_provider.users) == ["ada@example.com"]


@pytest.mark.integration
async def test_login_uses_email_and_the_same_error(client: AsyncClient) -> None:
    await register(client, "ada")

    logged_in = await client.post(
        "/api/v1/auth/login",
        json={"email": "Ada@example.com", "password": "password123"},
    )
    wrong_password = await client.post(
        "/api/v1/auth/login",
        json={"email": "ada@example.com", "password": "nope-nope"},
    )
    unknown_email = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "nope-nope"},
    )

    body = obj(logged_in)
    assert logged_in.status_code == 200
    assert "email" not in body
    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert obj(wrong_password) == obj(unknown_email)
    assert obj(wrong_password) == {"detail": "E-mail ou senha incorretos."}

    me = await client.get("/api/v1/me", headers=bearer(body["access_token"]))
    assert me.status_code == 200
    assert set(obj(me)) == {"id", "email", "first_name", "last_name", "created_at"}
    assert obj(me)["email"] == "ada@example.com"
    assert (obj(me)["first_name"], obj(me)["last_name"]) == ("Ada", "Silva")
    renamed = await client.patch(
        "/api/v1/me",
        json={"first_name": "Ada", "last_name": "Lovelace"},
        headers=bearer(body["access_token"]),
    )
    assert renamed.status_code == 200, renamed.text
    assert (obj(renamed)["first_name"], obj(renamed)["last_name"]) == ("Ada", "Lovelace")


@pytest.mark.integration
async def test_a_valid_token_recreates_the_missing_local_user(
    client: AsyncClient,
    auth_provider: FakeAuth,
) -> None:
    user_id = await auth_provider.sign_up("novo@example.com", "password123")
    session = await auth_provider.sign_in("novo@example.com", "password123")

    me = await client.get("/api/v1/me", headers=bearer(session.access_token))

    assert me.status_code == 200, me.text
    body = obj(me)
    assert body["id"] == str(user_id)
    assert body["email"] == "novo@example.com"
    assert (body["first_name"], body["last_name"]) == ("novo", "Conta")


@pytest.mark.integration
async def test_forgot_password_returns_the_same_message(client: AsyncClient) -> None:
    await register(client, "ada")
    known = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "ada@example.com"},
    )
    unknown = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )

    assert known.status_code == 200
    assert obj(known) == obj(unknown)
    assert "e-mail" in str(obj(known)["message"])


@pytest.mark.integration
async def test_change_password(client: AsyncClient) -> None:
    ada = await register(client, "ada")
    headers = bearer(ada["access_token"])

    changed = await client.post(
        "/api/v1/auth/password",
        json={"current_password": "password123", "new_password": "better-pass"},
        headers=headers,
    )
    old = await client.post(
        "/api/v1/auth/login",
        json={"email": "ada@example.com", "password": "password123"},
    )
    new = await client.post(
        "/api/v1/auth/login",
        json={"email": "ada@example.com", "password": "better-pass"},
    )
    wrong = await client.post(
        "/api/v1/auth/password",
        json={"current_password": "nope-nope", "new_password": "another-pass"},
        headers=headers,
    )

    assert changed.status_code == 204
    assert old.status_code == 401
    assert new.status_code == 200
    assert wrong.status_code == 400
    assert obj(wrong) == {"detail": "A senha atual não confere."}


@pytest.mark.integration
async def test_invite_without_acceptance_hides_the_group(client: AsyncClient) -> None:
    ada = await register(client, "ada")
    grace = await register(client, "grace")
    group = await create_group(client, ada["access_token"])

    invited = await client.post(
        f"/api/v1/groups/{group['id']}/invitations",
        json={"email": "grace@example.com"},
        headers=bearer(ada["access_token"]),
    )
    hidden = await client.get(
        f"/api/v1/groups/{group['id']}/copies",
        headers=bearer(grace["access_token"]),
    )
    inbox = await client.get("/api/v1/invitations", headers=bearer(grace["access_token"]))
    before = await client.get("/api/v1/groups", headers=bearer(grace["access_token"]))
    accepted = await client.post(
        f"/api/v1/invitations/{obj(invited)['invitation_id']}/accept",
        headers=bearer(grace["access_token"]),
    )
    visible = await client.get(
        f"/api/v1/groups/{group['id']}/copies",
        headers=bearer(grace["access_token"]),
    )
    cleared = await client.get("/api/v1/invitations", headers=bearer(grace["access_token"]))

    assert invited.status_code == 201
    assert hidden.status_code == 404
    assert rows(before) == []
    [pending] = rows(inbox)
    assert pending["id"] == obj(invited)["invitation_id"]
    assert pending["group"] == {"id": group["id"], "name": group["name"]}
    assert pending["invited_by"] == identity(ada)
    assert set(pending) == {"id", "group", "invited_by", "created_at"}
    assert accepted.status_code == 200
    assert visible.status_code == 200
    assert rows(cleared) == []


@pytest.mark.integration
async def test_second_bulk_request_conflicts(client: AsyncClient) -> None:
    ada = await register(client, "ada")
    grace = await register(client, "grace")
    linus = await register(client, "linus")
    group = await create_group(client, ada["access_token"])
    for person in (grace, linus):
        invited = await client.post(
            f"/api/v1/groups/{group['id']}/invitations",
            json={"email": person["email"]},
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
    assert obj(first)["status"] == "pending_acceptance"
    assert second.status_code == 409


@pytest.mark.integration
async def test_a_bulk_request_needs_acceptance_and_both_confirmations(
    client: AsyncClient,
) -> None:
    ada = await register(client, "ada")
    grace = await register(client, "grace")
    group = await create_group(client, ada["access_token"])
    invited = await client.post(
        f"/api/v1/groups/{group['id']}/invitations",
        json={"email": "grace@example.com"},
        headers=bearer(ada["access_token"]),
    )
    await client.post(
        f"/api/v1/invitations/{obj(invited)['invitation_id']}/accept",
        headers=bearer(grace["access_token"]),
    )
    oracle_id = await insert_catalog("Sol Ring")
    [copy] = rows(
        await client.post(
            f"/api/v1/groups/{group['id']}/copies",
            json={"oracle_id": oracle_id, "quantity": 1},
            headers=bearer(ada["access_token"]),
        )
    )
    deck = obj(
        await client.post(
            "/api/v1/decks",
            json={"name": "Grace", "format": "commander_10"},
            headers=bearer(grace["access_token"]),
        )
    )

    created = await client.post(
        f"/api/v1/decks/{deck['id']}/requests",
        json={"card_copy_id": copy["id"], "group_id": group["id"]},
        headers=bearer(grace["access_token"]),
    )
    request_id = obj(created)["id"]
    early = await client.post(
        f"/api/v1/requests/{request_id}/confirm",
        headers=bearer(grace["access_token"]),
    )
    accepted = await client.post(
        f"/api/v1/requests/{request_id}/accept",
        headers=bearer(ada["access_token"]),
    )
    first = await client.post(
        f"/api/v1/requests/{request_id}/confirm",
        headers=bearer(grace["access_token"]),
    )
    before_both = obj(
        await client.get(f"/api/v1/decks/{deck['id']}", headers=bearer(grace["access_token"]))
    )
    second = await client.post(
        f"/api/v1/requests/{request_id}/confirm",
        headers=bearer(ada["access_token"]),
    )
    detail = obj(
        await client.get(f"/api/v1/decks/{deck['id']}", headers=bearer(grace["access_token"]))
    )
    [moved] = rows(
        await client.get(
            f"/api/v1/groups/{group['id']}/copies",
            headers=bearer(grace["access_token"]),
        )
    )

    assert created.status_code == 201
    assert obj(created)["status"] == "pending_acceptance"
    assert early.status_code == 409
    assert accepted.status_code == 200
    assert obj(accepted)["status"] == "awaiting_handoff"
    assert first.status_code == 200
    assert obj(first)["requester_confirmed"] is True
    assert obj(first)["holder_confirmed"] is False
    assert before_both["cards"] == []
    assert second.status_code == 200
    assert obj(second)["status"] == "completed"
    cards = detail["cards"]
    assert isinstance(cards, list)
    assert [card["card_copy_id"] for card in cards] == [copy["id"]]
    assert moved["holder"] == identity(grace)
    assert (moved["state"], moved["locked"], moved["visibility"]) == (
        "in_deck",
        False,
        "in_deck",
    )
    assert moved["deck"] == {
        "id": deck["id"],
        "name": "Grace",
        "owner": identity(grace),
    }


@pytest.mark.integration
async def test_a_locked_deck_card_cannot_be_requested_from_another_group(
    client: AsyncClient,
) -> None:
    ada = await register(client, "ada")
    grace = await register(client, "grace")
    group_one = await create_group(client, ada["access_token"], "Um")
    group_two = await create_group(client, ada["access_token"], "Dois")
    invited = await client.post(
        f"/api/v1/groups/{group_two['id']}/invitations",
        json={"email": "grace@example.com"},
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
    [copy] = rows(
        await client.post(
            f"/api/v1/decks/{ada_deck['id']}/copies",
            json={"oracle_id": oracle_id, "quantity": 1},
            headers=bearer(ada["access_token"]),
        )
    )
    locked = await client.post(
        f"/api/v1/decks/{ada_deck['id']}/cards/{copy['id']}/lock",
        headers=bearer(ada["access_token"]),
    )

    blocked = await client.post(
        f"/api/v1/decks/{grace_deck['id']}/requests",
        json={"card_copy_id": copy["id"]},
        headers=bearer(grace["access_token"]),
    )
    visible = rows(
        await client.get(
            f"/api/v1/groups/{group_two['id']}/copies",
            headers=bearer(grace["access_token"]),
        )
    )

    assert locked.status_code == 200
    assert obj(locked)["locked"] is True
    assert blocked.status_code == 409
    assert visible[0]["visibility"] == "in_deck"
    deck_ref = visible[0]["deck"]
    assert isinstance(deck_ref, dict)
    assert deck_ref["owner"] == identity(ada)
    assert visible[0]["locked"] is True

    await client.post(
        f"/api/v1/decks/{ada_deck['id']}/cards/{copy['id']}/unlock",
        headers=bearer(ada["access_token"]),
    )
    opened = await client.post(
        f"/api/v1/decks/{grace_deck['id']}/requests",
        json={"card_copy_id": copy["id"]},
        headers=bearer(grace["access_token"]),
    )

    assert opened.status_code == 201
    assert obj(opened)["status"] == "pending_acceptance"


@pytest.mark.integration
async def test_deleting_a_deck_releases_even_locked_cards_to_the_bulk(
    client: AsyncClient,
) -> None:
    ada = await register(client, "ada")
    group = await create_group(client, ada["access_token"])
    headers = bearer(ada["access_token"])
    deck = obj(
        await client.post(
            "/api/v1/decks",
            json={"name": "Deck", "format": "commander_10"},
            headers=headers,
        )
    )
    oracle_id = await insert_catalog("Sol Ring")
    [copy] = rows(
        await client.post(
            f"/api/v1/decks/{deck['id']}/copies",
            json={"oracle_id": oracle_id, "quantity": 1},
            headers=headers,
        )
    )
    locked = await client.post(
        f"/api/v1/decks/{deck['id']}/cards/{copy['id']}/lock",
        headers=headers,
    )
    deleted = await client.delete(f"/api/v1/decks/{deck['id']}", headers=headers)
    [released] = rows(await client.get(f"/api/v1/groups/{group['id']}/copies", headers=headers))
    decks = rows(await client.get("/api/v1/decks", headers=headers))

    assert locked.status_code == 200
    assert obj(locked)["locked"] is True
    assert deleted.status_code == 204
    assert decks == []
    assert (released["state"], released["locked"], released["visibility"]) == (
        "available",
        False,
        "available",
    )
    assert released["deck"] is None


@pytest.mark.integration
async def test_a_new_deck_is_empty_and_the_list_counts_its_cards(
    client: AsyncClient,
) -> None:
    ada = await register(client, "ada")
    await create_group(client, ada["access_token"])
    headers = bearer(ada["access_token"])
    created = obj(
        await client.post(
            "/api/v1/decks",
            json={"name": "Vazio", "format": "commander_10"},
            headers=headers,
        )
    )
    [empty] = rows(await client.get("/api/v1/decks", headers=headers))
    oracle_id = await insert_catalog("Sol Ring")
    await client.post(
        f"/api/v1/decks/{created['id']}/copies",
        json={"oracle_id": oracle_id, "quantity": 1},
        headers=headers,
    )
    [filled] = rows(await client.get("/api/v1/decks", headers=headers))

    assert created["card_count"] == 0
    assert empty["card_count"] == 0
    assert empty["commanders"] == []
    assert filled["card_count"] == 1


@pytest.mark.integration
async def test_leaving_takes_only_cards_from_the_leavers_house(client: AsyncClient) -> None:
    ada = await register(client, "ada")
    grace = await register(client, "grace")
    shared = await create_group(client, ada["access_token"], "Compartilhado")
    private = await create_group(client, ada["access_token"], "So Ada")
    invited = await client.post(
        f"/api/v1/groups/{shared['id']}/invitations",
        json={"email": "grace@example.com"},
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
    assert [holder_email(copy) for copy in shared_copies] == ["grace@example.com"]
    assert [holder_email(copy) for copy in private_copies] == ["ada@example.com"]
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
