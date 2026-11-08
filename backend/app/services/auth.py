import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import (
    AuthProviderUnavailableError,
    DomainError,
    InvalidCredentialsError,
    RegistrationRejectedError,
)
from app.core.security import AccessTokenClaims
from app.domain.identity import ADMIN_LEVEL, USER_LEVEL, normalize_email
from app.integrations.auth import AuthProvider, AuthSession
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MeResponse,
    MessageResponse,
    PasswordChangeRequest,
    ProfileUpdate,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)

EMAIL_TAKEN = "Já existe uma conta com esse e-mail."
COULD_NOT_REGISTER = (
    "Não foi possível criar a conta. Se você já tem uma, entre ou recupere a senha."
)
AUTH_UNAVAILABLE = "Não foi possível falar com o login agora. Tente de novo em instantes."
INVALID_CREDENTIALS = "E-mail ou senha incorretos."
FORGOT_MESSAGE = "Se existir uma conta com esse e-mail, enviamos as instruções para trocar a senha."
CURRENT_PASSWORD_WRONG = "A senha atual não confere."
PASSWORD_UNCHANGED = "A nova senha precisa ser diferente da atual."
PASSWORD_REJECTED = "Não foi possível salvar essa senha. Use pelo menos 6 caracteres."

logger = logging.getLogger(__name__)


async def ensure_local_user(
    session: AsyncSession,
    claims: AccessTokenClaims,
    settings: Settings,
) -> User | None:
    """Recria a linha local de um usuário que já existe no provedor de auth."""
    if claims.email is None:
        return None
    try:
        email = normalize_email(claims.email)
    except ValueError:
        return None

    first_name, last_name = _recovered_names(claims, email)
    user: User | None = User(
        id=claims.user_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        level=_recovered_level(email, settings),
    )
    try:
        async with session.begin_nested():
            session.add(user)
            await session.flush()
    except IntegrityError:
        user = await session.get(User, claims.user_id)
        if user is None or user.email != email:
            return None
    logger.info("auth: usuário local recriado a partir do token: %s", email)
    return user


def _recovered_names(claims: AccessTokenClaims, email: str) -> tuple[str, str]:
    first_name = (
        _text_claim(claims.user_metadata.get("first_name"))
        or _text_claim(claims.user_metadata.get("nick"))
        or email.split("@", 1)[0]
    )
    last_name = _text_claim(claims.user_metadata.get("last_name")) or "Conta"
    return first_name[:80], last_name[:80]


def _text_claim(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _recovered_level(email: str, settings: Settings) -> int:
    if settings.admin_email:
        try:
            if normalize_email(settings.admin_email) == email:
                return ADMIN_LEVEL
        except ValueError:
            return USER_LEVEL
    return USER_LEVEL


async def create_user(
    session: AsyncSession,
    auth: AuthProvider,
    body: RegisterRequest,
    level: int = USER_LEVEL,
) -> User:
    taken = await session.scalar(select(User.id).where(User.email == body.email))
    if taken is not None:
        raise DomainError(409, EMAIL_TAKEN)
    try:
        user_id = await auth.sign_up(body.email, body.password)
    except RegistrationRejectedError as exc:
        raise DomainError(409, COULD_NOT_REGISTER) from exc
    except AuthProviderUnavailableError as exc:
        raise DomainError(503, AUTH_UNAVAILABLE) from exc

    user = User(
        id=user_id,
        email=body.email,
        first_name=body.first_name,
        last_name=body.last_name,
        level=level,
    )
    try:
        async with session.begin_nested():
            session.add(user)
            await session.flush()
    except IntegrityError:
        await auth.delete_user(user_id)
        raise DomainError(409, EMAIL_TAKEN) from None
    return user


async def register(
    session: AsyncSession,
    auth: AuthProvider,
    body: RegisterRequest,
) -> RegisterResponse:
    user = await create_user(session, auth, body)
    tokens = await _sign_in(auth, body.email, body.password)
    return RegisterResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


async def login(auth: AuthProvider, body: LoginRequest) -> TokenResponse:
    tokens = await _sign_in(auth, body.email, body.password)
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


async def refresh(auth: AuthProvider, body: RefreshRequest) -> TokenResponse:
    try:
        tokens = await auth.refresh(body.refresh_token)
    except InvalidCredentialsError as exc:
        raise DomainError(401, INVALID_CREDENTIALS) from exc
    except AuthProviderUnavailableError as exc:
        raise DomainError(503, AUTH_UNAVAILABLE) from exc
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


async def forgot_password(
    session: AsyncSession,
    auth: AuthProvider,
    body: ForgotPasswordRequest,
) -> MessageResponse:
    known = await session.scalar(select(User.id).where(User.email == body.email))
    if known is not None:
        try:
            await auth.request_password_reset(body.email)
        except AuthProviderUnavailableError as exc:
            raise DomainError(503, AUTH_UNAVAILABLE) from exc
    return MessageResponse(message=FORGOT_MESSAGE)


async def change_password(auth: AuthProvider, user: User, body: PasswordChangeRequest) -> None:
    if body.current_password == body.new_password:
        raise DomainError(422, PASSWORD_UNCHANGED)
    try:
        tokens = await auth.sign_in(user.email, body.current_password)
    except InvalidCredentialsError as exc:
        raise DomainError(400, CURRENT_PASSWORD_WRONG) from exc
    except AuthProviderUnavailableError as exc:
        raise DomainError(503, AUTH_UNAVAILABLE) from exc
    try:
        await auth.update_password(tokens.access_token, body.new_password)
    except InvalidCredentialsError as exc:
        raise DomainError(422, PASSWORD_REJECTED) from exc
    except AuthProviderUnavailableError as exc:
        raise DomainError(503, AUTH_UNAVAILABLE) from exc


def me(user: User) -> MeResponse:
    return MeResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        created_at=user.created_at,
    )


async def update_profile(user: User, body: ProfileUpdate) -> MeResponse:
    user.first_name = body.first_name
    user.last_name = body.last_name
    return me(user)


async def _sign_in(auth: AuthProvider, email: str, password: str) -> AuthSession:
    try:
        return await auth.sign_in(email, password)
    except InvalidCredentialsError as exc:
        raise DomainError(401, INVALID_CREDENTIALS) from exc
    except AuthProviderUnavailableError as exc:
        raise DomainError(503, AUTH_UNAVAILABLE) from exc
