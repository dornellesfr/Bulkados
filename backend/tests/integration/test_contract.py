"""Formato das respostas que o frontend valida (frontend/src/lib/api e docs/spec-frontend.md)."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.integration.conftest import bearer, obj, rows
from tests.integration.test_flows import create_group, insert_catalog, register

PERSON = {"id", "nick"}
CATALOG = {
    "oracle_id",
    "name_en",
    "name_pt",
    "image_url",
    "mana_cost",
    "type_line",
    "color_identity",
    "is_basic",
}
DECK_CATALOG = CATALOG | {"commander_legal", "can_be_commander", "partner_kind"}
COPY = {
    "id",
    "catalog",
    "holder",
    "added_by",
    "price_cents",
    "price_fetched_at",
    "state",
    "locked",
    "visibility",
    "deck",
    "open_request",
}
OPEN_REQUEST = {"id", "status", "source", "requester"}
DECK_CARD = {
    "card_copy_id",
    "role",
    "locked",
    "price_cents",
    "holder",
    "catalog",
    "open_request",
    "can_toggle_commander",
}


def keys(value: object) -> set[str]:
    assert isinstance(value, dict)
    return set(value)


def assert_copy_shape(copy: dict[str, object]) -> None:
    assert keys(copy) == COPY
    assert keys(copy["catalog"]) == CATALOG
    assert keys(copy["holder"]) == PERSON
    assert keys(copy["added_by"]) == PERSON


async def group_with_members(
    client: AsyncClient,
    owner: dict[str, object],
    *others: dict[str, object],
) -> dict[str, object]:
    group = await create_group(client, owner["access_token"])
    for person in others:
        invited = await client.post(
            f"/api/v1/groups/{group['id']}/invitations",
            json={"nick": person["nick"]},
            headers=bearer(owner["access_token"]),
        )
        await client.post(
            f"/api/v1/invitations/{obj(invited)['invitation_id']}/accept",
            headers=bearer(person["access_token"]),
        )
    return group


async def new_deck(
    client: AsyncClient,
    group: dict[str, object],
    person: dict[str, object],
    name: str = "Deck",
) -> dict[str, object]:
    response = await client.post(
        f"/api/v1/groups/{group['id']}/decks",
        json={"name": name, "format": "commander_10"},
        headers=bearer(person["access_token"]),
    )
    assert response.status_code == 201, response.text
    return obj(response)


async def register_copies(
    client: AsyncClient,
    group: dict[str, object],
    person: dict[str, object],
    oracle_id: str,
    quantity: int = 1,
) -> list[dict[str, object]]:
    response = await client.post(
        f"/api/v1/groups/{group['id']}/copies",
        json={"oracle_id": oracle_id, "quantity": quantity},
        headers=bearer(person["access_token"]),
    )
    assert response.status_code == 201, response.text
    return rows(response)


@pytest.mark.integration
async def test_bulk_registration_takes_the_oracle_id_and_returns_the_grouped_copy(
    client: AsyncClient,
) -> None:
    ada = await register(client, "ada")
    group = await group_with_members(client, ada)
    oracle_id = await insert_catalog("Sol Ring")

    copies = await register_copies(client, group, ada, oracle_id, quantity=2)

    assert len(copies) == 2
    for copy in copies:
        assert_copy_shape(copy)
        catalog = copy["catalog"]
        assert isinstance(catalog, dict)
        assert catalog["oracle_id"] == oracle_id
        assert copy["holder"] == {"id": ada["id"], "nick": "ada"}
        assert copy["added_by"] == {"id": ada["id"], "nick": "ada"}
        assert (copy["state"], copy["visibility"], copy["locked"]) == (
            "available",
            "available",
            False,
        )
        assert copy["deck"] is None
        assert copy["open_request"] is None


@pytest.mark.integration
async def test_bulk_registration_rejects_the_old_field_and_unknown_cards(
    client: AsyncClient,
) -> None:
    ada = await register(client, "ada")
    group = await group_with_members(client, ada)
    url = f"/api/v1/groups/{group['id']}/copies"
    headers = bearer(ada["access_token"])

    old_field = await client.post(
        url, json={"catalog_card_id": str(uuid4()), "quantity": 1}, headers=headers
    )
    unknown = await client.post(
        url, json={"oracle_id": str(uuid4()), "quantity": 1}, headers=headers
    )

    assert old_field.status_code == 422
    assert unknown.status_code == 404


@pytest.mark.integration
async def test_group_copy_list_uses_the_same_shape_and_exposes_the_open_request(
    client: AsyncClient,
) -> None:
    ada = await register(client, "ada")
    grace = await register(client, "grace")
    group = await group_with_members(client, ada, grace)
    oracle_id = await insert_catalog("Sol Ring")
    [copy] = await register_copies(client, group, ada, oracle_id)
    grace_deck = await new_deck(client, group, grace, "Grace")
    requested = await client.post(
        f"/api/v1/decks/{grace_deck['id']}/requests",
        json={"card_copy_id": copy["id"]},
        headers=bearer(grace["access_token"]),
    )

    listed = await client.get(
        f"/api/v1/groups/{group['id']}/copies",
        headers=bearer(ada["access_token"]),
    )

    assert requested.status_code == 201
    [item] = rows(listed)
    assert_copy_shape(item)
    assert keys(item["open_request"]) == OPEN_REQUEST
    assert item["open_request"] == {
        "id": obj(requested)["id"],
        "status": "awaiting_handoff",
        "source": "bulk",
        "requester": {"id": grace["id"], "nick": "grace"},
    }


@pytest.mark.integration
async def test_deck_detail_and_edit_return_grouped_cards(client: AsyncClient) -> None:
    ada = await register(client, "ada")
    group = await group_with_members(client, ada)
    oracle_id = await insert_catalog("Sol Ring")
    [copy] = await register_copies(client, group, ada, oracle_id)
    deck = await new_deck(client, group, ada, "Meu deck")
    headers = bearer(ada["access_token"])

    taken = await client.post(
        f"/api/v1/decks/{deck['id']}/take", json={"card_copy_id": copy["id"]}, headers=headers
    )
    detail = await client.get(f"/api/v1/decks/{deck['id']}", headers=headers)
    edited = await client.patch(
        f"/api/v1/decks/{deck['id']}", json={"name": "Renomeado"}, headers=headers
    )

    assert taken.status_code == 200, taken.text
    taken_copy = obj(taken)
    assert_copy_shape(taken_copy)
    assert taken_copy["visibility"] == "in_deck"
    assert taken_copy["deck"] == {
        "id": deck["id"],
        "name": "Meu deck",
        "owner": {"id": ada["id"], "nick": "ada"},
    }
    for response in (detail, edited):
        body = obj(response)
        assert response.status_code == 200
        assert {
            "id",
            "group_id",
            "name",
            "format",
            "owner_id",
            "card_count",
            "warnings",
            "cards",
        } <= set(body)
        [card] = body["cards"] if isinstance(body["cards"], list) else []
        assert keys(card) == DECK_CARD
        assert keys(card["catalog"]) == DECK_CATALOG
        assert card["holder"] == {"id": ada["id"], "nick": "ada"}
        assert card["open_request"] is None
    assert obj(edited)["name"] == "Renomeado"


@pytest.mark.integration
async def test_handoffs_use_the_grouped_format(client: AsyncClient) -> None:
    ada = await register(client, "ada")
    grace = await register(client, "grace")
    group = await group_with_members(client, ada, grace)
    oracle_id = await insert_catalog("Sol Ring")
    [copy] = await register_copies(client, group, ada, oracle_id)
    grace_deck = await new_deck(client, group, grace, "Grace")
    await client.post(
        f"/api/v1/decks/{grace_deck['id']}/requests",
        json={"card_copy_id": copy["id"]},
        headers=bearer(grace["access_token"]),
    )
    url = f"/api/v1/groups/{group['id']}/handoffs"

    for_ada = obj(await client.get(url, headers=bearer(ada["access_token"])))
    for_grace = obj(await client.get(url, headers=bearer(grace["access_token"])))

    assert set(for_ada) == {"to_bring", "to_receive"}
    [bring] = for_ada["to_bring"] if isinstance(for_ada["to_bring"], list) else []
    assert keys(bring) == {"id", "source", "catalog", "requester", "target_deck"}
    assert keys(bring["catalog"]) == {"name_en", "name_pt"}
    assert bring["requester"] == {"id": grace["id"], "nick": "grace"}
    assert bring["target_deck"] == {"id": grace_deck["id"], "name": "Grace"}
    [receive] = for_grace["to_receive"] if isinstance(for_grace["to_receive"], list) else []
    assert keys(receive) == {"id", "source", "catalog", "status", "holder", "target_deck"}
    assert receive["holder"] == {"id": ada["id"], "nick": "ada"}
    assert receive["status"] == "awaiting_handoff"


@pytest.mark.integration
async def test_a_card_registered_straight_into_a_deck_also_lives_in_the_bulk(
    client: AsyncClient,
) -> None:
    ada = await register(client, "ada")
    group = await group_with_members(client, ada)
    oracle_id = await insert_catalog("Sol Ring")
    deck = await new_deck(client, group, ada, "Meu deck")
    headers = bearer(ada["access_token"])

    created = await client.post(
        f"/api/v1/decks/{deck['id']}/copies",
        json={"oracle_id": oracle_id, "quantity": 1},
        headers=headers,
    )
    in_bulk = await client.get(f"/api/v1/groups/{group['id']}/copies", headers=headers)

    assert created.status_code == 201, created.text
    [copy] = rows(created)
    assert_copy_shape(copy)
    [listed] = rows(in_bulk)
    assert listed["id"] == copy["id"]
    assert (listed["visibility"], listed["locked"]) == ("in_deck", True)
    assert listed["deck"] == {
        "id": deck["id"],
        "name": "Meu deck",
        "owner": {"id": ada["id"], "nick": "ada"},
    }
