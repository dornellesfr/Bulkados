import pytest
from pydantic import ValidationError

from app.schemas.health import HealthResponse


def test_health_response_accepts_ok() -> None:
    payload = HealthResponse(status="ok")

    assert payload.status == "ok"


def test_health_response_rejects_unknown_status() -> None:
    with pytest.raises(ValidationError):
        HealthResponse.model_validate({"status": "degraded"})
