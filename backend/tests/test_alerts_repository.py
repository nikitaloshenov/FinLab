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
        ticker_id=ticker.id,
        condition="above",
        target_price=Decimal("300"),
        is_active=True,
    )
    db_session.add(alert)
    db_session.flush()

    event = AlertEvent(
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

    assert get_alert_by_id(db_session, alert.id) is None
    assert get_alerts(db_session) == []
    assert get_active_alerts(db_session) == []

    event_data = get_alert_events(db_session)

    assert len(event_data) == 1
    assert event_data[0]["alert_id"] == alert.id
    assert event_data[0]["secid"] == "SBER"
