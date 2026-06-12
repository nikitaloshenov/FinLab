from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.modules.events.models import Event, EventType
from app.modules.market_data.models import PriceCandle
from app.modules.reference.models import Instrument
from app.modules.studies.models import (
    StudyEventResult,
    StudyHorizonSummary,
    StudyRun,
    StudyRunEvent,
    StudySkippedEvent,
)
from app.modules.studies.service import (
    EventStudyUnknownEventTypeError,
    EventStudyUnknownInstrumentError,
    run_event_study,
)


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


def test_event_study_unknown_instrument_handled_clearly(db_session):
    _seed_event_type(db_session)

    with pytest.raises(EventStudyUnknownInstrumentError):
        run_event_study(db_session, secid="UNKNOWN", event_type_code="key_rate_decision")


def test_event_study_unknown_event_type_handled_clearly(db_session):
    _seed_instrument(db_session)

    with pytest.raises(EventStudyUnknownEventTypeError):
        run_event_study(db_session, secid="SBER", event_type_code="unknown")


def test_event_study_no_events_found_is_recorded(db_session):
    _seed_instrument(db_session)
    _seed_event_type(db_session)

    result = run_event_study(db_session, secid="SBER", event_type_code="key_rate_decision")

    skipped = db_session.scalar(select(StudySkippedEvent))
    study_run = db_session.get(StudyRun, result.study_run_id)

    assert result.events_total == 0
    assert result.events_processed == 0
    assert result.events_skipped == 0
    assert result.summary_rows_created == 4
    assert study_run.status == "success"
    assert skipped.reason_code == "no_events_found"


def test_event_study_selects_first_candle_on_or_after_event_date(db_session):
    instrument = _seed_instrument(db_session)
    event_type = _seed_event_type(db_session)
    event = _seed_event(db_session, event_type, event_date=date(2024, 1, 6))
    _seed_candle(db_session, instrument, trading_date=date(2024, 1, 5), close=Decimal("90"))
    event_candle = _seed_candle(
        db_session,
        instrument,
        trading_date=date(2024, 1, 8),
        close=Decimal("100"),
    )
    horizon_candle = _seed_candle(
        db_session,
        instrument,
        trading_date=date(2024, 1, 9),
        close=Decimal("110"),
    )

    run_event_study(
        db_session,
        secid="SBER",
        event_type_code="key_rate_decision",
        horizons=[1],
    )

    saved_result = db_session.scalar(select(StudyEventResult))

    assert saved_result.event_id == event.id
    assert saved_result.event_candle_id == event_candle.id
    assert saved_result.horizon_candle_id == horizon_candle.id
    assert saved_result.event_price == Decimal("100.000000")
    assert saved_result.horizon_price == Decimal("110.000000")
    assert saved_result.return_percent == Decimal("10.000000")


def test_event_study_horizon_uses_trading_day_offset(db_session):
    instrument = _seed_instrument(db_session)
    event_type = _seed_event_type(db_session)
    _seed_event(db_session, event_type, event_date=date(2024, 1, 3))
    _seed_candle(db_session, instrument, trading_date=date(2024, 1, 3), close=Decimal("100"))
    _seed_candle(db_session, instrument, trading_date=date(2024, 1, 5), close=Decimal("110"))
    expected_horizon = _seed_candle(
        db_session,
        instrument,
        trading_date=date(2024, 1, 8),
        close=Decimal("130"),
    )

    run_event_study(
        db_session,
        secid="SBER",
        event_type_code="key_rate_decision",
        horizons=[2],
    )

    saved_result = db_session.scalar(select(StudyEventResult))

    assert saved_result.horizon_candle_id == expected_horizon.id
    assert saved_result.return_percent == Decimal("30.000000")


def test_event_study_skips_missing_event_candle(db_session):
    instrument = _seed_instrument(db_session)
    event_type = _seed_event_type(db_session)
    _seed_event(db_session, event_type, event_date=date(2025, 1, 1))
    _seed_candle(db_session, instrument, trading_date=date(2024, 1, 3), close=Decimal("100"))

    result = run_event_study(
        db_session,
        secid="SBER",
        event_type_code="key_rate_decision",
        horizons=[1, 5],
    )

    results = db_session.scalars(select(StudyEventResult).order_by(StudyEventResult.horizon_trading_days)).all()
    run_event = db_session.scalar(select(StudyRunEvent))
    skipped = db_session.scalar(select(StudySkippedEvent).where(StudySkippedEvent.event_id.is_not(None)))

    assert result.events_skipped == 1
    assert run_event.status == "skipped"
    assert run_event.skipped_reason == "no_event_candle"
    assert [item.status for item in results] == ["skipped", "skipped"]
    assert [item.skipped_reason for item in results] == ["no_event_candle", "no_event_candle"]
    assert skipped.reason_code == "no_event_candle"


def test_event_study_skips_missing_horizon_candle(db_session):
    instrument = _seed_instrument(db_session)
    event_type = _seed_event_type(db_session)
    _seed_event(db_session, event_type, event_date=date(2024, 1, 3))
    _seed_candle(db_session, instrument, trading_date=date(2024, 1, 3), close=Decimal("100"))
    _seed_candle(db_session, instrument, trading_date=date(2024, 1, 4), close=Decimal("105"))

    result = run_event_study(
        db_session,
        secid="SBER",
        event_type_code="key_rate_decision",
        horizons=[1, 5],
    )

    results = {
        item.horizon_trading_days: item
        for item in db_session.scalars(select(StudyEventResult)).all()
    }

    assert result.events_processed == 1
    assert results[1].status == "success"
    assert results[5].status == "skipped"
    assert results[5].skipped_reason == "no_horizon_candles"


def test_event_study_skips_invalid_event_price(db_session):
    instrument = _seed_instrument(db_session)
    event_type = _seed_event_type(db_session)
    _seed_event(db_session, event_type, event_date=date(2024, 1, 3))
    _seed_candle(db_session, instrument, trading_date=date(2024, 1, 3), close=Decimal("0"))
    _seed_candle(db_session, instrument, trading_date=date(2024, 1, 4), close=Decimal("105"))

    run_event_study(
        db_session,
        secid="SBER",
        event_type_code="key_rate_decision",
        horizons=[1],
    )

    saved_result = db_session.scalar(select(StudyEventResult))
    skipped = db_session.scalar(select(StudySkippedEvent))

    assert saved_result.status == "skipped"
    assert saved_result.skipped_reason == "invalid_event_price"
    assert skipped.reason_code == "invalid_event_price"


def test_event_study_creates_summary_from_successful_results_only(db_session):
    instrument = _seed_instrument(db_session)
    event_type = _seed_event_type(db_session)
    _seed_event(db_session, event_type, event_date=date(2024, 1, 3))
    _seed_event(db_session, event_type, event_date=date(2024, 1, 5))
    _seed_candle(db_session, instrument, trading_date=date(2024, 1, 3), close=Decimal("100"))
    _seed_candle(db_session, instrument, trading_date=date(2024, 1, 4), close=Decimal("110"))
    _seed_candle(db_session, instrument, trading_date=date(2024, 1, 5), close=Decimal("200"))
    _seed_candle(db_session, instrument, trading_date=date(2024, 1, 8), close=Decimal("180"))

    result = run_event_study(
        db_session,
        secid="SBER",
        event_type_code="key_rate_decision",
        horizons=[1, 10],
    )

    summaries = {
        item.horizon_trading_days: item
        for item in db_session.scalars(select(StudyHorizonSummary)).all()
    }

    assert result.results_created == 4
    assert result.summary_rows_created == 2
    assert summaries[1].sample_size == 2
    assert summaries[1].skipped_count == 0
    assert summaries[1].positive_count == 1
    assert summaries[1].negative_count == 1
    assert summaries[1].average_return_percent == Decimal("0.000000")
    assert summaries[10].sample_size == 0
    assert summaries[10].skipped_count == 2
    assert summaries[10].average_return_percent is None


def test_event_study_dry_run_rolls_back(db_session):
    instrument = _seed_instrument(db_session)
    event_type = _seed_event_type(db_session)
    _seed_event(db_session, event_type, event_date=date(2024, 1, 3))
    _seed_candle(db_session, instrument, trading_date=date(2024, 1, 3), close=Decimal("100"))
    _seed_candle(db_session, instrument, trading_date=date(2024, 1, 4), close=Decimal("105"))

    result = run_event_study(
        db_session,
        secid="SBER",
        event_type_code="key_rate_decision",
        horizons=[1],
        dry_run=True,
    )

    assert result.status == "dry_run"
    assert db_session.scalar(select(StudyRun)) is None
    assert db_session.scalar(select(StudyEventResult)) is None


def _seed_instrument(db_session):
    instrument = Instrument(
        secid="SBER",
        name="Sberbank",
        short_name="Sberbank",
        asset_type="share",
        board="TQBR",
        market="shares",
        engine="stock",
        currency="RUB",
        is_active=True,
    )
    db_session.add(instrument)
    db_session.commit()
    return instrument


def _seed_event_type(db_session):
    event_type = EventType(
        code="key_rate_decision",
        name="Key rate decision",
        description="Bank of Russia key rate decision event.",
        is_active=True,
    )
    db_session.add(event_type)
    db_session.commit()
    return event_type


def _seed_event(db_session, event_type, *, event_date: date):
    event = Event(
        event_type_id=event_type.id,
        source_event_id=f"event:{event_date.isoformat()}",
        event_date=event_date,
        title=f"Event {event_date.isoformat()}",
        direction="hold",
        importance="high",
    )
    db_session.add(event)
    db_session.commit()
    return event


def _seed_candle(db_session, instrument, *, trading_date: date, close: Decimal | None):
    candle = PriceCandle(
        instrument_id=instrument.id,
        interval="1d",
        begin_at=datetime.combine(trading_date, datetime.min.time(), tzinfo=UTC),
        trading_date=trading_date,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=Decimal("1000"),
        value=Decimal("100000"),
    )
    db_session.add(candle)
    db_session.commit()
    return candle
