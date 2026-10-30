import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.core.database import SessionFactory
from app.models.copy import CardCopy
from tests.integration.conftest import bearer, obj, rows
from tests.integration.test_commanders import insert_card
from tests.integration.test_contract import (
    group_with_members,
    new_deck,
    register_copies,
)
from tests.integration.test_flows import register


async def copy_count() -> int:
    async with SessionFactory() as session:
        return await session.scalar(select(func.count()).select_from(CardCopy)) or 0


async def add_to_deck(
    client: AsyncClient,
    deck: dict[str, object],
    token: object,
    oracle_id: str,
    quantity: int,
) -> list[dict[str, object]]:
    response = await client.post(
        f"/api/v1/decks/{deck['id']}/copies",
        json={"oracle_id": oracle_id, "quantity": quantity},
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    return rows(response)


@pytest.mark.integration
async def test_adding_a_card_locks_the_free_copy_from_the_bulk(client: AsyncClient) -> None:
    ada = await register(client, "ada")
    group = await group_with_members(client, ada)
    deck = await new_deck(client, group, ada)
    oracle_id = await insert_card("Sol Ring")
    [free] = await register_copies(client, group, ada, oracle_id)

    [added] = await add_to_deck(client, deck, ada["access_token"], oracle_id, 1)

    assert added["id"] == free["id"]
    assert (added["state"], added["locked"], added["visibility"]) == ("in_deck", True, "in_deck")
    assert await copy_count() == 1
    detail = obj(
        await client.get(f"/api/v1/decks/{deck['id']}", headers=bearer(ada["access_token"]))
    )
    cards = detail["cards"]
    assert isinstance(cards, list)
    assert [card["card_copy_id"] for card in cards] == [free["id"]]


@pytest.mark.integration
async def test_the_missing_copies_are_registered_straight_into_the_deck(
    client: AsyncClient,
) -> None:
    ada = await register(client, "ada")
    group = await group_with_members(client, ada)
    deck = await new_deck(client, group, ada)
    oracle_id = await insert_card("Sol Ring")
    [free] = await register_copies(client, group, ada, oracle_id)

    added = await add_to_deck(client, deck, ada["access_token"], oracle_id, 3)

    assert len(added) == 3
    assert free["id"] in {copy["id"] for copy in added}
    assert all(copy["state"] == "in_deck" for copy in added)
    assert await copy_count() == 3


@pytest.mark.integration
async def test_it_never_takes_a_copy_that_is_in_another_persons_house(
    client: AsyncClient,
) -> None:
    ada = await register(client, "ada")
    grace = await register(client, "grace")
    group = await group_with_members(client, ada, grace)
    deck = await new_deck(client, group, ada)
    oracle_id = await insert_card("Sol Ring")
    [graces] = await register_copies(client, group, grace, oracle_id)

    [added] = await add_to_deck(client, deck, ada["access_token"], oracle_id, 1)

    assert added["id"] != graces["id"]
    assert (added["holder"]["nick"] if isinstance(added["holder"], dict) else None) == "ada"
    assert await copy_count() == 2
    listed = rows(
        await client.get(
            f"/api/v1/groups/{group['id']}/copies", headers=bearer(grace["access_token"])
        )
    )
    still_free = next(copy for copy in listed if copy["id"] == graces["id"])
    assert still_free["state"] == "available"
