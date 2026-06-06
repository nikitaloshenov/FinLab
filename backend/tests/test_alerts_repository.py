from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.modules.alerts.models import Alert, AlertEvent
from app.modules.alerts.repository import (
    delete_alert,
    get_active_alerts,
    get_alert_by_id,
    get_alert_events,
    get_alerts,
)
from app.modules.market.models import Ticker


SESSION_ID = "11111111-1111-4111-8111-111111111111"
OTHER_SESSION_ID = "22222222-2222-4222-8222-222222222222"


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_delete_alert_soft_deletes_alert_and_preserves_events(db_session):
    ticker = Ticker(
        secid="SBER",
        short_name="Sber",
        board="TQBR",
        market="shares",
        engine="stock",
    )
    db_session.add(ticker)
    db_session.flush()

    alert = Alert(
        session_id=SESSION_ID,
        ticker_id=ticker.id,
        condition="above",
        target_price=Decimal("300"),
        is_active=True,
    )
    db_session.add(alert)
    db_session.flush()

    event = AlertEvent(
        session_id=SESSION_ID,
        alert_id=alert.id,
        ticker_id=ticker.id,
        price=Decimal("323.78"),
        target_price=Decimal("300"),
        condition="above",
        message="triggered",
        created_at=datetime.now(UTC),
    )
    db_session.add(event)
    db_session.commit()

    delete_alert(db_session, alert)
    db_session.commit()

    deleted_alert = db_session.get(Alert, alert.id)
    events = db_session.query(AlertEvent).all()

    assert deleted_alert is not None
    assert deleted_alert.is_deleted is True
    assert deleted_alert.is_active is False
    assert deleted_alert.deleted_at is not None
    assert len(events) == 1
    assert events[0].alert_id == alert.id

    assert get_alert_by_id(db_session, alert.id, session_id=SESSION_ID) is None
    assert get_alerts(db_session, session_id=SESSION_ID) == []
    assert get_active_alerts(db_session, session_id=SESSION_ID) == []

    event_data = get_alert_events(db_session, session_id=SESSION_ID)

    assert len(event_data) == 1
    assert event_data[0]["alert_id"] == alert.id
    assert event_data[0]["secid"] == "SBER"


def test_alerts_and_events_are_session_scoped(db_session):
    ticker = Ticker(
        secid="SBER",
        short_name="Sber",
        board="TQBR",
        market="shares",
        engine="stock",
    )
    db_session.add(ticker)
    db_session.flush()

    alert_a = Alert(
        session_id=SESSION_ID,
        ticker_id=ticker.id,
        condition="above",
        target_price=Decimal("300"),
        is_active=True,
    )
    alert_b = Alert(
        session_id=OTHER_SESSION_ID,
        ticker_id=ticker.id,
        condition="above",
        target_price=Decimal("300"),
        is_active=True,
    )
    db_session.add_all([alert_a, alert_b])
    db_session.flush()

    db_session.add_all(
        [
            AlertEvent(
                session_id=SESSION_ID,
                alert_id=alert_a.id,
                ticker_id=ticker.id,
                price=Decimal("323.78"),
                target_price=Decimal("300"),
                condition="above",
                message="triggered a",
                created_at=datetime.now(UTC),
            ),
            AlertEvent(
                session_id=OTHER_SESSION_ID,
                alert_id=alert_b.id,
                ticker_id=ticker.id,
                price=Decimal("323.78"),
                target_price=Decimal("300"),
                condition="above",
                message="triggered b",
                created_at=datetime.now(UTC),
            ),
        ]
    )
    db_session.commit()

    session_alerts = get_alerts(db_session, session_id=SESSION_ID)
    other_alerts = get_alerts(db_session, session_id=OTHER_SESSION_ID)
    session_events = get_alert_events(db_session, session_id=SESSION_ID)

    assert [alert["id"] for alert in session_alerts] == [alert_a.id]
    assert [alert["id"] for alert in other_alerts] == [alert_b.id]
    assert get_alert_by_id(
        db_session,
        alert_b.id,
        session_id=SESSION_ID,
    ) is None
    assert [event["alert_id"] for event in session_events] == [alert_a.id]
