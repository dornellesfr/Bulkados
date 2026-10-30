from functools import lru_cache
from typing import Literal

from pydantic import field_validator
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

    @field_validator("database_url")
    @classmethod
    def database_url_must_use_asyncpg(cls, value: str) -> str:
        scheme = "postgresql+asyncpg://"
        if not value.startswith(scheme):
            message = "database_url must start with postgresql+asyncpg://"
            raise ValueError(message)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
