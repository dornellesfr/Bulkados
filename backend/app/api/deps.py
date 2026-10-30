from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.errors import DomainError, InvalidTokenError
from app.core.security import user_id_from_access_token
from app.domain.identity import ADMIN_LEVEL
from app.domain.pricing import NullPriceProvider, PriceProvider
from app.integrations.auth import AuthProvider
from app.integrations.scryfall import CardCatalog, CatalogSource, scryfall_client
from app.integrations.supabase import SupabaseAuthProvider
from app.models.user import User

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise DomainError(401, "not authenticated")
    try:
        user_id = await user_id_from_access_token(credentials.credentials, get_settings())
    except InvalidTokenError as exc:
        raise DomainError(401, "not authenticated") from exc
    user = await session.get(User, user_id)
    if user is None:
        raise DomainError(401, "not authenticated")
    return user


async def get_admin_user(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.level != ADMIN_LEVEL:
        raise DomainError(403, "forbidden")
    return user


def get_auth_provider() -> AuthProvider:
    return SupabaseAuthProvider(get_settings())


def get_price_provider() -> PriceProvider:
    return NullPriceProvider()


def get_card_catalog() -> CardCatalog:
    return scryfall_client()


def get_catalog_source() -> CatalogSource:
    return scryfall_client()


CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(get_admin_user)]
Auth = Annotated[AuthProvider, Depends(get_auth_provider)]
Prices = Annotated[PriceProvider, Depends(get_price_provider)]
Catalog = Annotated[CardCatalog, Depends(get_card_catalog)]
CatalogFeed = Annotated[CatalogSource, Depends(get_catalog_source)]
