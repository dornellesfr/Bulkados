from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import Catalog, CurrentUser, DbSession
from app.schemas.catalog import CatalogCardRead
from app.services import catalog as catalog_service
from app.services.access import require_deck_owner
from app.services.deck_identity import deck_identities

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/cards", response_model=list[CatalogCardRead])
async def search_cards(
    session: DbSession,
    catalog: Catalog,
    user: CurrentUser,
    q: Annotated[str, Query(min_length=1, max_length=200)],
    deck_id: UUID | None = None,
) -> list[CatalogCardRead]:
    """Com `deck_id`, só sugere cartas que cabem na identidade de cor do deck."""
    within = None
    if deck_id is not None:
        deck = await require_deck_owner(session, deck_id, user.id)
        within = (await deck_identities(session, [deck.id])).get(deck.id)
    return await catalog_service.search_cards(session, catalog, q, within)
