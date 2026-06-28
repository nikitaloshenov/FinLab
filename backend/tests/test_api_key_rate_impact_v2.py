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
    assert data["event_direction"] == "all"
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
    assert data["sector_comparison"]["status"] == "no_sector_mapping"


def test_key_rate_impact_v2_filters_events_by_direction(api_client):
    client, SessionLocal = api_client
    session = SessionLocal()
    try:
        instrument = _seed_instrument(session)
        event_type = _seed_event_type(session)
        _seed_event(
            session,
            event_type,
            event_date=date(2024, 1, 3),
            direction="hike",
        )
        _seed_event(
            session,
            event_type,
            event_date=date(2024, 1, 10),
            direction="cut",
        )
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 3), close=Decimal("100"))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 4), close=Decimal("110"))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 10), close=Decimal("100"))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 11), close=Decimal("90"))
        session.commit()
    finally:
        session.close()

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/v2",
        json={
            "secid": "SBER",
            "event_direction": "hike",
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
            "horizons": [1],
            "auto_prepare_data": False,
            "include_sector_comparison": False,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["event_direction"] == "hike"
    assert data["events_total"] == 1
    assert data["events_processed"] == 1
    assert Decimal(str(data["summary"][0]["average_return_percent"])) == Decimal("10.0")
    assert data["sample_results"][0]["event_date"] == "2024-01-03"


def test_key_rate_impact_v2_defaults_to_main_horizons_when_omitted(api_client):
    client, SessionLocal = api_client
    session = SessionLocal()
    try:
        instrument = _seed_instrument(session)
        event_type = _seed_event_type(session)
        _seed_event(session, event_type, event_date=date(2024, 1, 3))
        for index in range(0, 12):
            _seed_daily_candle(
                session,
                instrument,
                trading_date=date(2024, 1, 3 + index),
                close=Decimal("100") + Decimal(index),
            )
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
            "include_sector_comparison": False,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["horizons"] == [1, 5, 10]
    assert [item["horizon_trading_days"] for item in data["summary"]] == [1, 5, 10]
    assert 20 not in data["horizons"]


@pytest.mark.parametrize(
    ("event_direction", "expected_direction", "expected_count", "expected_return"),
    [
        ("all", "all", 3, Decimal("1.666667")),
        ("hike", "hike", 1, Decimal("10.0")),
        ("rate_hike", "hike", 1, Decimal("10.0")),
        ("cut", "cut", 1, Decimal("-10.0")),
        ("rate_cut", "cut", 1, Decimal("-10.0")),
        ("hold", "hold", 1, Decimal("5.0")),
        ("rate_hold", "hold", 1, Decimal("5.0")),
    ],
)
def test_key_rate_impact_v2_event_direction_aliases(
    api_client,
    event_direction,
    expected_direction,
    expected_count,
    expected_return,
):
    client, SessionLocal = api_client
    session = SessionLocal()
    try:
        instrument = _seed_instrument(session)
        event_type = _seed_event_type(session)
        _seed_event(session, event_type, event_date=date(2024, 1, 3), direction="hike")
        _seed_event(session, event_type, event_date=date(2024, 1, 10), direction="cut")
        _seed_event(session, event_type, event_date=date(2024, 1, 17), direction="hold")
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 3), close=Decimal("100"))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 4), close=Decimal("110"))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 10), close=Decimal("100"))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 11), close=Decimal("90"))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 17), close=Decimal("100"))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 18), close=Decimal("105"))
        session.commit()
    finally:
        session.close()

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/v2",
        json={
            "secid": "SBER",
            "event_direction": event_direction,
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
            "horizons": [1],
            "auto_prepare_data": False,
            "include_sector_comparison": False,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["event_direction"] == expected_direction
    assert data["events_total"] == expected_count
    assert Decimal(str(data["summary"][0]["average_return_percent"])) == expected_return


def test_key_rate_impact_v2_events_used_contains_real_per_event_returns(api_client):
    client, SessionLocal = api_client
    session = SessionLocal()
    try:
        instrument = _seed_instrument(session)
        event_type = _seed_event_type(session)
        _seed_event(session, event_type, event_date=date(2024, 1, 3), direction="hold")
        _seed_event(session, event_type, event_date=date(2024, 1, 10), direction="hold")
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 3), close=Decimal("100"))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 4), close=Decimal("110"))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 10), close=Decimal("100"))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 11), close=Decimal("80"))
        session.commit()
    finally:
        session.close()

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/v2",
        json={
            "secid": "SBER",
            "event_direction": "hold",
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
            "horizons": [1],
            "auto_prepare_data": False,
            "include_sector_comparison": False,
        },
    )

    assert response.status_code == 200

    data = response.json()
    used_returns = [
        Decimal(str(event["horizons"][0]["return_percent"]))
        for event in data["events"]["used"]
    ]

    assert data["events"]["used_total"] == 2
    assert Decimal(str(data["summary"][0]["average_return_percent"])) == Decimal("-5.0")
    assert used_returns == [Decimal("10.0"), Decimal("-20.0")]
    assert all(value != Decimal("-5.0") for value in used_returns)


def test_key_rate_impact_v2_partially_skipped_event_stays_used(api_client):
    client, SessionLocal = api_client
    session = SessionLocal()
    try:
        instrument = _seed_instrument(session)
        event_type = _seed_event_type(session)
        _seed_event(session, event_type, event_date=date(2024, 1, 3), direction="hold")
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 3), close=Decimal("100"))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 4), close=Decimal("110"))
        session.commit()
    finally:
        session.close()

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/v2",
        json={
            "secid": "SBER",
            "event_direction": "hold",
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
            "horizons": [1, 5],
            "auto_prepare_data": False,
            "include_sector_comparison": False,
        },
    )

    assert response.status_code == 200

    events = response.json()["events"]
    horizons = events["used"][0]["horizons"]

    assert events["used_total"] == 1
    assert events["skipped_total"] == 0
    assert [item["status"] for item in horizons] == ["success", "skipped"]
    assert horizons[1]["skipped_reason"] == "no_horizon_candles"


def test_key_rate_impact_v2_response_groups_used_and_skipped_events(api_client):
    client, SessionLocal = api_client
    session = SessionLocal()
    try:
        instrument = _seed_instrument(session)
        event_type = _seed_event_type(session)
        _seed_event(
            session,
            event_type,
            event_date=date(2024, 1, 3),
            direction="cut",
        )
        _seed_event(
            session,
            event_type,
            event_date=date(2024, 1, 5),
            direction="cut",
        )
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 3), close=Decimal("100"))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 4), close=Decimal("110"))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 5), close=Decimal("120"))
        session.commit()
    finally:
        session.close()

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/v2",
        json={
            "secid": "SBER",
            "event_direction": "cut",
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
            "horizons": [1],
            "auto_prepare_data": False,
            "include_sector_comparison": False,
        },
    )

    assert response.status_code == 200

    events = response.json()["events"]

    assert events["found_total"] == 2
    assert events["used_total"] == 1
    assert events["skipped_total"] == 1
    assert events["used"][0]["event_date"] == "2024-01-03"
    assert events["used"][0]["direction"] == "cut"
    assert Decimal(str(events["used"][0]["horizons"][0]["return_percent"])) == Decimal("10.0")
    assert events["skipped"][0]["event_date"] == "2024-01-05"
    assert events["skipped"][0]["reason"] == "no_horizon_candles"


def test_key_rate_impact_v2_sector_comparison_success(api_client):
    client, SessionLocal = api_client
    session = SessionLocal()
    try:
        sector = _seed_sector(session)
        instrument = _seed_instrument(session, sector=sector)
        peer = _seed_instrument(session, secid="VTBR", sector=sector)
        event_type = _seed_event_type(session)
        _seed_event(session, event_type, event_date=date(2024, 1, 3))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 3), close=Decimal("100"))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 4), close=Decimal("110"))
        _seed_daily_candle(session, peer, trading_date=date(2024, 1, 3), close=Decimal("100"))
        _seed_daily_candle(session, peer, trading_date=date(2024, 1, 4), close=Decimal("105"))
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
            "include_sector_comparison": True,
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["sector_comparison"]["status"] == "success"
    assert data["sector_comparison"]["sector"]["code"] == "finance"
    assert data["sector_comparison"]["peers_total"] == 1
    assert data["sector_comparison"]["peers_used"] == 1
    assert data["sector_comparison"]["peer_secids"] == ["VTBR"]
    sector_summary = data["sector_comparison"]["summary"][0]
    assert Decimal(str(sector_summary["selected_average_return_percent"])) == Decimal("10.0")
    assert Decimal(str(sector_summary["sector_average_return_percent"])) == Decimal("5.0")
    assert Decimal(str(sector_summary["excess_return_percent"])) == Decimal("5.0")


def test_key_rate_impact_v2_sector_peers_are_deduplicated(api_client):
    client, SessionLocal = api_client
    session = SessionLocal()
    try:
        sector = _seed_sector(session)
        instrument = _seed_instrument(session, sector=sector)
        peer = _seed_instrument(session, secid="VTBR", sector=sector)
        session.add(
            IssuerSectorHistory(
                issuer_id=peer.issuer_id,
                sector_id=sector.id,
                valid_from=date(2021, 1, 1),
            ),
        )
        event_type = _seed_event_type(session)
        _seed_event(session, event_type, event_date=date(2024, 1, 3))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 3), close=Decimal("100"))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 4), close=Decimal("110"))
        _seed_daily_candle(session, peer, trading_date=date(2024, 1, 3), close=Decimal("100"))
        _seed_daily_candle(session, peer, trading_date=date(2024, 1, 4), close=Decimal("105"))
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
            "include_sector_comparison": True,
        },
    )

    sector_comparison = response.json()["sector_comparison"]

    assert response.status_code == 200
    assert sector_comparison["peers_total"] == 1
    assert sector_comparison["peer_secids"] == ["VTBR"]
    assert "SBER" not in sector_comparison["peer_secids"]


def test_key_rate_impact_v2_sector_comparison_can_be_disabled(api_client):
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
            "secid": "SBER",
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
            "horizons": [1],
            "auto_prepare_data": False,
            "include_sector_comparison": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["sector_comparison"]["status"] == "disabled"


def test_key_rate_impact_v2_sector_with_no_peers_returns_no_peers(api_client):
    client, SessionLocal = api_client
    session = SessionLocal()
    try:
        sector = _seed_sector(session)
        instrument = _seed_instrument(session, sector=sector)
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
            "secid": "SBER",
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
            "horizons": [1],
            "auto_prepare_data": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["sector_comparison"]["status"] == "no_peers"


def test_key_rate_impact_v2_missing_peer_candles_are_skipped(api_client):
    client, SessionLocal = api_client
    session = SessionLocal()
    try:
        sector = _seed_sector(session)
        instrument = _seed_instrument(session, sector=sector)
        _seed_instrument(session, secid="VTBR", sector=sector)
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
            "secid": "SBER",
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
            "horizons": [1],
            "auto_prepare_data": False,
            "auto_prepare_sector_data": False,
        },
    )

    sector_comparison = response.json()["sector_comparison"]

    assert response.status_code == 200
    assert sector_comparison["status"] == "insufficient_data"
    assert sector_comparison["peers_skipped"] == [
        {"secid": "VTBR", "reason": "missing_daily_candles"}
    ]
    assert sector_comparison["data_preparation"]["peers_skipped_due_to_missing_data"] == 1


def test_key_rate_impact_v2_auto_prepare_sector_data_respects_peer_limit(
    api_client,
    monkeypatch,
):
    client, SessionLocal = api_client
    imported_secids = []
    session = SessionLocal()
    try:
        sector = _seed_sector(session)
        instrument = _seed_instrument(session, sector=sector)
        _seed_instrument(session, secid="AONE", sector=sector)
        _seed_instrument(session, secid="BTWO", sector=sector)
        event_type = _seed_event_type(session)
        _seed_event(session, event_type, event_date=date(2024, 1, 3))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 3), close=Decimal("100"))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 4), close=Decimal("110"))
        session.commit()
    finally:
        session.close()

    def fake_import_candles(db, secid, date_from, date_to, interval="1d"):
        imported_secids.append(secid)
        peer = db.scalar(select(Instrument).where(Instrument.secid == secid))
        _seed_daily_candle(db, peer, trading_date=date(2024, 1, 3), close=Decimal("100"))
        _seed_daily_candle(db, peer, trading_date=date(2024, 1, 4), close=Decimal("101"))
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
            "auto_prepare_data": False,
            "auto_prepare_sector_data": True,
            "sector_peer_limit": 1,
        },
    )

    sector_comparison = response.json()["sector_comparison"]

    assert response.status_code == 200
    assert imported_secids == ["AONE"]
    assert sector_comparison["peers_total"] == 2
    assert sector_comparison["peers_used"] == 1
    assert sector_comparison["data_preparation"]["sector_peer_candles_importer_ran_count"] == 1
    assert sector_comparison["data_preparation"]["sector_peer_candles_rows_loaded"] == 2


def test_key_rate_impact_v2_sector_peer_limit_validation(api_client):
    client, _ = api_client

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/v2",
        json={"secid": "SBER", "sector_peer_limit": 0},
    )

    assert response.status_code == 422


def test_key_rate_impact_v2_sector_comparison_uses_daily_candles_only(api_client):
    client, SessionLocal = api_client
    session = SessionLocal()
    try:
        sector = _seed_sector(session)
        instrument = _seed_instrument(session, sector=sector)
        peer = _seed_instrument(session, secid="VTBR", sector=sector)
        event_type = _seed_event_type(session)
        _seed_event(session, event_type, event_date=date(2024, 1, 3))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 3), close=Decimal("100"))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 4), close=Decimal("110"))
        _seed_intraday_candle(session, peer, trading_date=date(2024, 1, 3), close=Decimal("100"))
        _seed_intraday_candle(session, peer, trading_date=date(2024, 1, 4), close=Decimal("105"))
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

    sector_comparison = response.json()["sector_comparison"]

    assert response.status_code == 200
    assert sector_comparison["status"] == "insufficient_data"
    assert sector_comparison["peers_skipped"][0]["reason"] == "missing_daily_candles"


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


def test_key_rate_impact_v2_single_existing_candle_is_not_ready(api_client, monkeypatch):
    client, SessionLocal = api_client
    session = SessionLocal()
    try:
        instrument = _seed_instrument(session)
        event_type = _seed_event_type(session)
        _seed_event(session, event_type, event_date=date(2024, 1, 3))
        _seed_daily_candle(session, instrument, trading_date=date(2024, 1, 3), close=Decimal("100"))
        session.commit()
    finally:
        session.close()

    def fake_import_candles(db, secid, date_from, date_to, interval="1d"):
        instrument = db.scalar(select(Instrument).where(Instrument.secid == secid))
        _seed_daily_candle(db, instrument, trading_date=date(2024, 1, 4), close=Decimal("105"))
        db.commit()
        return CandleImportResult(
            secid=secid,
            interval=interval,
            date_from=date_from,
            date_to=date_to,
            rows_loaded=1,
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
            "include_sector_comparison": False,
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["events_processed"] == 1
    assert data["data_preparation"]["candles_importer_ran"] is True
    assert data["data_preparation"]["candles_rows_loaded"] == 1


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


def _seed_sector(session):
    sector = session.scalar(select(Sector).where(Sector.code == "finance"))
    if sector is not None:
        return sector

    sector = Sector(code="finance", name="Finance", is_active=True)
    session.add(sector)
    session.flush()
    return sector


def _seed_instrument(session, *, secid="SBER", sector=None):
    issuer = None
    if sector is not None:
        issuer = Issuer(
            name=f"{secid} issuer",
            short_name=f"{secid} issuer",
            country="RU",
            is_active=True,
        )
        session.add(issuer)
        session.flush()

    instrument = Instrument(
        issuer_id=issuer.id if issuer is not None else None,
        secid=secid,
        name=f"{secid} company",
        short_name=f"{secid} company",
        asset_type="share",
        board="TQBR",
        market="shares",
        engine="stock",
        currency="RUB",
        is_active=True,
    )
    session.add(instrument)
    session.flush()

    if issuer is not None:
        session.add(
            IssuerSectorHistory(
                issuer_id=issuer.id,
                sector_id=sector.id,
                valid_from=date(2000, 1, 1),
            ),
        )
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


def _seed_event(session, event_type, *, event_date: date, direction: str = "hold"):
    event = Event(
        event_type_id=event_type.id,
        source_event_id=f"event:{event_date.isoformat()}",
        event_date=event_date,
        title=f"Event {event_date.isoformat()}",
        direction=direction,
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
