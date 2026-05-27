from datetime import UTC, datetime
from decimal import Decimal

from app.modules.market import router as market_router
from app.modules.market.moex_client import MoexTickerNotFoundError


def test_get_market_ticker_from_moex_not_found_returns_api_error(client, monkeypatch):
    def fake_get_ticker_from_moex(secid):
        raise MoexTickerNotFoundError(f"Ticker {secid} not found on MOEX")

    monkeypatch.setattr(
        market_router,
        "get_ticker_from_moex",
        fake_get_ticker_from_moex,
    )

    response = client.get("/api/v1/market/tickers/SBER/moex")

    assert response.status_code == 404

    detail = response.json()["detail"]

    assert detail["code"] == "ticker_not_found"
    assert "SBER" in detail["message"]
    assert detail["details"] == {}


def test_get_market_ticker_candles_returns_points(client, monkeypatch):
    older = datetime(2026, 5, 25, tzinfo=UTC)
    newer = datetime(2026, 5, 26, tzinfo=UTC)

    def fake_get_ticker_candles(secid, interval, limit):
        assert secid == "SBER"
        assert interval == "1d"
        assert limit == 100

        return [
            {
                "begin": older,
                "open": Decimal("320"),
                "high": Decimal("325"),
                "low": Decimal("319"),
                "close": Decimal("323"),
                "volume": Decimal("123456"),
                "value": Decimal("12345678.90"),
            },
            {
                "begin": newer,
                "open": Decimal("323"),
                "high": Decimal("330"),
                "low": Decimal("322"),
                "close": Decimal("329"),
                "volume": Decimal("234567"),
                "value": Decimal("23456789.10"),
            },
        ]

    monkeypatch.setattr(
        market_router,
        "get_ticker_candles",
        fake_get_ticker_candles,
    )

    response = client.get("/api/v1/market/tickers/SBER/candles")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert Decimal(str(data[0]["close"])) == Decimal("323")
    assert Decimal(str(data[1]["volume"])) == Decimal("234567")


def test_get_market_ticker_candles_uses_interval_and_limit(client, monkeypatch):
    def fake_get_ticker_candles(secid, interval, limit):
        assert interval == "10m"
        assert limit == 25
        return []

    monkeypatch.setattr(
        market_router,
        "get_ticker_candles",
        fake_get_ticker_candles,
    )

    response = client.get(
        "/api/v1/market/tickers/SBER/candles?interval=10m&limit=25"
    )

    assert response.status_code == 200
    assert response.json() == []


def test_get_market_ticker_candles_rejects_invalid_query_params(client):
    invalid_interval_response = client.get(
        "/api/v1/market/tickers/SBER/candles?interval=5m"
    )
    low_limit_response = client.get(
        "/api/v1/market/tickers/SBER/candles?limit=0"
    )
    high_limit_response = client.get(
        "/api/v1/market/tickers/SBER/candles?limit=1000"
    )

    assert invalid_interval_response.status_code == 422
    assert low_limit_response.status_code == 422
    assert high_limit_response.status_code == 422


def test_get_market_ticker_candles_not_found_returns_api_error(client, monkeypatch):
    def fake_get_ticker_candles(secid, interval, limit):
        raise MoexTickerNotFoundError(f"Ticker {secid} not found on MOEX")

    monkeypatch.setattr(
        market_router,
        "get_ticker_candles",
        fake_get_ticker_candles,
    )

    response = client.get("/api/v1/market/tickers/SBER/candles")

    assert response.status_code == 404

    detail = response.json()["detail"]

    assert detail["code"] == "ticker_not_found"
    assert "SBER" in detail["message"]
    assert detail["details"] == {}
