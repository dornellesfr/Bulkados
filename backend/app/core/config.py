from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

type Environment = Literal["development", "test", "production"]


class Settings(BaseSettings):
    """Configuração carregada do ambiente e do arquivo `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Magic Bulk API"
    environment: Environment = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/magic_bulk"
    supabase_url: str = ""
    supabase_anon_key: SecretStr = SecretStr("")
    supabase_service_role_key: SecretStr = SecretStr("")
    supabase_jwt_secret: SecretStr = SecretStr("")
    supabase_jwks_url: str = ""
    admin_email: str = ""
    admin_password: SecretStr = SecretStr("")
    scryfall_api_url: str = "https://api.scryfall.com"
    scryfall_user_agent: str = "MagicBulkBackend/0.1"

    @field_validator("database_url")
    @classmethod
    def database_url_must_use_asyncpg(cls, value: str) -> str:
        scheme = "postgresql+asyncpg://"
        if not value.startswith(scheme):
            message = "database_url must start with postgresql+asyncpg://"
            raise ValueError(message)
        return value

    @field_validator("supabase_url", "supabase_jwks_url", "scryfall_api_url")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
