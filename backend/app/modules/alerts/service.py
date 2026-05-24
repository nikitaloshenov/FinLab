from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.modules.alerts.repository import (
    alert_to_dict,
    create_alert,
    create_alert_event,
    delete_alert,
    disable_alert,
    get_alert_by_id,
    get_alert_events,
    get_alerts,
    get_latest_price_for_ticker,
)
from app.modules.market.repository import get_ticker_by_secid
from app.modules.market.service import refresh_ticker_price


class AlertNotFoundError(Exception):
    pass


class AlertTickerCreateError(Exception):
    pass


class AlertLatestPriceNotFoundError(Exception):
    pass


def list_alerts(db: Session) -> list[dict[str, Any]]:
    return get_alerts(db)


def list_alert_events(db: Session) -> list[dict[str, Any]]:
    return get_alert_events(db)


def create_price_alert(
    db: Session,
    secid: str,
    condition: str,
    target_price: Decimal,
) -> dict[str, Any]:
    normalized_secid = secid.upper().strip()

    ticker = get_ticker_by_secid(db, normalized_secid)

    if ticker is None:
        refresh_ticker_price(db, normalized_secid)
        ticker = get_ticker_by_secid(db, normalized_secid)

    if ticker is None:
        raise AlertTickerCreateError(
            f"Ticker {normalized_secid} was not created"
        )

    alert = create_alert(
        db=db,
        ticker=ticker,
        condition=condition,
        target_price=target_price,
    )

    db.commit()

    created_alert = get_alert_by_id(db, alert.id)

    if created_alert is None:
        raise AlertTickerCreateError(
            f"Alert for ticker {normalized_secid} was not created"
        )

    return alert_to_dict(created_alert)


def remove_price_alert(
    db: Session,
    alert_id: int,
) -> dict[str, Any]:
    alert = get_alert_by_id(db, alert_id)

    if alert is None:
        raise AlertNotFoundError(
            f"Alert {alert_id} not found"
        )

    delete_alert(
        db=db,
        alert=alert,
    )

    db.commit()

    return {
        "id": alert_id,
        "deleted": True,
    }


def disable_price_alert(
    db: Session,
    alert_id: int,
) -> dict[str, Any]:
    alert = get_alert_by_id(db, alert_id)

    if alert is None:
        raise AlertNotFoundError(
            f"Alert {alert_id} not found"
        )

    disable_alert(
        db=db,
        alert=alert,
    )

    db.commit()

    return {
        "id": alert_id,
        "is_active": False,
    }


def check_price_alert(
    db: Session,
    alert_id: int,
) -> dict[str, Any]:
    alert = get_alert_by_id(db, alert_id)

    if alert is None:
        raise AlertNotFoundError(
            f"Alert {alert_id} not found"
        )

    latest_price = get_latest_price_for_ticker(
        db=db,
        ticker_id=alert.ticker_id,
    )

    if latest_price is None:
        raise AlertLatestPriceNotFoundError(
            f"Latest price for alert {alert_id} not found"
        )

    current_price = latest_price.price

    if not alert.is_active:
        return {
            "alert_id": alert.id,
            "secid": alert.ticker.secid,
            "condition": alert.condition,
            "target_price": alert.target_price,
            "current_price": current_price,
            "triggered": False,
            "is_active": False,
            "message": "Alert is inactive",
        }

    triggered = is_alert_triggered(
        condition=alert.condition,
        current_price=current_price,
        target_price=alert.target_price,
    )

    if not triggered:
        return {
            "alert_id": alert.id,
            "secid": alert.ticker.secid,
            "condition": alert.condition,
            "target_price": alert.target_price,
            "current_price": current_price,
            "triggered": False,
            "is_active": True,
            "message": "Alert condition is not met",
        }

    message = build_alert_message(
        secid=alert.ticker.secid,
        condition=alert.condition,
        current_price=current_price,
        target_price=alert.target_price,
    )

    create_alert_event(
        db=db,
        alert=alert,
        current_price=current_price,
        message=message,
    )

    alert.is_active = False
    alert.triggered_at = datetime.now(UTC)

    db.commit()

    return {
        "alert_id": alert.id,
        "secid": alert.ticker.secid,
        "condition": alert.condition,
        "target_price": alert.target_price,
        "current_price": current_price,
        "triggered": True,
        "is_active": False,
        "message": message,
    }


def is_alert_triggered(
    condition: str,
    current_price: Decimal,
    target_price: Decimal,
) -> bool:
    if condition == "above":
        return current_price >= target_price

    if condition == "below":
        return current_price <= target_price

    return False


def build_alert_message(
    secid: str,
    condition: str,
    current_price: Decimal,
    target_price: Decimal,
) -> str:
    if condition == "above":
        return (
            f"{secid} reached alert condition: "
            f"current price {current_price} is above or equal to {target_price}"
        )

    return (
        f"{secid} reached alert condition: "
        f"current price {current_price} is below or equal to {target_price}"
    )