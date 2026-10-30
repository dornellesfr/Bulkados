from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.database import SessionFactory
from app.domain.enums import CommanderLegal, PartnerKind
from app.domain.search import normalize_search_text
from app.models.catalog import CatalogCard
from tests.integration.conftest import bearer, obj, rows
from tests.integration.test_contract import group_with_members, new_deck
from tests.integration.test_flows import register

LEGENDARY = "Legendary Creature — Human Noble"


async def insert_card(
    name: str,
    *,
    type_line: str = "Artifact",
    commander: bool = False,
    partner: PartnerKind | None = None,
    colors: list[str] | None = None,
) -> str:
    async with SessionFactory() as session:
        card = CatalogCard(
            oracle_id=uuid4(),
            name_en=name,
            name_pt=None,
            search_en=normalize_search_text(name),
            type_line=type_line,
            oracle_text="",
            color_identity=colors or [],
            keywords=[],
            is_basic=False,
            any_number_allowed=False,
            commander_legal=CommanderLegal.legal,
            can_be_commander=commander,
            partner_kind=partner,
        )
        session.add(card)
        await session.commit()
        return str(card.oracle_id)


async def deck_holding(
    client: AsyncClient, cards: dict[str, str]
) -> tuple[dict[str, object], dict[str, str]]:
    """Um deck da Ada com uma cópia travada de cada carta; devolve o deck e os ids das cópias."""
    ada = await register(client, "ada")
    group = await group_with_members(client, ada)
    deck = await new_deck(client, group, ada)
    headers = bearer(ada["access_token"])
    copy_ids: dict[str, str] = {}
    for name, oracle_id in cards.items():
        created = await client.post(
            f"/api/v1/groups/{group['id']}/copies",
            json={"oracle_id": oracle_id, "quantity": 1},
            headers=headers,
        )
        copy_id = str(rows(created)[0]["id"])
        taken = await client.post(
            f"/api/v1/decks/{deck['id']}/take", json={"card_copy_id": copy_id}, headers=headers
        )
        assert taken.status_code == 200, taken.text
        copy_ids[name] = copy_id
    return {**deck, "token": ada["access_token"]}, copy_ids


async def set_commanders(
    client: AsyncClient, deck: dict[str, object], copy_ids: list[str]
) -> tuple[int, dict[str, object]]:
    response = await client.post(
        f"/api/v1/decks/{deck['id']}/commanders",
        json={"card_copy_ids": copy_ids},
        headers=bearer(deck["token"]),
    )
    return response.status_code, obj(response)


async def toggles(client: AsyncClient, deck: dict[str, object]) -> dict[str, object]:
    response = await client.get(f"/api/v1/decks/{deck['id']}", headers=bearer(deck["token"]))
    cards = obj(response)["cards"]
    assert isinstance(cards, list)
    return {card["catalog"]["name_en"]: card["can_toggle_commander"] for card in cards}


@pytest.mark.integration
async def test_an_ineligible_card_cannot_be_the_commander(client: AsyncClient) -> None:
    deck, ids = await deck_holding(
        client,
        {
            "Sol Ring": await insert_card("Sol Ring"),
            "Azula": await insert_card("Azula", type_line=LEGENDARY, commander=True),
        },
    )

    refused_status, refused = await set_commanders(client, deck, [ids["Sol Ring"]])
    accepted_status, _ = await set_commanders(client, deck, [ids["Azula"]])

    assert refused_status == 409
    assert refused["detail"] == "Esta carta não pode ser comandante."
    assert accepted_status == 200


@pytest.mark.integration
async def test_two_commanders_need_a_valid_pair(client: AsyncClient) -> None:
    deck, ids = await deck_holding(
        client,
        {
            "Partner A": await insert_card(
                "Partner A", type_line=LEGENDARY, commander=True, partner=PartnerKind.partner
            ),
            "Partner B": await insert_card(
                "Partner B", type_line=LEGENDARY, commander=True, partner=PartnerKind.partner
            ),
            "Plain": await insert_card("Plain", type_line=LEGENDARY, commander=True),
            "Creature": await insert_card(
                "Creature",
                type_line=LEGENDARY,
                commander=True,
                partner=PartnerKind.choose_a_background,
            ),
            "Background": await insert_card(
                "Background",
                type_line="Legendary Enchantment — Background",
                partner=PartnerKind.background,
            ),
        },
    )

    partners, _ = await set_commanders(client, deck, [ids["Partner A"], ids["Partner B"]])
    background, _ = await set_commanders(client, deck, [ids["Creature"], ids["Background"]])
    mismatch, body = await set_commanders(client, deck, [ids["Partner A"], ids["Plain"]])
    alone, _ = await set_commanders(client, deck, [ids["Background"]])
    three, _ = await set_commanders(
        client, deck, [ids["Partner A"], ids["Partner B"], ids["Plain"]]
    )
    cleared, _ = await set_commanders(client, deck, [])

    assert (partners, background) == (200, 200)
    assert mismatch == 409
    assert "dupla válida" in str(body["detail"])
    assert (alone, three) == (409, 409)
    assert cleared == 200


@pytest.mark.integration
async def test_each_card_says_whether_the_commander_toggle_is_allowed(
    client: AsyncClient,
) -> None:
    deck, ids = await deck_holding(
        client,
        {
            "Sol Ring": await insert_card("Sol Ring"),
            "Azula": await insert_card("Azula", type_line=LEGENDARY, commander=True),
            "Partner": await insert_card(
                "Partner", type_line=LEGENDARY, commander=True, partner=PartnerKind.partner
            ),
        },
    )

    before = await toggles(client, deck)
    await set_commanders(client, deck, [ids["Azula"]])
    after = await toggles(client, deck)

    assert before == {"Sol Ring": False, "Azula": True, "Partner": True}
    assert after == {"Sol Ring": False, "Azula": True, "Partner": False}


@pytest.mark.integration
async def test_a_commander_is_refused_when_deck_cards_fall_outside_its_identity(
    client: AsyncClient,
) -> None:
    deck, ids = await deck_holding(
        client,
        {
            "Ezuri": await insert_card("Ezuri", type_line=LEGENDARY, commander=True, colors=["G"]),
            "Azula": await insert_card(
                "Azula", type_line=LEGENDARY, commander=True, colors=["U", "B", "R"]
            ),
            "Counterspell": await insert_card("Counterspell", colors=["U"]),
        },
    )

    green_status, green = await set_commanders(client, deck, [ids["Ezuri"]])
    blue_status, blue = await set_commanders(client, deck, [ids["Azula"]])

    assert green_status == 409
    assert "Counterspell" in str(green["detail"])
    assert "identidade de cor" in str(green["detail"])
    assert blue_status == 409
    assert "Ezuri" in str(blue["detail"])
    assert "Counterspell" not in str(blue["detail"])


@pytest.mark.integration
async def test_clearing_the_commanders_is_always_allowed_and_frees_the_deck(
    client: AsyncClient,
) -> None:
    deck, ids = await deck_holding(
        client,
        {
            "Azula": await insert_card(
                "Azula", type_line=LEGENDARY, commander=True, colors=["U", "B", "R"]
            ),
            "Counterspell": await insert_card("Counterspell", colors=["U"]),
            "Sol Ring": await insert_card("Sol Ring"),
        },
    )

    first, _ = await set_commanders(client, deck, [ids["Azula"]])
    cleared, _ = await set_commanders(client, deck, [])

    assert (first, cleared) == (200, 200)


@pytest.mark.integration
async def test_dropping_one_of_two_commanders_is_refused_if_cards_need_its_colors(
    client: AsyncClient,
) -> None:
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
            "Llanowar Elves": await insert_card("Llanowar Elves", colors=["G"]),
        },
    )

    both, _ = await set_commanders(client, deck, [ids["Partner R"], ids["Partner G"]])
    only_red, body = await set_commanders(client, deck, [ids["Partner R"]])

    assert both == 200
    assert only_red == 409
    assert "Llanowar Elves" in str(body["detail"])
