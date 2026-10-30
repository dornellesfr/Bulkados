from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import Catalog, CurrentUser, DbSession
from app.schemas.catalog import CatalogCardRead
from app.services import catalog as catalog_service

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/cards", response_model=list[CatalogCardRead])
async def search_cards(
    session: DbSession,
    catalog: Catalog,
    _user: CurrentUser,
    q: Annotated[str, Query(min_length=1, max_length=200)],
) -> list[CatalogCardRead]:
    return await catalog_service.search_cards(session, catalog, q)
