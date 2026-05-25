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
