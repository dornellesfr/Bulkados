from functools import lru_cache
from typing import Literal, Self

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

type Environment = Literal["development", "test", "production"]

DEFAULT_TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/magic_bulk_test"


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
    cors_origins: str = ""
    catalog_sync_enabled: bool = True
    db_pool_size: int = 10
    db_max_overflow: int = 20
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/magic_bulk"
    test_database_url: str = DEFAULT_TEST_DATABASE_URL
    supabase_url: str = ""
    supabase_anon_key: SecretStr = SecretStr("")
    supabase_service_role_key: SecretStr = SecretStr("")
    supabase_jwt_secret: SecretStr = SecretStr("")
    supabase_jwks_url: str = ""
    admin_email: str = ""
    admin_password: SecretStr = SecretStr("")
    scryfall_api_url: str = "https://api.scryfall.com"
    scryfall_user_agent: str = "MagicBulkBackend/0.1"

    @property
    def effective_database_url(self) -> str:
        """No modo test o banco é o local de teste; nos demais, o DATABASE_URL configurado."""
        if self.environment == "test":
            return self.test_database_url
        return self.database_url

    @property
    def cors_origin_list(self) -> list[str]:
        """Origens liberadas para o navegador, separadas por vírgula em CORS_ORIGINS."""
        return [
            origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()
        ]

    @field_validator("database_url")
    @classmethod
    def database_url_must_use_asyncpg(cls, value: str) -> str:
        scheme = "postgresql+asyncpg://"
        if not value.startswith(scheme):
            message = "database_url must start with postgresql+asyncpg://"
            raise ValueError(message)
        return value

    @field_validator("test_database_url")
    @classmethod
    def test_database_url_must_use_asyncpg(cls, value: str) -> str:
        if not value:
            return DEFAULT_TEST_DATABASE_URL
        scheme = "postgresql+asyncpg://"
        if not value.startswith(scheme):
            message = "test_database_url must start with postgresql+asyncpg://"
            raise ValueError(message)
        return value

    @model_validator(mode="after")
    def test_database_must_differ_from_app_database(self) -> Self:
        if self.environment == "test" and self.test_database_url == self.database_url:
            message = "test_database_url must differ from database_url"
            raise ValueError(message)
        return self

    @field_validator("supabase_url", "supabase_jwks_url", "scryfall_api_url")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
