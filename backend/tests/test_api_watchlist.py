from datetime import UTC, datetime
from decimal import Decimal

from app.modules.watchlist import router as watchlist_router


def test_get_watchlist_returns_items(client, monkeypatch):
    created_at = datetime.now(UTC)

    monkeypatch.setattr(
        watchlist_router,
        "list_watchlist_items",
        lambda db: [
            {
                "id": 1,
                "secid": "SBER",
                "short_name": "Sber",
                "latest_price": Decimal("323.78"),
                "created_at": created_at,
            }
        ],
    )

    response = client.get("/api/v1/watchlist")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert data[0]["secid"] == "SBER"
    assert str(data[0]["latest_price"]) == "323.78"
    assert data[0]["created_at"]


def test_add_watchlist_item_returns_created_item(client, monkeypatch):
    created_at = datetime.now(UTC)

    def fake_add_ticker_to_watchlist(db, secid):
        return {
            "id": 1,
            "secid": secid.upper(),
            "short_name": "Sber",
            "latest_price": Decimal("323.78"),
            "created_at": created_at,
        }

    monkeypatch.setattr(
        watchlist_router,
        "add_ticker_to_watchlist",
        fake_add_ticker_to_watchlist,
    )

    response = client.post("/api/v1/watchlist/items", json={"secid": "SBER"})

    assert response.status_code == 200
    assert response.json()["secid"] == "SBER"


def test_add_watchlist_item_rejects_empty_secid(client):
    response = client.post("/api/v1/watchlist/items", json={"secid": ""})

    assert response.status_code == 422


def test_delete_watchlist_item_returns_delete_result(client, monkeypatch):
    monkeypatch.setattr(
        watchlist_router,
        "remove_ticker_from_watchlist",
        lambda db, secid: {"secid": secid.upper(), "deleted": True},
    )

    response = client.delete("/api/v1/watchlist/items/SBER")

    assert response.status_code == 200
    assert response.json() == {"secid": "SBER", "deleted": True}


def test_refresh_watchlist_prices_returns_batch_summary(client, monkeypatch):
    monkeypatch.setattr(
        watchlist_router,
        "refresh_watchlist_prices",
        lambda db: {
            "total": 2,
            "updated": 1,
            "failed": 1,
            "items": [
                {
                    "secid": "SBER",
                    "success": True,
                    "price": Decimal("323.78"),
                    "error": None,
                },
                {
                    "secid": "BROKEN",
                    "success": False,
                    "price": None,
                    "error": "MOEX unavailable",
                },
            ],
        },
    )

    response = client.post("/api/v1/watchlist/refresh-prices")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert data["updated"] == 1
    assert data["failed"] == 1
    assert data["items"][0]["secid"] == "SBER"
    assert data["items"][1]["success"] is False
