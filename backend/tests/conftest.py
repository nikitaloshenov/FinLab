import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("APP_NAME", "FinLab")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("API_V1_PREFIX", "/api/v1")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://finlab:finlab@localhost:5432/finlab",
)
os.environ.setdefault("MOEX_BASE_URL", "https://iss.moex.com/iss")
os.environ.setdefault("MOEX_DEFAULT_ENGINE", "stock")
os.environ.setdefault("MOEX_DEFAULT_MARKET", "shares")
os.environ.setdefault("MOEX_DEFAULT_BOARD", "TQBR")
os.environ.setdefault("MOEX_TIMEOUT_SECONDS", "15")
os.environ.setdefault("MOEX_RETRY_ATTEMPTS", "2")
os.environ.setdefault("MOEX_RETRY_DELAY_SECONDS", "0.5")
os.environ.setdefault(
    "BACKEND_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)

from app.core.database import get_db
from app.main import app


class FakeDb:
    pass


@pytest.fixture
def client():
    def override_get_db():
        yield FakeDb()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
