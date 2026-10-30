import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


def test_service_role_is_hidden_from_settings_repr() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/magic_bulk",
        supabase_service_role_key=SecretStr("super-secret-role"),
    )

    assert "super-secret-role" not in repr(settings)


def test_register_rejects_invalid_nick() -> None:
    from app.schemas.auth import RegisterRequest

    with pytest.raises(ValidationError):
        RegisterRequest(email="ada@example.com", password="password123", nick="A")
