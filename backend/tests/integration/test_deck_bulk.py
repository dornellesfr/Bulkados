import pytest
from httpx import AsyncClient

from tests.integration.conftest import bearer, obj, rows
from tests.integration.test_commanders import LEGENDARY, insert_card
from tests.integration.test_contract import group_with_members, new_deck, register_copies
from tests.integration.test_flows import register


async def bulk_update(
    client: AsyncClient,
    deck: dict[str, object],
    person: dict[str, object],
    cards: list[dict[str, str]],
) -> tuple[int, dict[str, object]]:
    response = await client.put(
        f"/api/v1/decks/{deck['id']}/bulk",
        json={"cards": cards},
        headers=bearer(person["access_token"]),
    )
    return response.status_code, obj(response)


@pytest.mark.integration
async def test_bulk_replaces_the_deck_by_names_and_keeps_the_free_copy(
    client: AsyncClient,
) -> None:
    ada = await register(client, "ada")
    group = await group_with_members(client, ada)
    deck = await new_deck(client, group, ada)
    sol = await insert_card("Sol Ring")
    await insert_card("Azula", type_line=LEGENDARY, commander=True)
    [free] = await register_copies(client, group, ada, sol)

    status, detail = await bulk_update(
        client,
        deck,
        ada,
        [
            {"name": "Azula", "role": "commander"},
            {"name": "Sol Ring", "role": "main"},
        ],
    )

    assert status == 200, detail
    cards = detail["cards"]
    assert isinstance(cards, list)
    by_name = {card["catalog"]["name_en"]: card for card in cards}
    assert set(by_name) == {"Azula", "Sol Ring"}
    assert by_name["Azula"]["role"] == "commander"
    assert by_name["Sol Ring"]["role"] == "main"
    assert by_name["Sol Ring"]["card_copy_id"] == free["id"]


@pytest.mark.integration
async def test_an_unknown_name_aborts_the_whole_bulk_update(client: AsyncClient) -> None:
    ada = await register(client, "ada")
    group = await group_with_members(client, ada)
    deck = await new_deck(client, group, ada)
    sol = await insert_card("Sol Ring")
    [free] = await register_copies(client, group, ada, sol)
    taken = await client.post(
        f"/api/v1/decks/{deck['id']}/take",
        json={"card_copy_id": free["id"]},
        headers=bearer(ada["access_token"]),
    )
    assert taken.status_code == 200, taken.text

    status, body = await bulk_update(
        client,
        deck,
        ada,
        [
            {"name": "Sol Ring", "role": "main"},
            {"name": "Carta Que Não Existe", "role": "main"},
        ],
    )

    assert status == 422
    assert "Carta Que Não Existe" in str(body["detail"])
    detail = obj(
        await client.get(
            f"/api/v1/decks/{deck['id']}",
            headers=bearer(ada["access_token"]),
        )
    )
    cards = detail["cards"]
    assert isinstance(cards, list)
    assert [card["catalog"]["name_en"] for card in cards] == ["Sol Ring"]


@pytest.mark.integration
async def test_removing_a_card_in_bulk_returns_it_to_the_bulk(client: AsyncClient) -> None:
    ada = await register(client, "ada")
    group = await group_with_members(client, ada)
    deck = await new_deck(client, group, ada)
    sol = await insert_card("Sol Ring")
    [free] = await register_copies(client, group, ada, sol)
    taken = await client.post(
        f"/api/v1/decks/{deck['id']}/take",
        json={"card_copy_id": free["id"]},
        headers=bearer(ada["access_token"]),
    )
    assert taken.status_code == 200, taken.text

    status, detail = await bulk_update(client, deck, ada, [])

    assert status == 200, detail
    assert detail["cards"] == []
    listed = rows(
        await client.get(
            f"/api/v1/groups/{group['id']}/copies",
            headers=bearer(ada["access_token"]),
        )
    )
    returned = next(copy for copy in listed if copy["id"] == free["id"])
    assert (returned["state"], returned["locked"], returned["deck"]) == (
        "available",
        False,
        None,
    )


@pytest.mark.integration
async def test_the_commander_can_be_moved_to_main_or_removed_by_the_list(
    client: AsyncClient,
) -> None:
    ada = await register(client, "ada")
    group = await group_with_members(client, ada)
    deck = await new_deck(client, group, ada)
    await insert_card("Azula", type_line=LEGENDARY, commander=True)

    created, _ = await bulk_update(
        client,
        deck,
        ada,
        [{"name": "Azula", "role": "commander"}],
    )
    demoted, detail = await bulk_update(
        client,
        deck,
        ada,
        [{"name": "Azula", "role": "main"}],
    )
    removed, empty = await bulk_update(client, deck, ada, [])

    assert created == 200
    assert demoted == 200
    cards = detail["cards"]
    assert isinstance(cards, list)
    assert [card["role"] for card in cards] == ["main"]
    assert removed == 200
    assert empty["cards"] == []


@pytest.mark.integration
async def test_bulk_keeps_a_requested_copy_and_removes_the_other_one(
    client: AsyncClient,
) -> None:
    ada = await register(client, "ada")
    grace = await register(client, "grace")
    group = await group_with_members(client, ada, grace)
    deck = await new_deck(client, group, ada)
    other = await new_deck(client, group, grace, name="Deck da Grace")
    sol = await insert_card("Sol Ring")
    copies = await register_copies(client, group, ada, sol, quantity=2)
    for copy in copies:
        taken = await client.post(
            f"/api/v1/decks/{deck['id']}/take",
            json={"card_copy_id": copy["id"]},
            headers=bearer(ada["access_token"]),
        )
        assert taken.status_code == 200, taken.text
    requested = await client.post(
        f"/api/v1/decks/{other['id']}/requests",
        json={"card_copy_id": copies[0]["id"], "group_id": group["id"]},
        headers=bearer(grace["access_token"]),
    )
    assert requested.status_code == 201, requested.text

    status, detail = await bulk_update(
        client,
        deck,
        ada,
        [{"name": "Sol Ring", "role": "main"}],
    )

    assert status == 200, detail
    cards = detail["cards"]
    assert isinstance(cards, list)
    assert [card["card_copy_id"] for card in cards] == [copies[0]["id"]]


@pytest.mark.integration
async def test_a_card_with_an_open_request_cannot_leave_the_deck_in_bulk(
    client: AsyncClient,
) -> None:
    ada = await register(client, "ada")
    grace = await register(client, "grace")
    group = await group_with_members(client, ada, grace)
    deck = await new_deck(client, group, ada)
    other = await new_deck(client, group, grace, name="Deck da Grace")
    sol = await insert_card("Sol Ring")
    [free] = await register_copies(client, group, ada, sol)
    taken = await client.post(
        f"/api/v1/decks/{deck['id']}/take",
        json={"card_copy_id": free["id"]},
        headers=bearer(ada["access_token"]),
    )
    assert taken.status_code == 200, taken.text
    requested = await client.post(
        f"/api/v1/decks/{other['id']}/requests",
        json={"card_copy_id": free["id"], "group_id": group["id"]},
        headers=bearer(grace["access_token"]),
    )
    assert requested.status_code == 201, requested.text

    status, body = await bulk_update(client, deck, ada, [])

    assert status == 409
    assert "pedido aberto" in str(body["detail"])
    detail = obj(
        await client.get(
            f"/api/v1/decks/{deck['id']}",
            headers=bearer(ada["access_token"]),
        )
    )
    cards = detail["cards"]
    assert isinstance(cards, list)
    assert [card["catalog"]["name_en"] for card in cards] == ["Sol Ring"]
