from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.modules.events.models import Event, EventTarget, EventType, EventValue
from app.modules.events.service import import_key_rate_decisions_to_events
from app.modules.hypotheses.models import KeyRateDecision
from app.modules.reference.models import DataSource


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


def test_import_key_rate_events_creates_event_type(db_session):
    _seed_cbr_source(db_session)

    result = import_key_rate_decisions_to_events(db_session)

    event_type = db_session.scalar(select(EventType).where(EventType.code == "key_rate_decision"))

    assert result.legacy_decisions_total == 0
    assert result.event_type_id == event_type.id
    assert event_type.name == "Key rate decision"
    assert event_type.default_source_id is not None


def test_import_key_rate_events_imports_legacy_decisions(db_session):
    source = _seed_cbr_source(db_session)
    _seed_decision(
        db_session,
        decision_date=date(2024, 7, 26),
        rate_before=Decimal("16.00"),
        rate_after=Decimal("18.00"),
        change_bps=200,
        direction="rate_hike",
    )

    result = import_key_rate_decisions_to_events(db_session)

    event = db_session.scalar(select(Event))
    event_type = db_session.scalar(select(EventType).where(EventType.code == "key_rate_decision"))

    assert result.legacy_decisions_total == 1
    assert result.events_created == 1
    assert result.events_updated == 0
    assert event.event_type_id == event_type.id
    assert event.source_event_id == "key_rate_decision:2024-07-26"
    assert event.event_date == date(2024, 7, 26)
    assert event.title == "CBR key rate decision: 18%"
    assert event.direction == "hike"
    assert event.importance == "high"
    assert event.source_id == source.id


def test_import_key_rate_events_imports_event_values(db_session):
    _seed_cbr_source(db_session)
    _seed_decision(
        db_session,
        decision_date=date(2024, 6, 7),
        rate_before=Decimal("16.00"),
        rate_after=Decimal("16.00"),
        change_bps=None,
        direction="rate_hold",
    )

    result = import_key_rate_decisions_to_events(db_session)

    values = {
        value.key: value
        for value in db_session.scalars(select(EventValue).order_by(EventValue.key)).all()
    }

    assert result.event_values_upserted == 3
    assert values["key_rate"].numeric_value == Decimal("16.00000000")
    assert values["key_rate"].unit == "percent"
    assert values["previous_key_rate"].numeric_value == Decimal("16.00000000")
    assert values["previous_key_rate"].unit == "percent"
    assert values["change_bps"].numeric_value == Decimal("0E-8")
    assert values["change_bps"].unit == "bps"


def test_import_key_rate_events_creates_market_target(db_session):
    _seed_cbr_source(db_session)
    _seed_decision(db_session, decision_date=date(2024, 1, 1))

    result = import_key_rate_decisions_to_events(db_session)

    target = db_session.scalar(select(EventTarget))

    assert result.event_targets_created == 1
    assert target.target_type == "market"
    assert target.instrument_id is None
    assert target.issuer_id is None
    assert target.sector_id is None
    assert target.benchmark_id is None


def test_import_key_rate_events_is_idempotent(db_session):
    _seed_cbr_source(db_session)
    _seed_decision(db_session, decision_date=date(2024, 2, 16), change_bps=-100)

    first = import_key_rate_decisions_to_events(db_session)
    second = import_key_rate_decisions_to_events(db_session)

    assert first.events_created == 1
    assert second.events_created == 0
    assert second.events_updated == 1
    assert second.event_targets_created == 0
    assert second.event_targets_skipped == 1
    assert db_session.scalar(select(func.count()).select_from(EventType)) == 1
    assert db_session.scalar(select(func.count()).select_from(Event)) == 1
    assert db_session.scalar(select(func.count()).select_from(EventValue)) == 3
    assert db_session.scalar(select(func.count()).select_from(EventTarget)) == 1


def test_import_key_rate_events_calculates_directions(db_session):
    _seed_cbr_source(db_session)
    _seed_decision(
        db_session,
        decision_date=date(2024, 1, 1),
        rate_before=Decimal("16.00"),
        rate_after=Decimal("15.00"),
        direction="rate_cut",
    )
    _seed_decision(
        db_session,
        decision_date=date(2024, 2, 1),
        rate_before=Decimal("15.00"),
        rate_after=Decimal("17.00"),
        direction="rate_hike",
    )
    _seed_decision(
        db_session,
        decision_date=date(2024, 3, 1),
        rate_before=Decimal("17.00"),
        rate_after=Decimal("17.00"),
        direction="rate_hold",
    )

    import_key_rate_decisions_to_events(db_session)

    directions = [
        event.direction
        for event in db_session.scalars(select(Event).order_by(Event.event_date)).all()
    ]

    assert directions == ["cut", "hike", "hold"]


def test_import_key_rate_events_empty_legacy_table_is_graceful(db_session):
    result = import_key_rate_decisions_to_events(db_session)

    assert result.legacy_decisions_total == 0
    assert result.events_created == 0
    assert result.events_updated == 0
    assert result.event_values_upserted == 0
    assert result.event_targets_created == 0
    assert db_session.scalar(select(func.count()).select_from(Event)) == 0


def _seed_cbr_source(db_session):
    source = DataSource(
        code="cbr",
        name="Bank of Russia",
        source_type="cbr",
        url="https://www.cbr.ru",
    )
    db_session.add(source)
    db_session.commit()
    return source


def _seed_decision(
    db_session,
    *,
    decision_date: date,
    rate_before: Decimal = Decimal("16.00"),
    rate_after: Decimal = Decimal("15.00"),
    change_bps: int | None = None,
    direction: str = "rate_cut",
):
    decision = KeyRateDecision(
        decision_date=decision_date,
        rate_before=rate_before,
        rate_after=rate_after,
        change_bps=change_bps,
        direction=direction,
        title=f"Decision {decision_date.isoformat()}",
        is_scheduled=True,
        is_official=True,
    )
    db_session.add(decision)
    db_session.commit()
    return decision
