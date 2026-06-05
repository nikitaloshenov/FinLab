import re
from datetime import date
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
from app.modules.hypotheses import key_rate_impact_service
from app.modules.market.moex_client import MoexClientError


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


def test_key_rate_impact_valid_request_returns_report(api_client, monkeypatch):
    client, SessionLocal = api_client
    _seed_decisions(SessionLocal)
    monkeypatch.setattr(key_rate_impact_service, "MoexClient", FakeMoexClient)

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/analyze",
        json={
            "main_ticker": "sber",
            "direction": "rate_hike",
            "benchmark_ticker": "moex",
            "horizons": [1, 3, 10, 30],
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["main_ticker"] == "SBER"
    assert data["benchmark_ticker"] == "MOEX"
    assert data["direction"] == "rate_hike"
    assert data["horizons"] == [1, 3, 10, 30]
    assert data["decisions_total"] == 2
    assert data["horizon_summary"]
    assert data["benchmark_summary"]
    assert data["event_results"]
    assert data["metadata"]["source"] == "key_rate_impact_service"
    assert data["metadata"]["engine"] == "multi_event_validation"
    assert data["summary"]["main_ticker"] == "SBER"
    assert data["summary"]["company_name"] == "Сбербанк"
    assert data["summary"]["direction_label"] == "повышение ключевой ставки"
    assert data["summary"]["is_prediction"] is False
    assert data["confidence"]["level"] == "low"
    assert data["skipped_summary"]["skipped_total"] == data["decisions_skipped"]


def test_key_rate_impact_existing_response_keys_still_exist(
    api_client,
    monkeypatch,
):
    client, SessionLocal = api_client
    _seed_non_official_hike_decisions(SessionLocal)
    monkeypatch.setattr(key_rate_impact_service, "MoexClient", FakeMoexClient)

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/analyze",
        json={"main_ticker": "SBER", "direction": "rate_hike", "horizons": [1]},
    )

    assert response.status_code == 200

    data = response.json()
    expected_keys = {
        "main_ticker",
        "benchmark_ticker",
        "direction",
        "horizons",
        "decisions_total",
        "decisions_used",
        "decisions_skipped",
        "horizon_summary",
        "benchmark_summary",
        "event_results",
        "limitations",
        "metadata",
    }

    assert expected_keys.issubset(data.keys())


@pytest.mark.parametrize(
    ("direction", "direction_label"),
    [
        ("rate_cut", "снижение ключевой ставки"),
        ("rate_hike", "повышение ключевой ставки"),
        ("rate_hold", "сохранение ключевой ставки"),
    ],
)
def test_key_rate_impact_summary_direction_labels(
    api_client,
    direction,
    direction_label,
):
    client, _ = api_client

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/analyze",
        json={"main_ticker": "SBER", "direction": direction},
    )

    assert response.status_code == 200
    assert response.json()["summary"]["direction_label"] == direction_label


def test_key_rate_impact_best_horizon_exists_when_usable_data_exists(
    api_client,
    monkeypatch,
):
    client, SessionLocal = api_client
    _seed_non_official_hike_decisions(SessionLocal)
    monkeypatch.setattr(key_rate_impact_service, "MoexClient", FakeMoexClient)

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/analyze",
        json={
            "main_ticker": "SBER",
            "direction": "rate_hike",
            "horizons": [1],
            "only_official": False,
        },
    )

    assert response.status_code == 200

    best_horizon = response.json()["best_horizon"]

    assert best_horizon is not None
    assert best_horizon["horizon_days"] == 1
    assert best_horizon["horizon_label"] == "1 торговый день"
    assert best_horizon["events_with_data"] == 3
    assert best_horizon["typical_effect_label"]


def test_key_rate_impact_best_horizon_is_null_without_usable_data(
    api_client,
    monkeypatch,
):
    client, SessionLocal = api_client
    _seed_decisions(SessionLocal)
    monkeypatch.setattr(key_rate_impact_service, "MoexClient", FakeMoexClient)

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/analyze",
        json={"main_ticker": "SBER", "direction": "rate_hike", "horizons": [1]},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["decisions_total"] == 2
    assert data["best_horizon"] is None
    assert data["summary"]["result_type"] == "insufficient_data"


def test_key_rate_impact_insufficient_data_summary_uses_cautious_wording(
    api_client,
    monkeypatch,
):
    client, SessionLocal = api_client
    _seed_decisions(SessionLocal)
    monkeypatch.setattr(key_rate_impact_service, "MoexClient", FakeMoexClient)

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/analyze",
        json={"main_ticker": "SBER", "direction": "rate_hike", "horizons": [1]},
    )

    assert response.status_code == 200

    summary = response.json()["summary"]

    assert summary["result_type"] == "insufficient_data"
    assert summary["short_conclusion"] == (
        "Данных недостаточно для устойчивого вывода. Ниже показаны "
        "отдельные исторические наблюдения."
    )


def test_key_rate_impact_horizon_summary_contains_readable_labels(
    api_client,
    monkeypatch,
):
    client, SessionLocal = api_client
    _seed_decisions(SessionLocal)
    monkeypatch.setattr(key_rate_impact_service, "MoexClient", FakeMoexClient)

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/analyze",
        json={
            "main_ticker": "SBER",
            "direction": "rate_hike",
            "horizons": [1],
            "only_official": False,
        },
    )

    assert response.status_code == 200

    horizon = response.json()["horizon_summary"][0]

    assert horizon["horizon_label"] == "1 торговый день"
    assert horizon["typical_effect_label"]
    assert horizon["typical_direction_label"]


def test_key_rate_impact_uses_direction_filter(api_client, monkeypatch):
    client, SessionLocal = api_client
    _seed_decisions(SessionLocal)
    monkeypatch.setattr(key_rate_impact_service, "MoexClient", FakeMoexClient)

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/analyze",
        json={"main_ticker": "SBER", "direction": "rate_cut", "horizons": [1]},
    )

    assert response.status_code == 200
    assert response.json()["decisions_total"] == 1


def test_key_rate_impact_default_horizons_are_used(api_client, monkeypatch):
    client, SessionLocal = api_client
    _seed_decisions(SessionLocal)
    monkeypatch.setattr(key_rate_impact_service, "MoexClient", FakeMoexClient)

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/analyze",
        json={"main_ticker": "SBER", "direction": "rate_hike"},
    )

    assert response.status_code == 200
    assert response.json()["horizons"] == [1, 3, 10, 30]


def test_key_rate_impact_without_benchmark_returns_null_summary(
    api_client,
    monkeypatch,
):
    client, SessionLocal = api_client
    _seed_decisions(SessionLocal)
    monkeypatch.setattr(key_rate_impact_service, "MoexClient", FakeMoexClient)

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/analyze",
        json={
            "main_ticker": "SBER",
            "direction": "rate_hike",
            "benchmark_ticker": None,
            "horizons": [1],
        },
    )

    assert response.status_code == 200
    assert response.json()["benchmark_summary"] is None


def test_key_rate_impact_benchmark_failure_keeps_main_report(
    api_client,
    monkeypatch,
):
    client, SessionLocal = api_client
    _seed_decisions(SessionLocal)
    monkeypatch.setattr(
        key_rate_impact_service,
        "MoexClient",
        BenchmarkFailingMoexClient,
    )

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/analyze",
        json={
            "main_ticker": "SBER",
            "direction": "rate_hike",
            "benchmark_ticker": "MOEX",
            "horizons": [1],
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["benchmark_summary"] is None
    assert data["benchmark_ticker"] is None
    assert any("Benchmark comparison" in item for item in data["limitations"])


def test_key_rate_impact_no_decisions_returns_clean_report(
    api_client,
    monkeypatch,
):
    client, _ = api_client
    monkeypatch.setattr(key_rate_impact_service, "MoexClient", FakeMoexClient)

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/analyze",
        json={"main_ticker": "SBER", "direction": "rate_hike"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["decisions_total"] == 0
    assert data["horizon_summary"] == []
    assert data["event_results"] == []
    assert any("No key rate decisions" in item for item in data["limitations"])


def test_key_rate_impact_invalid_direction_returns_422(client):
    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/analyze",
        json={"main_ticker": "SBER", "direction": "invalid"},
    )

    assert response.status_code == 422


def test_key_rate_impact_invalid_horizons_return_422(client):
    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/analyze",
        json={
            "main_ticker": "SBER",
            "direction": "rate_hike",
            "horizons": [2],
        },
    )

    assert response.status_code == 422


def test_key_rate_impact_include_events_false_hides_events(api_client, monkeypatch):
    client, SessionLocal = api_client
    _seed_decisions(SessionLocal)
    monkeypatch.setattr(key_rate_impact_service, "MoexClient", FakeMoexClient)

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/analyze",
        json={
            "main_ticker": "SBER",
            "direction": "rate_hike",
            "horizons": [1],
            "include_events": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["event_results"] == []
    assert "skipped_summary" in response.json()


def test_key_rate_impact_main_ticker_failure_returns_structured_error(
    api_client,
    monkeypatch,
):
    client, SessionLocal = api_client
    _seed_decisions(SessionLocal)
    monkeypatch.setattr(key_rate_impact_service, "MoexClient", MainFailingMoexClient)

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/analyze",
        json={"main_ticker": "SBER", "direction": "rate_hike", "horizons": [1]},
    )

    assert response.status_code == 502
    assert (
        response.json()["detail"]["code"]
        == "key_rate_impact_market_data_unavailable"
    )


def test_key_rate_impact_same_benchmark_as_main_is_ignored(
    api_client,
    monkeypatch,
):
    client, SessionLocal = api_client
    _seed_decisions(SessionLocal)
    monkeypatch.setattr(key_rate_impact_service, "MoexClient", FakeMoexClient)

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/analyze",
        json={
            "main_ticker": "SBER",
            "direction": "rate_hike",
            "benchmark_ticker": "sber",
            "horizons": [1],
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["benchmark_ticker"] is None
    assert any("Benchmark ticker matched" in item for item in data["limitations"])


def test_key_rate_impact_response_has_no_forbidden_wording(api_client, monkeypatch):
    client, SessionLocal = api_client
    _seed_decisions(SessionLocal)
    monkeypatch.setattr(key_rate_impact_service, "MoexClient", FakeMoexClient)

    response = client.post(
        "/api/v1/hypotheses/key-rate-impact/analyze",
        json={"main_ticker": "SBER", "direction": "rate_hike", "horizons": [1]},
    )

    assert response.status_code == 200

    text = str(response.json()).lower()
    forbidden_words = [
        "точно",
        "гарантированно",
        "купить",
        "продать",
        "точно",
        "гарантированно",
        "купить",
        "продать",
    ]

    for word in forbidden_words:
        assert not _contains_forbidden_word(text, word)


def _contains_forbidden_word(text, word):
    pattern = rf"(?<![0-9A-Za-zА-Яа-яЁё_]){re.escape(word)}(?![0-9A-Za-zА-Яа-яЁё_])"

    return re.search(pattern, text, flags=re.IGNORECASE) is not None


class FakeMoexClient:
    calls = []

    def fetch_candles(self, secid, interval, from_date, till_date):
        self.calls.append(
            {
                "secid": secid,
                "interval": interval,
                "from_date": from_date,
                "till_date": till_date,
            }
        )

        if secid == "MOEX":
            return _benchmark_candles()

        return _stock_candles()


class BenchmarkFailingMoexClient(FakeMoexClient):
    def fetch_candles(self, secid, interval, from_date, till_date):
        if secid == "MOEX":
            raise MoexClientError("benchmark unavailable")

        return _stock_candles()


class MainFailingMoexClient(FakeMoexClient):
    def fetch_candles(self, secid, interval, from_date, till_date):
        raise MoexClientError("main ticker unavailable")


def _seed_decisions(SessionLocal):
    session = SessionLocal()

    try:
        create_key_rate_decision(
            session,
            _decision_data(date(2024, 7, 26), "rate_hike"),
        )
        create_key_rate_decision(
            session,
            _decision_data(date(2024, 8, 2), "rate_hike"),
        )
        create_key_rate_decision(
            session,
            _decision_data(date(2024, 8, 9), "rate_cut"),
        )
        create_key_rate_decision(
            session,
            _decision_data(date(2024, 8, 16), "rate_hike", is_official=False),
        )
        session.commit()
    finally:
        session.close()


def _seed_non_official_hike_decisions(SessionLocal):
    session = SessionLocal()

    try:
        create_key_rate_decision(
            session,
            _decision_data(date(2024, 7, 26), "rate_hike", is_official=False),
        )
        create_key_rate_decision(
            session,
            _decision_data(date(2024, 8, 2), "rate_hike", is_official=False),
        )
        create_key_rate_decision(
            session,
            _decision_data(date(2024, 8, 16), "rate_hike", is_official=False),
        )
        session.commit()
    finally:
        session.close()


def _decision_data(decision_date, direction, is_official=True):
    change_bps = 200 if direction == "rate_hike" else -100

    return {
        "decision_date": decision_date,
        "rate_before": Decimal("16.00"),
        "rate_after": Decimal("18.00"),
        "change_bps": change_bps,
        "direction": direction,
        "title": f"Decision {decision_date.isoformat()}",
        "description": "Official imported decision.",
        "is_scheduled": True,
        "is_official": is_official,
        "source_url": "https://www.cbr.ru/",
        "source_type": "official_curated",
        "source_note": "Test row for API tests.",
    }


def _stock_candles():
    return [
        _candle("2024-07-15", "95"),
        _candle("2024-07-25", "100"),
        _candle("2024-07-26", "101"),
        _candle("2024-07-29", "103"),
        _candle("2024-07-30", "105"),
        _candle("2024-07-31", "108"),
        _candle("2024-08-01", "110"),
        _candle("2024-08-02", "112"),
        _candle("2024-08-05", "114"),
        _candle("2024-08-06", "115"),
        _candle("2024-08-07", "116"),
        _candle("2024-08-08", "117"),
        _candle("2024-08-09", "118"),
        _candle("2024-08-12", "119"),
        _candle("2024-08-13", "120"),
        _candle("2024-08-14", "121"),
        _candle("2024-08-15", "122"),
        _candle("2024-08-16", "123"),
        _candle("2024-08-19", "124"),
        _candle("2024-08-20", "125"),
        _candle("2024-08-21", "126"),
        _candle("2024-08-22", "127"),
        _candle("2024-08-23", "128"),
        _candle("2024-08-26", "129"),
        _candle("2024-08-27", "130"),
        _candle("2024-08-28", "131"),
        _candle("2024-08-29", "132"),
        _candle("2024-08-30", "133"),
        _candle("2024-09-02", "134"),
        _candle("2024-09-03", "135"),
        _candle("2024-09-04", "136"),
        _candle("2024-09-05", "137"),
        _candle("2024-09-06", "138"),
        _candle("2024-09-09", "139"),
        _candle("2024-09-10", "140"),
        _candle("2024-09-11", "141"),
        _candle("2024-09-12", "142"),
        _candle("2024-09-13", "143"),
    ]


def _benchmark_candles():
    return [
        _candle("2024-07-15", "97"),
        _candle("2024-07-25", "100"),
        _candle("2024-07-26", "100"),
        _candle("2024-07-29", "101"),
        _candle("2024-07-30", "102"),
        _candle("2024-07-31", "103"),
        _candle("2024-08-01", "104"),
        _candle("2024-08-02", "105"),
        _candle("2024-08-05", "106"),
        _candle("2024-08-06", "107"),
        _candle("2024-08-07", "108"),
        _candle("2024-08-08", "109"),
        _candle("2024-08-09", "110"),
        _candle("2024-08-12", "111"),
        _candle("2024-08-13", "112"),
        _candle("2024-08-14", "113"),
        _candle("2024-08-15", "114"),
        _candle("2024-08-16", "115"),
        _candle("2024-08-19", "116"),
        _candle("2024-08-20", "117"),
    ]


def _candle(begin, close):
    close_value = Decimal(close)

    return {
        "begin": begin,
        "open": close_value,
        "high": close_value,
        "low": close_value,
        "close": close_value,
        "volume": Decimal("1000"),
    }
