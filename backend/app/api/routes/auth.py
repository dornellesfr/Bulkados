from fastapi import APIRouter

from app.api.deps import Auth, CurrentUser, DbSession
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
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    body: RegisterRequest,
    session: DbSession,
    auth: Auth,
) -> RegisterResponse:
    return await auth_service.register(session, auth, body)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, auth: Auth) -> TokenResponse:
    return await auth_service.login(auth, body)


@router.post("/password", status_code=204)
async def change_password(
    body: PasswordChangeRequest,
    user: CurrentUser,
    auth: Auth,
) -> None:
    await auth_service.change_password(auth, user, body)


@router.post("/refresh", response_model=TokenResponse)
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


@me_router.patch("/me", response_model=MeResponse)
async def update_me(body: ProfileUpdate, user: CurrentUser) -> MeResponse:
    return await auth_service.update_profile(user, body)
