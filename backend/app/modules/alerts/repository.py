from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.modules.alerts.models import Alert, AlertEvent
from app.modules.market.models import Ticker, TickerLatestPrice


def alert_to_dict(alert: Alert) -> dict[str, Any]:
    ticker = alert.ticker

    return {
        "id": alert.id,
        "secid": ticker.secid,
        "short_name": ticker.short_name,
        "condition": alert.condition,
        "target_price": alert.target_price,
        "is_active": alert.is_active,
        "triggered_at": alert.triggered_at,
        "created_at": alert.created_at,
        "updated_at": alert.updated_at,
    }


def alert_event_to_dict(event: AlertEvent) -> dict[str, Any]:
    ticker = event.ticker

    return {
        "id": event.id,
        "alert_id": event.alert_id,
        "secid": ticker.secid,
        "price": event.price,
        "target_price": event.target_price,
        "condition": event.condition,
        "message": event.message,
        "created_at": event.created_at,
    }


def get_alerts(db: Session) -> list[dict[str, Any]]:
    alerts = (
        db.query(Alert)
        .options(joinedload(Alert.ticker))
        .order_by(Alert.created_at.desc())
        .all()
    )

    return [alert_to_dict(alert) for alert in alerts]


def get_alert_by_id(
    db: Session,
    alert_id: int,
) -> Alert | None:
    return (
        db.query(Alert)
        .options(joinedload(Alert.ticker))
        .filter(Alert.id == alert_id)
        .first()
    )


def create_alert(
    db: Session,
    ticker: Ticker,
    condition: str,
    target_price: Decimal,
) -> Alert:
    alert = Alert(
        ticker_id=ticker.id,
        condition=condition,
        target_price=target_price,
        is_active=True,
    )

    db.add(alert)
    db.flush()

    return alert


def delete_alert(
    db: Session,
    alert: Alert,
) -> None:
    db.delete(alert)
    db.flush()


def disable_alert(
    db: Session,
    alert: Alert,
) -> Alert:
    alert.is_active = False
    db.flush()

    return alert


def get_latest_price_for_ticker(
    db: Session,
    ticker_id: int,
) -> TickerLatestPrice | None:
    return (
        db.query(TickerLatestPrice)
        .filter(TickerLatestPrice.ticker_id == ticker_id)
        .first()
    )


def create_alert_event(
    db: Session,
    alert: Alert,
    current_price: Decimal,
    message: str,
) -> AlertEvent:
    event = AlertEvent(
        alert_id=alert.id,
        ticker_id=alert.ticker_id,
        price=current_price,
        target_price=alert.target_price,
        condition=alert.condition,
        message=message,
    )

    db.add(event)
    db.flush()

    return event


def get_alert_events(db: Session) -> list[dict[str, Any]]:
    events = (
        db.query(AlertEvent)
        .options(joinedload(AlertEvent.ticker))
        .order_by(AlertEvent.created_at.desc())
        .all()
    )

    return [alert_event_to_dict(event) for event in events]