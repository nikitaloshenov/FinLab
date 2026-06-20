from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.modules.events.models import Event, EventType
from app.modules.hypotheses import key_rate_v2_service
from app.modules.market_data.models import PriceCandle
from app.modules.market_data.service import CandleImportResult
from app.modules.reference.models import Instrument


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


def test_key_rate_impact_v2_endpoint_works_when_data_is_prepared(api_client):
    client, SessionLocal = api_client
    session = SessionLocal()
    try:
        instrument = _seed_instrument(session)
        event_type = _seed_event_type(session)
        _seed_event(session, event_type, event_date=date(2024, 1, 3))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 3), close=Decimal("100"))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 4), close=Decimal("110"))
        session.commit()
    finally:
        session.close()

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/v2",
        json={
            "secid": "sber",
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
            "horizons": [1],
            "auto_prepare_data": False,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["study_run_id"] is not None
    assert data["secid"] == "SBER"
    assert data["instrument"]["secid"] == "SBER"
    assert data["event_type"] == "key_rate_decision"
    assert data["events_total"] == 1
    assert data["events_processed"] == 1
    assert data["events_skipped"] == 0
    assert data["horizons"] == [1]
    assert data["summary"][0]["sample_size"] == 1
    assert Decimal(str(data["summary"][0]["average_return_percent"])) == Decimal("10.0")
    assert data["data_preparation"]["key_rate_events_ready"] is True
    assert data["data_preparation"]["key_rate_events_importer_ran"] is False
    assert data["data_preparation"]["candles_ready"] is True
    assert data["data_preparation"]["candles_importer_ran"] is False


def test_key_rate_impact_v2_service_auto_prepares_events(api_client, monkeypatch):
    client, SessionLocal = api_client
    session = SessionLocal()
    try:
        instrument = _seed_instrument(session)
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 3), close=Decimal("100"))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 4), close=Decimal("101"))
        session.commit()
    finally:
        session.close()

    def fake_import_events(db, dry_run=False):
        event_type = _seed_event_type(db)
        _seed_event(db, event_type, event_date=date(2024, 1, 3))
        db.commit()

    monkeypatch.setattr(key_rate_v2_service, "import_key_rate_decisions_to_events", fake_import_events)

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/v2",
        json={
            "secid": "SBER",
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
            "horizons": [1],
            "auto_prepare_data": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["data_preparation"]["key_rate_events_importer_ran"] is True


def test_key_rate_impact_v2_service_auto_prepares_candles(api_client, monkeypatch):
    client, SessionLocal = api_client
    session = SessionLocal()
    try:
        _seed_instrument(session)
        event_type = _seed_event_type(session)
        _seed_event(session, event_type, event_date=date(2024, 1, 3))
        session.commit()
    finally:
        session.close()

    def fake_import_candles(db, secid, date_from, date_to, interval="1d"):
        instrument = db.scalar(select(Instrument).where(Instrument.secid == secid))
        _seed_daily_candle(db, instrument, trading_date=date(2024, 1, 3), close=Decimal("100"))
        _seed_daily_candle(db, instrument, trading_date=date(2024, 1, 4), close=Decimal("105"))
        db.commit()
        return CandleImportResult(
            secid=secid,
            interval=interval,
            date_from=date_from,
            date_to=date_to,
            rows_loaded=2,
            ingestion_run_id=1,
            status="success",
        )

    monkeypatch.setattr(key_rate_v2_service, "import_daily_candles", fake_import_candles)

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/v2",
        json={
            "secid": "SBER",
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
            "horizons": [1],
            "auto_prepare_data": True,
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["events_processed"] == 1
    assert data["data_preparation"]["candles_importer_ran"] is True
    assert data["data_preparation"]["candles_rows_loaded"] == 2


def test_key_rate_impact_v2_invalid_secid_returns_structured_error(api_client):
    client, _ = api_client

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/v2",
        json={"secid": "UNKNOWN", "auto_prepare_data": False},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "key_rate_v2_unknown_instrument"


def test_key_rate_impact_v2_invalid_horizons_rejected(api_client):
    client, _ = api_client

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/v2",
        json={"secid": "SBER", "horizons": [0]},
    )

    assert response.status_code == 422


def test_key_rate_impact_v2_date_from_after_date_to_rejected(api_client):
    client, _ = api_client

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/v2",
        json={
            "secid": "SBER",
            "date_from": "2024-02-01",
            "date_to": "2024-01-01",
        },
    )

    assert response.status_code == 422


def test_key_rate_impact_v2_no_events_with_auto_prepare_false_is_clear(api_client):
    client, SessionLocal = api_client
    session = SessionLocal()
    try:
        _seed_instrument(session)
        _seed_event_type(session)
        session.commit()
    finally:
        session.close()

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/v2",
        json={
            "secid": "SBER",
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
            "auto_prepare_data": False,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "key_rate_v2_data_not_prepared"


def test_key_rate_impact_v2_uses_daily_price_candles_only(api_client):
    client, SessionLocal = api_client
    session = SessionLocal()
    try:
        instrument = _seed_instrument(session)
        event_type = _seed_event_type(session)
        _seed_event(session, event_type, event_date=date(2024, 1, 3))
        _seed_intraday_candle(session, instrument, trading_date=date(2024, 1, 3), close=Decimal("100"))
        _seed_intraday_candle(session, instrument, trading_date=date(2024, 1, 4), close=Decimal("110"))
        session.commit()
    finally:
        session.close()

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/v2",
        json={
            "secid": "SBER",
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
            "horizons": [1],
            "auto_prepare_data": False,
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["events_total"] == 1
    assert data["events_processed"] == 0
    assert data["events_skipped"] == 1
    assert data["summary"][0]["sample_size"] == 0
    assert data["sample_results"][0]["status"] == "skipped"
    assert data["sample_results"][0]["skipped_reason"] == "no_event_candle"


def _seed_instrument(session):
    instrument = Instrument(
        secid="SBER",
        name="Sberbank",
        short_name="Sberbank",
        asset_type="share",
        board="TQBR",
        market="shares",
        engine="stock",
        currency="RUB",
        is_active=True,
    )
    session.add(instrument)
    session.flush()
    return instrument


def _seed_event_type(session):
    event_type = session.scalar(select(EventType).where(EventType.code == "key_rate_decision"))
    if event_type is not None:
        return event_type

    event_type = EventType(
        code="key_rate_decision",
        name="Key rate decision",
        description="Bank of Russia key rate decision event.",
        is_active=True,
    )
    session.add(event_type)
    session.flush()
    return event_type


def _seed_event(session, event_type, *, event_date: date):
    event = Event(
        event_type_id=event_type.id,
        source_event_id=f"event:{event_date.isoformat()}",
        event_date=event_date,
        title=f"Event {event_date.isoformat()}",
        direction="hold",
        importance="high",
    )
    session.add(event)
    session.flush()
    return event


def _seed_daily_candle(session, instrument, *, trading_date: date, close: Decimal):
    return _seed_candle(
        session,
        instrument,
        interval="1d",
        trading_date=trading_date,
        close=close,
    )


def _seed_intraday_candle(session, instrument, *, trading_date: date, close: Decimal):
    return _seed_candle(
        session,
        instrument,
        interval="10m",
        trading_date=trading_date,
        close=close,
    )


def _seed_candle(session, instrument, *, interval: str, trading_date: date, close: Decimal):
    candle = PriceCandle(
        instrument_id=instrument.id,
        interval=interval,
        begin_at=datetime.combine(trading_date, datetime.min.time(), tzinfo=UTC),
        trading_date=trading_date,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=Decimal("1000"),
        value=Decimal("100000"),
    )
    session.add(candle)
    session.flush()
    return candle
