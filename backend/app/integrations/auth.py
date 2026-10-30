from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AuthSession:
    access_token: str
    refresh_token: str
    expires_in: int


class AuthProvider(Protocol):
    async def sign_up(self, email: str, password: str, nick: str) -> UUID: ...

    async def sign_in(self, email: str, password: str) -> AuthSession: ...

    async def refresh(self, refresh_token: str) -> AuthSession: ...

    async def request_password_reset(self, email: str) -> None: ...

    async def delete_user(self, user_id: UUID) -> None: ...
