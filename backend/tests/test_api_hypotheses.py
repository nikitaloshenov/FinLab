from decimal import Decimal

from app.modules.hypotheses import router as hypotheses_router
from app.modules.hypotheses import service as hypotheses_service
from app.modules.hypotheses.blueprints import UnsupportedHypothesisBlueprintError
from app.modules.market.moex_client import MoexClientError


def test_post_hypothesis_analyze_returns_report_with_main_and_benchmark(
    client,
    monkeypatch,
):
    class FakeMoexClient:
        def fetch_candles(self, secid, interval, from_date, till_date):
            assert interval == "1d"
            assert from_date == "2026-04-25"
            assert till_date == "2026-06-04"

            if secid == "IMOEX":
                return _benchmark_candles()

            return _positive_candles()

    monkeypatch.setattr(hypotheses_service, "MoexClient", FakeMoexClient)

    response = client.post(
        "/api/v1/hypotheses/analyze",
        json=_valid_request(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["hypothesis"]["main_ticker"] == "SBER"
    assert data["hypothesis"]["benchmark_ticker"] == "IMOEX"
    assert data["historical_validation"]["main_ticker_result"]["secid"] == "SBER"
    assert data["historical_validation"]["benchmark_result"]["secid"] == "IMOEX"
    assert data["historical_validation"]["relative_result"]
    assert data["blueprint"]
    assert data["assessment"]
    assert data["metadata"]["is_prediction"] is False


def test_post_hypothesis_analyze_rejects_invalid_event_type(client):
    payload = {
        **_valid_request(),
        "event_type": "dividend",
    }

    response = client.post("/api/v1/hypotheses/analyze", json=payload)

    assert response.status_code == 422


def test_post_hypothesis_analyze_rejects_empty_main_ticker(client):
    payload = {
        **_valid_request(),
        "main_ticker": " ",
    }

    response = client.post("/api/v1/hypotheses/analyze", json=payload)

    assert response.status_code == 422


def test_post_hypothesis_analyze_rejects_old_tickers_field(client):
    payload = {
        **_valid_request(),
        "tickers": ["SBER", "VTBR"],
    }
    payload.pop("main_ticker")

    response = client.post("/api/v1/hypotheses/analyze", json=payload)

    assert response.status_code == 422


def test_post_hypothesis_analyze_ignores_same_benchmark_as_main(
    client,
    monkeypatch,
):
    class FakeMoexClient:
        def fetch_candles(self, secid, interval, from_date, till_date):
            return _positive_candles()

    monkeypatch.setattr(hypotheses_service, "MoexClient", FakeMoexClient)

    payload = {
        **_valid_request(),
        "benchmark_ticker": "sber",
    }

    response = client.post("/api/v1/hypotheses/analyze", json=payload)

    assert response.status_code == 200
    assert response.json()["hypothesis"]["benchmark_ticker"] is None
    assert response.json()["historical_validation"]["benchmark_result"] is None
    assert response.json()["historical_validation"]["relative_result"] is None


def test_post_hypothesis_analyze_unsupported_blueprint_returns_api_error(
    client,
    monkeypatch,
):
    def fake_analyze_hypothesis(request):
        raise UnsupportedHypothesisBlueprintError("Unsupported blueprint")

    monkeypatch.setattr(
        hypotheses_router,
        "analyze_hypothesis",
        fake_analyze_hypothesis,
    )

    response = client.post(
        "/api/v1/hypotheses/analyze",
        json=_valid_request(),
    )

    assert response.status_code == 400

    detail = response.json()["detail"]

    assert detail["code"] == "unsupported_hypothesis_blueprint"
    assert "Unsupported blueprint" in detail["message"]


def test_post_hypothesis_analyze_schema_rejects_unsupported_sector(client):
    payload = {
        **_valid_request(),
        "sector": "real_estate",
    }

    response = client.post("/api/v1/hypotheses/analyze", json=payload)

    assert response.status_code == 422


def test_post_hypothesis_analyze_benchmark_failure_does_not_fail_endpoint(
    client,
    monkeypatch,
):
    class FakeMoexClient:
        def fetch_candles(self, secid, interval, from_date, till_date):
            if secid == "IMOEX":
                raise MoexClientError("MOEX unavailable")

            return _positive_candles()

    monkeypatch.setattr(hypotheses_service, "MoexClient", FakeMoexClient)

    response = client.post(
        "/api/v1/hypotheses/analyze",
        json=_valid_request(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["historical_validation"]["main_ticker_result"]["status"] == "ok"
    assert data["historical_validation"]["benchmark_result"]["status"] == "failed"
    assert data["historical_validation"]["relative_result"] is None
    assert "Benchmark validation was unavailable." in data["limitations"]


def test_post_hypothesis_analyze_near_zero_main_return_is_not_supports(
    client,
    monkeypatch,
):
    class FakeMoexClient:
        def fetch_candles(self, secid, interval, from_date, till_date):
            if secid == "IMOEX":
                return _benchmark_candles()

            return _near_zero_candles()

    monkeypatch.setattr(hypotheses_service, "MoexClient", FakeMoexClient)

    response = client.post(
        "/api/v1/hypotheses/analyze",
        json=_valid_request(),
    )

    assert response.status_code == 200
    assert response.json()["assessment"]["overall_result"] == "mixed_support"


def test_post_hypothesis_analyze_negative_main_return_contradicts_positive(
    client,
    monkeypatch,
):
    class FakeMoexClient:
        def fetch_candles(self, secid, interval, from_date, till_date):
            if secid == "IMOEX":
                return _benchmark_candles()

            return _negative_candles()

    monkeypatch.setattr(hypotheses_service, "MoexClient", FakeMoexClient)

    response = client.post(
        "/api/v1/hypotheses/analyze",
        json=_valid_request(),
    )

    assert response.status_code == 200
    assert response.json()["assessment"]["overall_result"] == "contradicts"


def test_post_hypothesis_analyze_response_has_no_forbidden_wording(
    client,
    monkeypatch,
):
    class FakeMoexClient:
        def fetch_candles(self, secid, interval, from_date, till_date):
            if secid == "IMOEX":
                return _benchmark_candles()

            return _positive_candles()

    monkeypatch.setattr(hypotheses_service, "MoexClient", FakeMoexClient)

    response = client.post(
        "/api/v1/hypotheses/analyze",
        json=_valid_request(),
    )

    assert response.status_code == 200

    forbidden_words = [
        "точно",
        "гарантированно",
        "купить",
        "продать",
        "акция вырастет",
    ]
    generated_text = " ".join(_collect_strings(response.json())).lower()

    for word in forbidden_words:
        assert word not in generated_text


def _valid_request():
    return {
        "title": "Key rate cut and SBER",
        "user_hypothesis_text": "I expect rate cuts to support SBER.",
        "event_type": "key_rate",
        "event_direction": "rate_cut",
        "sector": "banks",
        "main_ticker": "SBER",
        "benchmark_ticker": "IMOEX",
        "event_date": "2026-05-15",
        "interval": "1d",
        "window_before_days": 20,
        "window_after_days": 20,
        "expected_direction": "positive",
    }


def _positive_candles():
    return [
        {
            "begin": "2026-05-14",
            "open": Decimal("99"),
            "high": Decimal("101"),
            "low": Decimal("98"),
            "close": Decimal("100"),
            "volume": Decimal("100000"),
        },
        {
            "begin": "2026-05-15",
            "open": Decimal("101"),
            "high": Decimal("106"),
            "low": Decimal("100"),
            "close": Decimal("105"),
            "volume": Decimal("120000"),
        },
        {
            "begin": "2026-05-18",
            "open": Decimal("105"),
            "high": Decimal("112"),
            "low": Decimal("104"),
            "close": Decimal("110"),
            "volume": Decimal("130000"),
        },
    ]


def _benchmark_candles():
    return [
        {
            "begin": "2026-05-14",
            "open": Decimal("100"),
            "high": Decimal("101"),
            "low": Decimal("99"),
            "close": Decimal("100"),
            "volume": Decimal("100000"),
        },
        {
            "begin": "2026-05-15",
            "open": Decimal("100"),
            "high": Decimal("106"),
            "low": Decimal("100"),
            "close": Decimal("105"),
            "volume": Decimal("120000"),
        },
        {
            "begin": "2026-05-18",
            "open": Decimal("105"),
            "high": Decimal("107"),
            "low": Decimal("104"),
            "close": Decimal("106"),
            "volume": Decimal("130000"),
        },
    ]


def _negative_candles():
    return [
        {
            "begin": "2026-05-14",
            "open": Decimal("100"),
            "high": Decimal("101"),
            "low": Decimal("99"),
            "close": Decimal("100"),
            "volume": Decimal("100000"),
        },
        {
            "begin": "2026-05-15",
            "open": Decimal("100"),
            "high": Decimal("101"),
            "low": Decimal("95"),
            "close": Decimal("98"),
            "volume": Decimal("120000"),
        },
        {
            "begin": "2026-05-18",
            "open": Decimal("98"),
            "high": Decimal("99"),
            "low": Decimal("90"),
            "close": Decimal("92"),
            "volume": Decimal("130000"),
        },
    ]


def _near_zero_candles():
    return [
        {
            "begin": "2026-05-14",
            "open": Decimal("100"),
            "high": Decimal("101"),
            "low": Decimal("99"),
            "close": Decimal("100"),
            "volume": Decimal("100000"),
        },
        {
            "begin": "2026-05-15",
            "open": Decimal("100"),
            "high": Decimal("101"),
            "low": Decimal("99"),
            "close": Decimal("100"),
            "volume": Decimal("120000"),
        },
        {
            "begin": "2026-05-18",
            "open": Decimal("100"),
            "high": Decimal("101"),
            "low": Decimal("99"),
            "close": Decimal("100.2"),
            "volume": Decimal("130000"),
        },
    ]


def _collect_strings(value):
    if isinstance(value, str):
        return [value]

    if isinstance(value, dict):
        strings = []
        for item in value.values():
            strings.extend(_collect_strings(item))
        return strings

    if isinstance(value, list):
        strings = []
        for item in value:
            strings.extend(_collect_strings(item))
        return strings

    return []

