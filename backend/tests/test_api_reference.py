from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.modules.reference.models import Instrument, Issuer, IssuerSectorHistory, Sector


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


def test_get_reference_instrument_returns_404_for_unknown_secid(api_client):
    client, _ = api_client

    response = client.get("/api/v1/reference/instruments/UNKNOWN")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "reference_instrument_not_found"


def test_get_reference_instrument_returns_summary(api_client):
    client, SessionLocal = api_client
    _seed_reference_data(SessionLocal)

    response = client.get("/api/v1/reference/instruments/sber")

    assert response.status_code == 200
    assert response.json() == {
        "secid": "SBER",
        "name": "Sberbank",
        "short_name": "Sber",
        "asset_type": "share",
        "engine": "stock",
        "market": "shares",
        "board": "TQBR",
        "currency": "RUB",
        "issuer": {
            "id": 1,
            "name": "Sberbank",
            "short_name": "Sberbank",
        },
        "sector": {
            "code": "finance",
            "name": "Finance",
        },
    }


def test_get_reference_instrument_prefers_tqbr_board(api_client):
    client, SessionLocal = api_client
    _seed_reference_data(SessionLocal, include_second_board=True)

    response = client.get("/api/v1/reference/instruments/SBER")

    assert response.status_code == 200
    assert response.json()["board"] == "TQBR"


def _seed_reference_data(SessionLocal, *, include_second_board=False):
    db = SessionLocal()

    try:
        issuer = Issuer(id=1, name="Sberbank", short_name="Sberbank", country="RU")
        sector = Sector(code="finance", name="Finance")
        instrument = Instrument(
            issuer=issuer,
            secid="SBER",
            name="Sberbank",
            short_name="Sber",
            asset_type="share",
            board="TQBR",
            market="shares",
            engine="stock",
            currency="RUB",
        )
        history = IssuerSectorHistory(
            issuer=issuer,
            sector=sector,
            valid_from=date(1900, 1, 1),
        )

        db.add_all([issuer, sector, instrument, history])

        if include_second_board:
            db.add(
                Instrument(
                    issuer=issuer,
                    secid="SBER",
                    name="Sberbank secondary board",
                    short_name="Sber secondary",
                    asset_type="share",
                    board="TQTF",
                    market="shares",
                    engine="stock",
                    currency="RUB",
                ),
            )

        db.commit()
    finally:
        db.close()
