from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

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


def get_preferred_instrument_by_secid(db: Session, secid: str) -> Instrument | None:
    normalized_secid = secid.strip().upper()
    instruments = db.scalars(
        select(Instrument).where(func.upper(Instrument.secid) == normalized_secid),
    ).all()

    if not instruments:
        return None

    return sorted(
        instruments,
        key=lambda instrument: (
            not instrument.is_active,
            instrument.board != "TQBR",
            instrument.id,
        ),
    )[0]


def get_event_type_by_code(db: Session, code: str) -> EventType | None:
    return db.scalar(select(EventType).where(EventType.code == code))


def list_events_by_type(
    db: Session,
    *,
    event_type_id: int,
    date_from: date | None,
    date_to: date | None,
) -> list[Event]:
    query = select(Event).where(Event.event_type_id == event_type_id)

    if date_from is not None:
        query = query.where(Event.event_date >= date_from)
    if date_to is not None:
        query = query.where(Event.event_date <= date_to)

    return list(db.scalars(query.order_by(Event.event_date, Event.id)).all())


def list_price_candles(
    db: Session,
    *,
    instrument_id: int,
    interval: str = "1d",
) -> list[PriceCandle]:
    return list(
        db.scalars(
            select(PriceCandle)
            .where(
                PriceCandle.instrument_id == instrument_id,
                PriceCandle.interval == interval,
            )
            .order_by(PriceCandle.trading_date, PriceCandle.begin_at, PriceCandle.id),
        ).all(),
    )


def create_study_run(
    db: Session,
    *,
    event_type_id: int | None,
    target_instrument_id: int | None,
    params_json: dict[str, Any],
    status: str = "running",
) -> StudyRun:
    study_run = StudyRun(
        study_type="event_study",
        event_type_id=event_type_id,
        target_type="instrument",
        target_instrument_id=target_instrument_id,
        params_json=params_json,
        methodology_version="event_study_v1",
        data_cutoff_at=datetime.now(UTC),
        status=status,
    )
    db.add(study_run)
    db.flush()
    return study_run


def finish_study_run(
    db: Session,
    study_run: StudyRun,
    *,
    status: str,
    error_message: str | None = None,
) -> StudyRun:
    study_run.status = status
    study_run.completed_at = datetime.now(UTC)
    study_run.error_message = error_message
    db.flush()
    return study_run


def create_study_run_event(
    db: Session,
    *,
    study_run_id: int,
    event_id: int,
    status: str,
    skipped_reason: str | None,
) -> StudyRunEvent:
    run_event = StudyRunEvent(
        study_run_id=study_run_id,
        event_id=event_id,
        status=status,
        skipped_reason=skipped_reason,
    )
    db.add(run_event)
    db.flush()
    return run_event


def create_study_event_result(
    db: Session,
    *,
    study_run_id: int,
    event_id: int,
    instrument_id: int,
    horizon_trading_days: int,
    event_candle_id: int | None,
    horizon_candle_id: int | None,
    event_price: Decimal | None,
    horizon_price: Decimal | None,
    return_percent: Decimal | None,
    status: str,
    skipped_reason: str | None,
) -> StudyEventResult:
    result = StudyEventResult(
        study_run_id=study_run_id,
        event_id=event_id,
        instrument_id=instrument_id,
        horizon_trading_days=horizon_trading_days,
        event_candle_id=event_candle_id,
        horizon_candle_id=horizon_candle_id,
        event_price=event_price,
        horizon_price=horizon_price,
        return_percent=return_percent,
        status=status,
        skipped_reason=skipped_reason,
    )
    db.add(result)
    db.flush()
    return result


def create_study_horizon_summary(
    db: Session,
    *,
    study_run_id: int,
    instrument_id: int,
    horizon_trading_days: int,
    sample_size: int,
    skipped_count: int,
    positive_count: int,
    negative_count: int,
    neutral_count: int,
    average_return_percent: Decimal | None,
    median_return_percent: Decimal | None,
    hit_rate_percent: Decimal | None,
    best_horizon_flag: bool = False,
) -> StudyHorizonSummary:
    summary = StudyHorizonSummary(
        study_run_id=study_run_id,
        subject_type="instrument",
        instrument_id=instrument_id,
        horizon_trading_days=horizon_trading_days,
        sample_size=sample_size,
        skipped_count=skipped_count,
        positive_count=positive_count,
        negative_count=negative_count,
        neutral_count=neutral_count,
        average_return_percent=average_return_percent,
        median_return_percent=median_return_percent,
        hit_rate_percent=hit_rate_percent,
        average_relative_return_percent=None,
        median_relative_return_percent=None,
        best_horizon_flag=best_horizon_flag,
    )
    db.add(summary)
    db.flush()
    return summary


def create_study_skipped_event(
    db: Session,
    *,
    study_run_id: int,
    event_id: int | None,
    reason_code: str,
    reason_detail: str | None,
    context_json: dict[str, Any] | None = None,
) -> StudySkippedEvent:
    skipped_event = StudySkippedEvent(
        study_run_id=study_run_id,
        event_id=event_id,
        reason_code=reason_code,
        reason_detail=reason_detail,
        context_json=context_json,
    )
    db.add(skipped_event)
    db.flush()
    return skipped_event
