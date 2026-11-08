import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

# Antes de importar a aplicação: o ambiente de teste usa TEST_DATABASE_URL
# (ou o Postgres local de teste) e não cria o admin do startup.
os.environ["ENVIRONMENT"] = "test"

from app.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client
