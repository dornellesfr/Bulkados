import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

# Antes de importar a aplicação: no ambiente de teste o admin do startup não é criado.
os.environ["ENVIRONMENT"] = "test"

from app.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client
