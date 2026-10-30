from fastapi import APIRouter

from app.api.deps import Auth, CurrentUser, DbSession
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
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    body: RegisterRequest,
    session: DbSession,
    auth: Auth,
) -> RegisterResponse:
    return await auth_service.register(session, auth, body)


@router.post("/login", response_model=TokenResponse, response_model_exclude_none=True)
async def login(body: LoginRequest, session: DbSession, auth: Auth) -> TokenResponse:
    return await auth_service.login(session, auth, body)


@router.post("/refresh", response_model=TokenResponse, response_model_exclude_none=True)
async def refresh(body: RefreshRequest, auth: Auth) -> TokenResponse:
    return await auth_service.refresh(auth, body)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    session: DbSession,
    auth: Auth,
) -> MessageResponse:
    return await auth_service.forgot_password(session, auth, body)


me_router = APIRouter(tags=["auth"])


@me_router.get("/me", response_model=MeResponse)
async def me(user: CurrentUser) -> MeResponse:
    return auth_service.me(user)
