from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    AuthProviderUnavailableError,
    DomainError,
    InvalidCredentialsError,
    RegistrationRejectedError,
)
from app.integrations.auth import AuthProvider, AuthSession
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MeResponse,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)

FORGOT_MESSAGE = "If an account exists, password reset instructions were sent."


async def register(
    session: AsyncSession,
    auth: AuthProvider,
    body: RegisterRequest,
) -> RegisterResponse:
    normalized = body.nick.lower()
    taken = await session.scalar(select(User.id).where(User.nick_normalized == normalized))
    if taken is not None:
        raise DomainError(409, "nick already taken")
    try:
        user_id = await auth.sign_up(body.email, body.password, body.nick)
    except RegistrationRejectedError as exc:
        raise DomainError(409, "could not register") from exc
    except AuthProviderUnavailableError as exc:
        raise DomainError(503, "authentication provider unavailable") from exc

    user = User(id=user_id, email=body.email, nick=body.nick, nick_normalized=normalized)
    try:
        async with session.begin_nested():
            session.add(user)
            await session.flush()
    except IntegrityError:
        await auth.delete_user(user_id)
        raise DomainError(409, "nick already taken") from None

    tokens = await _sign_in(auth, body.email, body.password)
    return RegisterResponse(
        id=user.id,
        nick=user.nick,
        email=user.email,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


async def login(
    session: AsyncSession,
    auth: AuthProvider,
    body: LoginRequest,
) -> TokenResponse:
    identifier = body.identifier.strip()
    by_nick = "@" not in identifier
    if by_nick:
        user = await session.scalar(select(User).where(User.nick_normalized == identifier.lower()))
        if user is None:
            raise DomainError(401, "invalid credentials")
        email = user.email
    else:
        email = identifier.lower()
    tokens = await _sign_in(auth, email, body.password)
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        email=None if by_nick else email,
    )


async def refresh(auth: AuthProvider, body: RefreshRequest) -> TokenResponse:
    try:
        tokens = await auth.refresh(body.refresh_token)
    except InvalidCredentialsError as exc:
        raise DomainError(401, "invalid credentials") from exc
    except AuthProviderUnavailableError as exc:
        raise DomainError(503, "authentication provider unavailable") from exc
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
    identifier = body.identifier.strip()
    email: str | None
    if "@" in identifier:
        email = identifier.lower()
    else:
        user = await session.scalar(select(User).where(User.nick_normalized == identifier.lower()))
        email = user.email if user is not None else None
    if email is not None:
        try:
            await auth.request_password_reset(email)
        except AuthProviderUnavailableError as exc:
            raise DomainError(503, "authentication provider unavailable") from exc
    return MessageResponse(message=FORGOT_MESSAGE)


def me(user: User) -> MeResponse:
    return MeResponse(id=user.id, nick=user.nick)


async def _sign_in(auth: AuthProvider, email: str, password: str) -> AuthSession:
    try:
        return await auth.sign_in(email, password)
    except InvalidCredentialsError as exc:
        raise DomainError(401, "invalid credentials") from exc
    except AuthProviderUnavailableError as exc:
        raise DomainError(503, "authentication provider unavailable") from exc
