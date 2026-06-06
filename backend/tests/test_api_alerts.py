from datetime import UTC, datetime
from decimal import Decimal

from app.modules.alerts import router as alerts_router
from app.modules.alerts.service import AlertLatestPriceNotFoundError, AlertNotFoundError


SESSION_ID = "11111111-1111-4111-8111-111111111111"
OTHER_SESSION_ID = "22222222-2222-4222-8222-222222222222"
SESSION_HEADERS = {"X-FinLab-Session-Id": SESSION_ID}
OTHER_SESSION_HEADERS = {"X-FinLab-Session-Id": OTHER_SESSION_ID}


def make_alert(alert_id=1):
    now = datetime.now(UTC)

    return {
        "id": alert_id,
        "secid": "SBER",
        "short_name": "Sber",
        "condition": "above",
        "target_price": Decimal("300"),
        "is_active": True,
        "triggered_at": None,
        "created_at": now,
        "updated_at": now,
    }


def test_get_alerts_returns_list(client, monkeypatch):
    monkeypatch.setattr(
        alerts_router,
        "list_alerts",
        lambda db, session_id: [make_alert()],
    )

    response = client.get("/api/v1/alerts", headers=SESSION_HEADERS)

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert data[0]["id"] == 1
    assert data[0]["secid"] == "SBER"


def test_get_alerts_does_not_return_deleted_alerts(client, monkeypatch):
    monkeypatch.setattr(
        alerts_router,
        "list_alerts",
        lambda db, session_id: [make_alert(alert_id=1)],
    )

    response = client.get("/api/v1/alerts", headers=SESSION_HEADERS)

    assert response.status_code == 200

    data = response.json()

    assert [alert["id"] for alert in data] == [1]
    assert all(alert["id"] != 2 for alert in data)


def test_create_alert_returns_created_alert(client, monkeypatch):
    def fake_create_price_alert(db, secid, condition, target_price, session_id):
        assert session_id == SESSION_ID
        alert = make_alert()
        alert["secid"] = secid.upper()
        alert["condition"] = condition
        alert["target_price"] = target_price
        return alert

    monkeypatch.setattr(
        alerts_router,
        "create_price_alert",
        fake_create_price_alert,
    )

    response = client.post(
        "/api/v1/alerts",
        json={"secid": "SBER", "condition": "above", "target_price": 300},
        headers=SESSION_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["secid"] == "SBER"
    assert data["condition"] == "above"


def test_create_alert_rejects_invalid_condition(client):
    response = client.post(
        "/api/v1/alerts",
        json={"secid": "SBER", "condition": "invalid", "target_price": 300},
        headers=SESSION_HEADERS,
    )

    assert response.status_code == 422


def test_create_alert_rejects_negative_target_price(client):
    response = client.post(
        "/api/v1/alerts",
        json={"secid": "SBER", "condition": "above", "target_price": -1},
        headers=SESSION_HEADERS,
    )

    assert response.status_code == 422


def test_check_alert_returns_check_result(client, monkeypatch):
    monkeypatch.setattr(
        alerts_router,
        "check_price_alert",
        lambda db, alert_id, session_id: {
            "alert_id": alert_id,
            "secid": "SBER",
            "condition": "above",
            "target_price": Decimal("300"),
            "current_price": Decimal("323.78"),
            "triggered": True,
            "is_active": False,
            "message": "triggered",
        },
    )

    response = client.post("/api/v1/alerts/1/check", headers=SESSION_HEADERS)

    assert response.status_code == 200

    data = response.json()

    assert data["alert_id"] == 1
    assert data["triggered"] is True
    assert str(data["current_price"]) == "323.78"


def test_check_alert_not_found_returns_api_error(client, monkeypatch):
    def fake_check_price_alert(db, alert_id, session_id):
        raise AlertNotFoundError(f"Alert {alert_id} not found")

    monkeypatch.setattr(alerts_router, "check_price_alert", fake_check_price_alert)

    response = client.post("/api/v1/alerts/999/check", headers=SESSION_HEADERS)

    assert response.status_code == 404

    detail = response.json()["detail"]

    assert detail["code"] == "alert_not_found"
    assert "999" in detail["message"]
    assert detail["details"] == {}


def test_check_alert_latest_price_not_found_returns_api_error(client, monkeypatch):
    def fake_check_price_alert(db, alert_id, session_id):
        raise AlertLatestPriceNotFoundError(f"Latest price for alert {alert_id} not found")

    monkeypatch.setattr(alerts_router, "check_price_alert", fake_check_price_alert)

    response = client.post("/api/v1/alerts/1/check", headers=SESSION_HEADERS)

    assert response.status_code == 404

    detail = response.json()["detail"]

    assert detail["code"] == "alert_latest_price_not_found"
    assert "Latest price" in detail["message"]
    assert detail["details"] == {}


def test_check_active_alerts_returns_batch_summary(client, monkeypatch):
    monkeypatch.setattr(
        alerts_router,
        "check_active_price_alerts",
        lambda db, session_id: {
            "total": 2,
            "checked": 1,
            "triggered": 1,
            "failed": 1,
            "items": [
                {
                    "alert_id": 1,
                    "secid": "SBER",
                    "condition": "above",
                    "target_price": Decimal("300"),
                    "current_price": Decimal("323.78"),
                    "triggered": True,
                    "is_active": False,
                    "success": True,
                    "message": "triggered",
                    "error": None,
                },
                {
                    "alert_id": 2,
                    "secid": None,
                    "condition": None,
                    "target_price": None,
                    "current_price": None,
                    "triggered": False,
                    "is_active": None,
                    "success": False,
                    "message": None,
                    "error": "Latest price not found",
                },
            ],
        },
    )

    response = client.post("/api/v1/alerts/check-active", headers=SESSION_HEADERS)

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert data["checked"] == 1
    assert data["triggered"] == 1
    assert data["failed"] == 1
    assert data["items"][1]["success"] is False


def test_check_active_alerts_does_not_include_deleted_alerts(client, monkeypatch):
    monkeypatch.setattr(
        alerts_router,
        "check_active_price_alerts",
        lambda db, session_id: {
            "total": 1,
            "checked": 1,
            "triggered": 0,
            "failed": 0,
            "items": [
                {
                    "alert_id": 1,
                    "secid": "SBER",
                    "condition": "above",
                    "target_price": Decimal("300"),
                    "current_price": Decimal("290"),
                    "triggered": False,
                    "is_active": True,
                    "success": True,
                    "message": "Alert condition is not met",
                    "error": None,
                }
            ],
        },
    )

    response = client.post("/api/v1/alerts/check-active", headers=SESSION_HEADERS)

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert [item["alert_id"] for item in data["items"]] == [1]
    assert all(item["alert_id"] != 2 for item in data["items"])


def test_delete_alert_returns_delete_result(client, monkeypatch):
    monkeypatch.setattr(
        alerts_router,
        "remove_price_alert",
        lambda db, alert_id, session_id: {"id": alert_id, "deleted": True},
    )

    response = client.delete("/api/v1/alerts/1", headers=SESSION_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"id": 1, "deleted": True}


def test_get_alert_events_returns_list(client, monkeypatch):
    created_at = datetime.now(UTC)

    monkeypatch.setattr(
        alerts_router,
        "list_alert_events",
        lambda db, session_id: [
            {
                "id": 1,
                "alert_id": 1,
                "secid": "SBER",
                "price": Decimal("323.78"),
                "target_price": Decimal("300"),
                "condition": "above",
                "message": "triggered",
                "created_at": created_at,
            }
        ],
    )

    response = client.get("/api/v1/alerts/events", headers=SESSION_HEADERS)

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert data[0]["alert_id"] == 1
    assert data[0]["secid"] == "SBER"


def test_alerts_require_session_header(client):
    response = client.get("/api/v1/alerts")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "demo_session_required"


def test_alerts_reject_invalid_session_header(client):
    response = client.get(
        "/api/v1/alerts",
        headers={"X-FinLab-Session-Id": "not-a-uuid"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "demo_session_invalid"


def test_alerts_session_id_is_forwarded_to_service(client, monkeypatch):
    seen_sessions = []

    def fake_list_alerts(db, session_id):
        seen_sessions.append(session_id)
        return []

    monkeypatch.setattr(alerts_router, "list_alerts", fake_list_alerts)

    client.get("/api/v1/alerts", headers=SESSION_HEADERS)
    client.get("/api/v1/alerts", headers=OTHER_SESSION_HEADERS)

    assert seen_sessions == [SESSION_ID, OTHER_SESSION_ID]
