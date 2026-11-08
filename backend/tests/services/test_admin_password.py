from pydantic import SecretStr

from app.core.config import Environment, Settings
from app.services.admin_bootstrap import DEVELOPMENT_ADMIN_PASSWORD, admin_password


def _settings(environment: Environment, password: str = "") -> Settings:
    return Settings(environment=environment, admin_password=SecretStr(password))


def test_development_falls_back_to_the_default_password() -> None:
    assert admin_password(_settings("development")) == DEVELOPMENT_ADMIN_PASSWORD


def test_other_environments_have_no_default_password() -> None:
    assert admin_password(_settings("production")) is None
    assert admin_password(_settings("test")) is None


def test_a_configured_password_wins_everywhere() -> None:
    assert admin_password(_settings("production", "chosen-by-me")) == "chosen-by-me"
    assert admin_password(_settings("development", "chosen-by-me")) == "chosen-by-me"
