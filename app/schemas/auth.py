from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.identity import normalize_email, normalize_nick


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str = Field(min_length=6, max_length=128)
    nick: str

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("nick")
    @classmethod
    def nick_must_be_valid(cls, value: str) -> str:
        return normalize_nick(value)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1)


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(min_length=1, max_length=320)


class TokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    email: str | None = None


class RegisterResponse(TokenResponse):
    id: UUID
    nick: str


class MeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    nick: str


class MessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
