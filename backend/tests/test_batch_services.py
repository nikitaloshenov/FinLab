from decimal import Decimal
from types import SimpleNamespace

from app.modules.alerts import service as alerts_service
from app.modules.alerts.service import AlertLatestPriceNotFoundError
from app.modules.market.moex_client import MoexClientError
from app.modules.watchlist import service as watchlist_service


SESSION_ID = "11111111-1111-4111-8111-111111111111"


class FakeDb:
    def __init__(self):
        self.rollbacks = 0

    def rollback(self):
        self.rollbacks += 1


def test_refresh_watchlist_prices_continues_after_failed_ticker(monkeypatch):
    db = FakeDb()

    monkeypatch.setattr(
        watchlist_service,
        "get_watchlist_items",
        lambda db, session_id: [{"secid": "SBER"}, {"secid": "BROKEN"}],
    )

    def fake_refresh_ticker_price(db, secid):
        if secid == "BROKEN":
            raise MoexClientError("MOEX unavailable")

        return {"price": Decimal("123.45")}

    monkeypatch.setattr(
        watchlist_service,
        "refresh_ticker_price",
        fake_refresh_ticker_price,
    )

    result = watchlist_service.refresh_watchlist_prices(db, session_id=SESSION_ID)

    assert result["total"] == 2
    assert result["updated"] == 1
    assert result["failed"] == 1
    assert result["items"][0]["success"] is True
    assert result["items"][1]["success"] is False
    assert result["items"][1]["secid"] == "BROKEN"
    assert db.rollbacks == 1


def test_check_active_price_alerts_continues_after_failed_alert(monkeypatch):
    db = FakeDb()

    monkeypatch.setattr(
        alerts_service,
        "get_active_alerts",
        lambda db, session_id: [SimpleNamespace(id=1), SimpleNamespace(id=2)],
    )

    def fake_check_price_alert(db, alert_id, session_id):
        if alert_id == 2:
            raise AlertLatestPriceNotFoundError("Latest price not found")

        return {
            "alert_id": alert_id,
            "secid": "SBER",
            "condition": "above",
            "target_price": Decimal("100"),
            "current_price": Decimal("110"),
            "triggered": True,
            "is_active": False,
            "message": "triggered",
        }

    monkeypatch.setattr(alerts_service, "check_price_alert", fake_check_price_alert)

    result = alerts_service.check_active_price_alerts(db, session_id=SESSION_ID)

    assert result["total"] == 2
    assert result["checked"] == 1
    assert result["triggered"] == 1
    assert result["failed"] == 1
    assert result["items"][0]["success"] is True
    assert result["items"][1]["success"] is False
    assert result["items"][1]["alert_id"] == 2
    assert db.rollbacks == 1
