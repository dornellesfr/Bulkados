import logging
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import SessionFactory
from app.core.errors import (
    AuthProviderUnavailableError,
    InvalidCredentialsError,
    InvalidTokenError,
    RegistrationRejectedError,
)
from app.core.security import user_id_from_access_token
from app.domain.identity import ADMIN_LEVEL, ADMIN_NICK, normalize_email
from app.integrations.auth import AuthProvider
from app.integrations.supabase import SupabaseAuthProvider
from app.models.user import User

logger = logging.getLogger(__name__)

DEVELOPMENT_ADMIN_PASSWORD = "@bulkados1234"


def admin_password(settings: Settings) -> str | None:
    """A senha configurada; sem ela, o padrão só vale em desenvolvimento."""
    configured = settings.admin_password.get_secret_value()
    if configured:
        return configured
    return DEVELOPMENT_ADMIN_PASSWORD if settings.environment == "development" else None


async def bootstrap_admin() -> None:
    """Cria o admin no startup. Nunca derruba a subida: só registra o que deu errado."""
    settings = get_settings()
    if settings.environment == "test":
        return
    try:
        async with SessionFactory() as session:
            await ensure_admin(session, SupabaseAuthProvider(settings), settings)
            await session.commit()
    except Exception:
        logger.exception("admin: falha ao garantir o usuário admin")


async def ensure_admin(session: AsyncSession, auth: AuthProvider, settings: Settings) -> None:
    """Cria o admin se ele não existir. Nunca promove um usuário que já exista."""
    password = admin_password(settings)
    if not settings.admin_email or password is None:
        logger.warning("admin: defina ADMIN_EMAIL e ADMIN_PASSWORD, usuário admin não criado")
        return
    try:
        email = normalize_email(settings.admin_email)
    except ValueError:
        logger.warning("admin: ADMIN_EMAIL inválido, usuário admin não criado")
        return

    existing = await session.scalar(
        select(User).where(or_(User.nick_normalized == ADMIN_NICK, User.email == email))
    )
    if existing is not None:
        if existing.level != ADMIN_LEVEL:
            logger.warning("admin: o nick ou o e-mail do admin já é de um usuário comum")
        return

    user_id = await _auth_user_id(auth, email, password, settings)
    if user_id is None:
        return
    session.add(
        User(
            id=user_id,
            email=email,
            nick=ADMIN_NICK,
            nick_normalized=ADMIN_NICK,
            level=ADMIN_LEVEL,
        )
    )
    await session.flush()
    logger.info("admin: usuário %s criado", ADMIN_NICK)


async def _auth_user_id(
    auth: AuthProvider,
    email: str,
    password: str,
    settings: Settings,
) -> UUID | None:
    try:
        return await auth.sign_up(email, password, ADMIN_NICK)
    except RegistrationRejectedError:
        pass  # já existe no provedor (banco local recriado, por exemplo): reaproveita o id
    except AuthProviderUnavailableError:
        logger.warning("admin: provedor de autenticação indisponível, usuário admin não criado")
        return None
    try:
        session = await auth.sign_in(email, password)
        return await user_id_from_access_token(session.access_token, settings)
    except (InvalidCredentialsError, AuthProviderUnavailableError, InvalidTokenError):
        logger.warning(
            "admin: não foi possível criar nem entrar com esse e-mail e senha "
            "(senha curta demais, ou o e-mail já existe no provedor com outra senha)"
        )
        return None
