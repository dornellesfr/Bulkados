from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.errors import DomainError, InvalidTokenError
from app.core.security import user_id_from_access_token
from app.integrations.auth import AuthProvider
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


def get_auth_provider() -> AuthProvider:
    return SupabaseAuthProvider(get_settings())


CurrentUser = Annotated[User, Depends(get_current_user)]
Auth = Annotated[AuthProvider, Depends(get_auth_provider)]
