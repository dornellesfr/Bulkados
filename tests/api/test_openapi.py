from fastapi.testclient import TestClient

EXPECTED_PATHS = {
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/forgot-password",
    "/api/v1/me",
    "/api/v1/groups",
    "/api/v1/groups/{group_id}",
    "/api/v1/groups/{group_id}/invitations",
    "/api/v1/invitations/{invitation_id}/accept",
    "/api/v1/invitations/{invitation_id}/decline",
    "/api/v1/groups/{group_id}/leave",
    "/api/v1/groups/{group_id}/members",
    "/api/v1/catalog/cards",
    "/api/v1/groups/{group_id}/copies",
    "/api/v1/copies/{copy_id}/groups",
    "/api/v1/copies/{copy_id}",
    "/api/v1/copies/{copy_id}/refresh-price",
    "/api/v1/groups/{group_id}/decks",
    "/api/v1/decks/{deck_id}",
    "/api/v1/decks/{deck_id}/commanders",
    "/api/v1/decks/{deck_id}/take",
    "/api/v1/decks/{deck_id}/copies",
    "/api/v1/decks/{deck_id}/cards/{card_copy_id}/move",
    "/api/v1/decks/{deck_id}/cards/{card_copy_id}/return",
    "/api/v1/decks/{deck_id}/cards/{card_copy_id}/lock",
    "/api/v1/decks/{deck_id}/cards/{card_copy_id}/unlock",
    "/api/v1/decks/{deck_id}/requests",
    "/api/v1/requests/{request_id}/accept",
    "/api/v1/requests/{request_id}/reject",
    "/api/v1/requests/{request_id}/cancel",
    "/api/v1/requests/{request_id}/confirm",
    "/api/v1/groups/{group_id}/handoffs",
}


def test_openapi_exposes_domain_routes(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    payload: object = response.json()
    assert isinstance(payload, dict)
    paths: object = payload["paths"]
    assert isinstance(paths, dict)
    missing = EXPECTED_PATHS - set(paths)
    assert missing == set()


def test_domain_tables_are_registered() -> None:
    from app.models import Base

    names = set(Base.metadata.tables)
    assert {
        "users",
        "groups",
        "group_members",
        "catalog_cards",
        "card_copies",
        "card_copy_groups",
        "decks",
        "deck_cards",
        "requests",
    } <= names
