from datetime import UTC, datetime
from decimal import Decimal

from app.modules.watchlist import router as watchlist_router
from app.modules.watchlist.service import WatchlistItemNotFoundError


SESSION_ID = "11111111-1111-4111-8111-111111111111"
OTHER_SESSION_ID = "22222222-2222-4222-8222-222222222222"
SESSION_HEADERS = {"X-FinLab-Session-Id": SESSION_ID}
OTHER_SESSION_HEADERS = {"X-FinLab-Session-Id": OTHER_SESSION_ID}


def test_get_watchlist_returns_items(client, monkeypatch):
    created_at = datetime.now(UTC)

    monkeypatch.setattr(
        watchlist_router,
        "list_watchlist_items",
        lambda db, session_id: [
            {
                "id": 1,
                "secid": "SBER",
                "short_name": "Sber",
                "latest_price": Decimal("323.78"),
                "created_at": created_at,
            }
        ],
    )

    response = client.get("/api/v1/watchlist", headers=SESSION_HEADERS)

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert data[0]["secid"] == "SBER"
    assert str(data[0]["latest_price"]) == "323.78"
    assert data[0]["created_at"]


def test_add_watchlist_item_returns_created_item(client, monkeypatch):
    created_at = datetime.now(UTC)

    def fake_add_ticker_to_watchlist(db, secid, session_id):
        assert session_id == SESSION_ID
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

    response = client.post(
        "/api/v1/watchlist/items",
        json={"secid": "SBER"},
        headers=SESSION_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["secid"] == "SBER"


def test_add_watchlist_item_rejects_empty_secid(client):
    response = client.post(
        "/api/v1/watchlist/items",
        json={"secid": ""},
        headers=SESSION_HEADERS,
    )

    assert response.status_code == 422


def test_delete_watchlist_item_returns_delete_result(client, monkeypatch):
    monkeypatch.setattr(
        watchlist_router,
        "remove_ticker_from_watchlist",
        lambda db, secid, session_id: {"secid": secid.upper(), "deleted": True},
    )

    response = client.delete("/api/v1/watchlist/items/SBER", headers=SESSION_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"secid": "SBER", "deleted": True}


def test_delete_watchlist_item_not_found_returns_api_error(client, monkeypatch):
    def fake_remove_ticker_from_watchlist(db, secid, session_id):
        raise WatchlistItemNotFoundError(f"Ticker {secid} not found in watchlist")

    monkeypatch.setattr(
        watchlist_router,
        "remove_ticker_from_watchlist",
        fake_remove_ticker_from_watchlist,
    )

    response = client.delete("/api/v1/watchlist/items/SBER", headers=SESSION_HEADERS)

    assert response.status_code == 404

    detail = response.json()["detail"]

    assert detail["code"] == "watchlist_item_not_found"
    assert "SBER" in detail["message"]
    assert detail["details"] == {}


def test_refresh_watchlist_prices_returns_batch_summary(client, monkeypatch):
    monkeypatch.setattr(
        watchlist_router,
        "refresh_watchlist_prices",
        lambda db, session_id: {
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

    response = client.post("/api/v1/watchlist/refresh-prices", headers=SESSION_HEADERS)

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert data["updated"] == 1
    assert data["failed"] == 1
    assert data["items"][0]["secid"] == "SBER"
    assert data["items"][1]["success"] is False


def test_watchlist_requires_session_header(client):
    response = client.get("/api/v1/watchlist")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "demo_session_required"


def test_watchlist_rejects_invalid_session_header(client):
    response = client.get(
        "/api/v1/watchlist",
        headers={"X-FinLab-Session-Id": "not-a-uuid"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "demo_session_invalid"


def test_watchlist_session_id_is_forwarded_to_service(client, monkeypatch):
    seen_sessions = []

    def fake_list_watchlist_items(db, session_id):
        seen_sessions.append(session_id)
        return []

    monkeypatch.setattr(
        watchlist_router,
        "list_watchlist_items",
        fake_list_watchlist_items,
    )

    client.get("/api/v1/watchlist", headers=SESSION_HEADERS)
    client.get("/api/v1/watchlist", headers=OTHER_SESSION_HEADERS)

    assert seen_sessions == [SESSION_ID, OTHER_SESSION_ID]
