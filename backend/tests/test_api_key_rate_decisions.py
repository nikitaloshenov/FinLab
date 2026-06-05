from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.modules.hypotheses.key_rate_decisions_repository import (
    create_key_rate_decision,
)


@pytest.fixture
def api_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = SessionLocal()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client, SessionLocal

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_get_key_rate_decisions_empty_table_returns_empty_response(api_client):
    client, _ = api_client

    response = client.get("/api/v1/hypotheses/key-rate-decisions")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "limit": 100,
        "offset": 0,
    }


def test_get_key_rate_decisions_returns_seeded_rows(api_client):
    client, SessionLocal = api_client
    _seed_decisions(SessionLocal)

    response = client.get("/api/v1/hypotheses/key-rate-decisions")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 3
    assert data["limit"] == 100
    assert data["offset"] == 0
    assert [item["decision_date"] for item in data["items"]] == [
        "2026-05-15",
        "2026-02-14",
        "2026-01-16",
    ]
    assert data["items"][0]["rate_before"] == "16.00"
    assert data["items"][0]["rate_after"] == "15.50"
    assert data["items"][0]["meeting_date"] == "2026-05-15"
    assert data["items"][0]["effective_date"] == "2026-05-19"
    assert data["items"][0]["publication_datetime_msk"] is not None
    assert data["items"][0]["source_title"] == "Bank of Russia key rate decision"
    assert data["items"][0]["notes"] == "Curated official row."
    assert data["items"][1]["meeting_date"] is None
    assert data["items"][1]["effective_date"] is None
    assert data["items"][1]["publication_datetime_msk"] is None
    assert data["items"][1]["source_title"] is None
    assert data["items"][1]["notes"] is None


def test_get_key_rate_decisions_filters_direction_and_only_official(api_client):
    client, SessionLocal = api_client
    _seed_decisions(SessionLocal)

    direction_response = client.get(
        "/api/v1/hypotheses/key-rate-decisions",
        params={"direction": "rate_cut"},
    )
    official_response = client.get(
        "/api/v1/hypotheses/key-rate-decisions",
        params={"only_official": "true"},
    )

    assert direction_response.status_code == 200
    assert official_response.status_code == 200

    direction_data = direction_response.json()
    official_data = official_response.json()

    assert direction_data["total"] == 1
    assert direction_data["items"][0]["direction"] == "rate_cut"
    assert official_data["total"] == 2
    assert all(item["is_official"] is True for item in official_data["items"])


def test_get_key_rate_decisions_limit_and_offset(api_client):
    client, SessionLocal = api_client
    _seed_decisions(SessionLocal)

    response = client.get(
        "/api/v1/hypotheses/key-rate-decisions",
        params={"limit": 1, "offset": 1},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 3
    assert data["limit"] == 1
    assert data["offset"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["decision_date"] == "2026-02-14"


def test_get_key_rate_decisions_invalid_direction_returns_422(api_client):
    client, _ = api_client

    response = client.get(
        "/api/v1/hypotheses/key-rate-decisions",
        params={"direction": "invalid"},
    )

    assert response.status_code == 422


def _seed_decisions(SessionLocal):
    session = SessionLocal()

    try:
        create_key_rate_decision(
            session,
            _decision_data(
                decision_date=date(2026, 1, 16),
                direction="rate_hold",
                is_official=False,
            ),
        )
        create_key_rate_decision(
            session,
            _decision_data(
                decision_date=date(2026, 5, 15),
                direction="rate_cut",
                is_official=True,
                meeting_date=date(2026, 5, 15),
                effective_date=date(2026, 5, 19),
                publication_datetime_msk=datetime(2026, 5, 15, 13, 30, tzinfo=UTC),
                source_title="Bank of Russia key rate decision",
                notes="Curated official row.",
            ),
        )
        create_key_rate_decision(
            session,
            _decision_data(
                decision_date=date(2026, 2, 14),
                direction="rate_hike",
                is_official=True,
            ),
        )
        session.commit()
    finally:
        session.close()


def _decision_data(
    decision_date,
    direction,
    is_official=True,
    meeting_date=None,
    effective_date=None,
    publication_datetime_msk=None,
    source_title=None,
    notes=None,
):
    return {
        "decision_date": decision_date,
        "meeting_date": meeting_date,
        "effective_date": effective_date,
        "publication_datetime_msk": publication_datetime_msk,
        "rate_before": Decimal("16.00"),
        "rate_after": Decimal("15.50"),
        "change_bps": -50,
        "direction": direction,
        "title": f"Decision {decision_date.isoformat()}",
        "description": "Official imported decision.",
        "is_scheduled": True,
        "is_official": is_official,
        "source_url": "https://www.cbr.ru/",
        "source_title": source_title,
        "source_type": "manual_official_import",
        "source_note": "Test row for API tests.",
        "notes": notes,
    }
