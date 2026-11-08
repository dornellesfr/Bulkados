from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.identity import normalize_email, normalize_person_name


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str = Field(min_length=6, max_length=128)
    first_name: str
    last_name: str

    @field_validator("first_name")
    @classmethod
    def first_name_must_be_present(cls, value: str) -> str:
        return normalize_person_name(value, missing="Informe o nome.")

    @field_validator("last_name")
    @classmethod
    def last_name_must_be_present(cls, value: str) -> str:
        return normalize_person_name(value, missing="Informe o sobrenome.")

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        return normalize_email(value)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        return normalize_email(value)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1)


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        return normalize_email(value)


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str
    last_name: str

    @field_validator("first_name")
    @classmethod
    def first_name_must_be_present(cls, value: str) -> str:
        return normalize_person_name(value, missing="Informe o nome.")

    @field_validator("last_name")
    @classmethod
    def last_name_must_be_present(cls, value: str) -> str:
        return normalize_person_name(value, missing="Informe o sobrenome.")


class PasswordChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RegisterResponse(TokenResponse):
    id: UUID
    email: str
    first_name: str
    last_name: str


class MeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    email: str
    first_name: str
    last_name: str
    created_at: datetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
