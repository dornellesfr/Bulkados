from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.core.database import SessionFactory
from app.domain.enums import PartnerKind
from tests.integration.conftest import bearer, obj, rows
from tests.integration.test_commanders import (
    LEGENDARY,
    deck_holding,
    insert_card,
    set_commanders,
)
from tests.integration.test_contract import (
    new_deck,
    register_copies,
)
from tests.integration.test_flows import register


async def green_deck(client: AsyncClient) -> tuple[dict[str, object], dict[str, str]]:
    """Deck da Ada com um comandante verde já marcado."""
    deck, ids = await deck_holding(
        client,
        {"Ezuri": await insert_card("Ezuri", type_line=LEGENDARY, commander=True, colors=["G"])},
    )
    status, _ = await set_commanders(client, deck, [ids["Ezuri"]])
    assert status == 200
    return deck, ids


async def add_direct(client: AsyncClient, deck: dict[str, object], oracle_id: str) -> int:
    response = await client.post(
        f"/api/v1/decks/{deck['id']}/copies",
        json={"oracle_id": oracle_id, "quantity": 1},
        headers=bearer(deck["token"]),
    )
    return response.status_code


async def identity_of(client: AsyncClient, deck: dict[str, object]) -> tuple[object, object]:
    detail = obj(await client.get(f"/api/v1/decks/{deck['id']}", headers=bearer(deck["token"])))
    listed = rows(
        await client.get(f"/api/v1/groups/{deck['group_id']}/decks", headers=bearer(deck["token"]))
    )
    assert (listed[0]["color_identity"], listed[0]["color_identity_name"]) == (
        detail["color_identity"],
        detail["color_identity_name"],
    )
    return detail["color_identity"], detail["color_identity_name"]


@pytest.mark.integration
async def test_a_deck_without_color_commander_is_colorless(client: AsyncClient) -> None:
    deck, ids = await deck_holding(
        client,
        {"Karn": await insert_card("Karn", type_line=LEGENDARY, commander=True)},
    )

    nobody = await identity_of(client, deck)
    await set_commanders(client, deck, [ids["Karn"]])
    colorless = await identity_of(client, deck)

    assert nobody == (None, None)
    assert colorless == ([], "Incolor")


@pytest.mark.integration
async def test_the_deck_identity_is_the_union_of_its_commanders(client: AsyncClient) -> None:
    deck, ids = await deck_holding(
        client,
        {
            "Partner R": await insert_card(
                "Partner R",
                type_line=LEGENDARY,
                commander=True,
                colors=["R"],
                partner=PartnerKind.partner,
            ),
            "Partner G": await insert_card(
                "Partner G",
                type_line=LEGENDARY,
                commander=True,
                colors=["G"],
                partner=PartnerKind.partner,
            ),
        },
    )

    await set_commanders(client, deck, [ids["Partner G"], ids["Partner R"]])

    assert await identity_of(client, deck) == (["R", "G"], "Gruul")


@pytest.mark.integration
async def test_adding_a_card_outside_the_identity_is_refused(client: AsyncClient) -> None:
    deck, _ = await green_deck(client)
    blue = await insert_card("Counterspell", colors=["U"])
    green = await insert_card("Llanowar Elves", colors=["G"])
    colorless = await insert_card("Sol Ring")
    group = {"id": deck["group_id"]}
    ada = {"access_token": deck["token"]}
    [blue_copy] = await register_copies(client, group, ada, blue)

    refused = await client.post(
        f"/api/v1/decks/{deck['id']}/copies",
        json={"oracle_id": blue, "quantity": 1},
        headers=bearer(deck["token"]),
    )
    taken = await client.post(
        f"/api/v1/decks/{deck['id']}/take",
        json={"card_copy_id": blue_copy["id"]},
        headers=bearer(deck["token"]),
    )

    assert refused.status_code == 409
    assert "identidade de cor" in str(obj(refused)["detail"])
    assert taken.status_code == 409
    assert await add_direct(client, deck, green) == 201
    assert await add_direct(client, deck, colorless) == 201


@pytest.mark.integration
async def test_moving_or_requesting_a_card_outside_the_identity_is_refused(
    client: AsyncClient,
) -> None:
    deck, _ = await green_deck(client)
    grace = await register(client, "grace")
    group = {"id": deck["group_id"]}
    ada = {"access_token": deck["token"]}
    invited = await client.post(
        f"/api/v1/groups/{group['id']}/invitations",
        json={"nick": "grace"},
        headers=bearer(deck["token"]),
    )
    await client.post(
        f"/api/v1/invitations/{obj(invited)['invitation_id']}/accept",
        headers=bearer(grace["access_token"]),
    )
    blue = await insert_card("Counterspell", colors=["U"])
    [grace_copy] = await register_copies(client, group, grace, blue)
    other = await new_deck(client, group, ada, "Outro")
    [ada_copy] = await register_copies(client, group, ada, blue)
    await client.post(
        f"/api/v1/decks/{other['id']}/take",
        json={"card_copy_id": ada_copy["id"]},
        headers=bearer(deck["token"]),
    )

    requested = await client.post(
        f"/api/v1/decks/{deck['id']}/requests",
        json={"card_copy_id": grace_copy["id"]},
        headers=bearer(deck["token"]),
    )
    moved = await client.post(
        f"/api/v1/decks/{other['id']}/cards/{ada_copy['id']}/move",
        json={"target_deck_id": deck["id"]},
        headers=bearer(deck["token"]),
    )

    assert requested.status_code == 409
    assert moved.status_code == 409


@pytest.mark.integration
async def test_the_search_inside_a_deck_only_suggests_cards_that_fit(
    client: AsyncClient,
) -> None:
    deck, _ = await green_deck(client)
    await insert_card("Lightning Helix", colors=["R", "W"])
    await insert_card("Llanowar Elves", colors=["G"])
    await insert_card("Lightning Greaves")
    async with SessionFactory() as session:
        await session.execute(
            text(
                "INSERT INTO catalog_sync (id, last_synced_at) VALUES (1, now()) "
                "ON CONFLICT (id) DO UPDATE SET last_synced_at = now()"
            )
        )
        await session.commit()
    headers = bearer(deck["token"])

    everything = rows(await client.get("/api/v1/catalog/cards", params={"q": "l"}, headers=headers))
    fitting = rows(
        await client.get(
            "/api/v1/catalog/cards", params={"q": "l", "deck_id": str(deck["id"])}, headers=headers
        )
    )
    foreign = await client.get(
        "/api/v1/catalog/cards", params={"q": "l", "deck_id": str(uuid4())}, headers=headers
    )

    assert {card["name_en"] for card in everything} >= {
        "Lightning Helix",
        "Llanowar Elves",
        "Lightning Greaves",
    }
    assert {card["name_en"] for card in fitting} == {
        "Llanowar Elves",
        "Lightning Greaves",
    }
    assert foreign.status_code == 404


@pytest.mark.integration
async def test_the_deck_list_names_the_commanders(client: AsyncClient) -> None:
    deck, ids = await deck_holding(
        client,
        {
            "Azula": await insert_card("Azula", type_line=LEGENDARY, commander=True),
            "Partner": await insert_card(
                "Partner", type_line=LEGENDARY, commander=True, partner=PartnerKind.partner
            ),
            "Twin": await insert_card(
                "Twin", type_line=LEGENDARY, commander=True, partner=PartnerKind.partner
            ),
        },
    )
    url = f"/api/v1/groups/{deck['group_id']}/decks"
    headers = bearer(deck["token"])

    async def commanders() -> list[object]:
        [summary] = rows(await client.get(url, headers=headers))
        found = summary["commanders"]
        assert isinstance(found, list)
        return [commander["name_en"] for commander in found]

    none_yet = await commanders()
    await set_commanders(client, deck, [ids["Azula"]])
    one = await commanders()
    await set_commanders(client, deck, [ids["Twin"], ids["Partner"]])
    two = await commanders()

    assert (none_yet, one, two) == ([], ["Azula"], ["Partner", "Twin"])
