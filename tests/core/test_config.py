import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_accepts_asyncpg_url() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/magic_bulk",
    )

    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.api_v1_prefix == "/api/v1"


def test_settings_rejects_url_without_asyncpg() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="postgresql://postgres:postgres@localhost:5432/magic_bulk")


def test_settings_rejects_unknown_environment() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate(
            {
                "database_url": "postgresql+asyncpg://postgres:postgres@localhost:5432/magic_bulk",
                "environment": "staging",
            }
        )
