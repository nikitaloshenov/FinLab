from datetime import datetime
from decimal import Decimal

from app.modules.market import service as market_service


def test_get_ticker_candles_sorts_oldest_to_newest_and_applies_limit(monkeypatch):
    class FakeMoexClient:
        def fetch_ticker(self, secid):
            return {"secid": secid}

        def fetch_candles(self, secid, interval, from_date, till_date):
            return [
                {
                    "begin": datetime(2026, 5, 27),
                    "open": Decimal("3"),
                    "high": Decimal("3"),
                    "low": Decimal("3"),
                    "close": Decimal("3"),
                    "volume": Decimal("3"),
                    "value": Decimal("3"),
                },
                {
                    "begin": datetime(2026, 5, 25),
                    "open": Decimal("1"),
                    "high": Decimal("1"),
                    "low": Decimal("1"),
                    "close": Decimal("1"),
                    "volume": Decimal("1"),
                    "value": Decimal("1"),
                },
                {
                    "begin": datetime(2026, 5, 26),
                    "open": Decimal("2"),
                    "high": Decimal("2"),
                    "low": Decimal("2"),
                    "close": Decimal("2"),
                    "volume": Decimal("2"),
                    "value": Decimal("2"),
                },
            ]

    monkeypatch.setattr(market_service, "MoexClient", FakeMoexClient)

    result = market_service.get_ticker_candles(
        secid="SBER",
        interval="1d",
        limit=2,
    )

    assert [candle["close"] for candle in result] == [
        Decimal("2"),
        Decimal("3"),
    ]
