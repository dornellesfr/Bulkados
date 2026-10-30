import logging
from uuid import UUID

import httpx

from app.core.config import Settings
from app.core.errors import (
    AuthProviderUnavailableError,
    InvalidCredentialsError,
    RegistrationRejectedError,
)
from app.integrations.auth import AuthSession

logger = logging.getLogger(__name__)


class SupabaseAuthProvider:
    """Cliente do Supabase Auth. A service role só sai daqui no header da chamada admin."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.supabase_url.rstrip("/")

    async def sign_up(self, email: str, password: str, nick: str) -> UUID:
        self._require_service_role()
        response = await self._send(
            "POST",
            "/auth/v1/admin/users",
            self._service_headers(),
            {
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"nick": nick},
            },
        )
        if response.status_code in {400, 409, 422}:
            raise RegistrationRejectedError
        if response.status_code not in {200, 201}:
            logger.warning("supabase sign up failed with status %s", response.status_code)
            raise AuthProviderUnavailableError
        user_id = _uuid_field(_json_object(response), "id")
        if user_id is None:
            raise AuthProviderUnavailableError
        return user_id

    async def sign_in(self, email: str, password: str) -> AuthSession:
        self._require_anon_key()
        response = await self._send(
            "POST",
            "/auth/v1/token",
            self._anon_headers(),
            {"email": email, "password": password},
            params={"grant_type": "password"},
        )
        if response.status_code == 400:
            raise InvalidCredentialsError
        if response.status_code != 200:
            logger.warning("supabase sign in failed with status %s", response.status_code)
            raise AuthProviderUnavailableError
        return _session(_json_object(response))

    async def refresh(self, refresh_token: str) -> AuthSession:
        self._require_anon_key()
        response = await self._send(
            "POST",
            "/auth/v1/token",
            self._anon_headers(),
            {"refresh_token": refresh_token},
            params={"grant_type": "refresh_token"},
        )
        if response.status_code == 400:
            raise InvalidCredentialsError
        if response.status_code != 200:
            logger.warning("supabase refresh failed with status %s", response.status_code)
            raise AuthProviderUnavailableError
        return _session(_json_object(response))

    async def request_password_reset(self, email: str) -> None:
        self._require_anon_key()
        response = await self._send(
            "POST",
            "/auth/v1/recover",
            self._anon_headers(),
            {"email": email},
        )
        if response.status_code < 500:
            return
        logger.warning("supabase recover failed with status %s", response.status_code)
        raise AuthProviderUnavailableError

    async def delete_user(self, user_id: UUID) -> None:
        self._require_service_role()
        response = await self._send(
            "DELETE",
            f"/auth/v1/admin/users/{user_id}",
            self._service_headers(),
            None,
        )
        if response.status_code not in {200, 204, 404}:
            logger.warning("supabase delete user failed with status %s", response.status_code)

    def _require_service_role(self) -> None:
        if not self._base_url or not self._settings.supabase_service_role_key.get_secret_value():
            raise AuthProviderUnavailableError

    def _require_anon_key(self) -> None:
        if not self._base_url or not self._settings.supabase_anon_key.get_secret_value():
            raise AuthProviderUnavailableError

    def _anon_headers(self) -> dict[str, str]:
        key = self._settings.supabase_anon_key.get_secret_value()
        return _auth_headers(key)

    def _service_headers(self) -> dict[str, str]:
        key = self._settings.supabase_service_role_key.get_secret_value()
        return _auth_headers(key)

    async def _send(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: dict[str, object] | None,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                return await client.request(
                    method,
                    f"{self._base_url}{path}",
                    headers=headers,
                    json=body,
                    params=params,
                )
        except httpx.HTTPError as exc:
            logger.warning("supabase request failed")
            raise AuthProviderUnavailableError from exc


def _auth_headers(key: str) -> dict[str, str]:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _json_object(response: httpx.Response) -> dict[str, object]:
    payload: object = response.json()
    if not isinstance(payload, dict):
        raise AuthProviderUnavailableError
    result: dict[str, object] = {}
    for key, value in payload.items():
        if isinstance(key, str):
            result[key] = value
    return result


def _session(payload: dict[str, object]) -> AuthSession:
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    expires_in = payload.get("expires_in")
    if not isinstance(access_token, str) or not isinstance(refresh_token, str):
        raise AuthProviderUnavailableError
    if not isinstance(expires_in, int):
        expires_in = 3600
    return AuthSession(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


def _uuid_field(payload: dict[str, object], key: str) -> UUID | None:
    raw = payload.get(key)
    if not isinstance(raw, str):
        return None
    try:
        return UUID(raw)
    except ValueError:
        return None
