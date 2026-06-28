from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from statistics import median

from sqlalchemy.orm import Session

from app.modules.events.models import Event
from app.modules.market_data.models import PriceCandle
from app.modules.studies.repository import (
    create_study_event_result,
    create_study_horizon_summary,
    create_study_run,
    create_study_run_event,
    create_study_skipped_event,
    finish_study_run,
    get_event_type_by_code,
    get_preferred_instrument_by_secid,
    list_events_by_type,
    list_price_candles,
)


DEFAULT_EVENT_STUDY_HORIZONS = [1, 5, 10, 20]
EVENT_STUDY_METHODOLOGY_VERSION = "event_study_v1"
PERCENT_QUANT = Decimal("0.000001")


class EventStudyError(Exception):
    pass


class EventStudyUnknownInstrumentError(EventStudyError):
    pass


class EventStudyUnknownEventTypeError(EventStudyError):
    pass


@dataclass
class HorizonSummaryResult:
    horizon_trading_days: int
    sample_size: int
    skipped_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    average_return_percent: Decimal | None
    median_return_percent: Decimal | None
    hit_rate_percent: Decimal | None
    best_horizon_flag: bool = False


@dataclass
class EventStudyRunResult:
    study_run_id: int | None
    secid: str
    event_type: str
    horizons: list[int]
    events_total: int
    events_processed: int
    events_skipped: int
    results_created: int
    summary_rows_created: int
    status: str
    summary: list[HorizonSummaryResult] = field(default_factory=list)


@dataclass
class _EventProcessingResult:
    event_id: int
    event_status: str
    skipped_reason: str | None
    results_created: int


def run_event_study(
    db: Session,
    *,
    secid: str,
    event_type_code: str,
    horizons: list[int] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    event_direction: str | None = None,
    dry_run: bool = False,
) -> EventStudyRunResult:
    normalized_horizons = _normalize_horizons(horizons or DEFAULT_EVENT_STUDY_HORIZONS)
    instrument = get_preferred_instrument_by_secid(db, secid)
    if instrument is None:
        raise EventStudyUnknownInstrumentError(f"Unknown instrument: {secid.strip().upper()}")

    event_type = get_event_type_by_code(db, event_type_code)
    if event_type is None:
        raise EventStudyUnknownEventTypeError(f"Unknown event type: {event_type_code}")

    params_json = {
        "secid": instrument.secid,
        "event_type": event_type.code,
        "horizons": normalized_horizons,
        "from": date_from.isoformat() if date_from is not None else None,
        "to": date_to.isoformat() if date_to is not None else None,
        "event_direction": event_direction,
        "interval": "1d",
    }
    study_run = create_study_run(
        db,
        event_type_id=event_type.id,
        target_instrument_id=instrument.id,
        params_json=params_json,
    )

    try:
        events = list_events_by_type(
            db,
            event_type_id=event_type.id,
            date_from=date_from,
            date_to=date_to,
            direction=event_direction,
        )
        candles = list_price_candles(db, instrument_id=instrument.id, interval="1d")

        if not events:
            create_study_skipped_event(
                db,
                study_run_id=study_run.id,
                event_id=None,
                reason_code="no_events_found",
                reason_detail="No events found for the selected event type/date range.",
                context_json={"event_type": event_type.code},
            )

        processing_results: list[_EventProcessingResult] = []
        for event in events:
            processing_results.append(
                _process_event(
                    db,
                    study_run_id=study_run.id,
                    event=event,
                    instrument_id=instrument.id,
                    candles=candles,
                    horizons=normalized_horizons,
                ),
            )

        summary = _create_horizon_summaries(
            db,
            study_run_id=study_run.id,
            instrument_id=instrument.id,
            horizons=normalized_horizons,
            event_results_count=len(events),
        )
        finish_study_run(db, study_run, status="success")

        result = EventStudyRunResult(
            study_run_id=study_run.id,
            secid=instrument.secid,
            event_type=event_type.code,
            horizons=normalized_horizons,
            events_total=len(events),
            events_processed=sum(1 for item in processing_results if item.event_status == "success"),
            events_skipped=sum(1 for item in processing_results if item.event_status == "skipped"),
            results_created=sum(item.results_created for item in processing_results),
            summary_rows_created=len(summary),
            status="dry_run" if dry_run else study_run.status,
            summary=summary,
        )

        if dry_run:
            db.rollback()
        else:
            db.commit()

        return result
    except Exception:
        db.rollback()
        study_run = db.merge(study_run)
        finish_study_run(db, study_run, status="failed", error_message="Event study failed.")
        db.commit()
        raise


def _process_event(
    db: Session,
    *,
    study_run_id: int,
    event: Event,
    instrument_id: int,
    candles: list[PriceCandle],
    horizons: list[int],
) -> _EventProcessingResult:
    event_index, event_candle = _find_event_candle(candles, event.event_date)
    results_created = 0

    if event_candle is None:
        for horizon in horizons:
            create_study_event_result(
                db,
                study_run_id=study_run_id,
                event_id=event.id,
                instrument_id=instrument_id,
                horizon_trading_days=horizon,
                event_candle_id=None,
                horizon_candle_id=None,
                event_price=None,
                horizon_price=None,
                return_percent=None,
                status="skipped",
                skipped_reason="no_event_candle",
            )
            results_created += 1
        create_study_run_event(
            db,
            study_run_id=study_run_id,
            event_id=event.id,
            status="skipped",
            skipped_reason="no_event_candle",
        )
        create_study_skipped_event(
            db,
            study_run_id=study_run_id,
            event_id=event.id,
            reason_code="no_event_candle",
            reason_detail="No daily candle found on or after event date.",
            context_json={"event_date": event.event_date.isoformat()},
        )
        return _EventProcessingResult(event.id, "skipped", "no_event_candle", results_created)

    if event_candle.close is None or event_candle.close <= 0:
        for horizon in horizons:
            create_study_event_result(
                db,
                study_run_id=study_run_id,
                event_id=event.id,
                instrument_id=instrument_id,
                horizon_trading_days=horizon,
                event_candle_id=event_candle.id,
                horizon_candle_id=None,
                event_price=event_candle.close,
                horizon_price=None,
                return_percent=None,
                status="skipped",
                skipped_reason="invalid_event_price",
            )
            results_created += 1
        create_study_run_event(
            db,
            study_run_id=study_run_id,
            event_id=event.id,
            status="skipped",
            skipped_reason="invalid_event_price",
        )
        create_study_skipped_event(
            db,
            study_run_id=study_run_id,
            event_id=event.id,
            reason_code="invalid_event_price",
            reason_detail="Event candle close is missing or not positive.",
            context_json={"event_candle_id": event_candle.id},
        )
        return _EventProcessingResult(event.id, "skipped", "invalid_event_price", results_created)

    successful_horizons = 0
    for horizon in horizons:
        horizon_candle = _find_horizon_candle(candles, event_index, horizon)
        if horizon_candle is None:
            create_study_event_result(
                db,
                study_run_id=study_run_id,
                event_id=event.id,
                instrument_id=instrument_id,
                horizon_trading_days=horizon,
                event_candle_id=event_candle.id,
                horizon_candle_id=None,
                event_price=event_candle.close,
                horizon_price=None,
                return_percent=None,
                status="skipped",
                skipped_reason="no_horizon_candles",
            )
            results_created += 1
            continue

        if horizon_candle.close is None:
            create_study_event_result(
                db,
                study_run_id=study_run_id,
                event_id=event.id,
                instrument_id=instrument_id,
                horizon_trading_days=horizon,
                event_candle_id=event_candle.id,
                horizon_candle_id=horizon_candle.id,
                event_price=event_candle.close,
                horizon_price=None,
                return_percent=None,
                status="skipped",
                skipped_reason="invalid_horizon_price",
            )
            results_created += 1
            continue

        create_study_event_result(
            db,
            study_run_id=study_run_id,
            event_id=event.id,
            instrument_id=instrument_id,
            horizon_trading_days=horizon,
            event_candle_id=event_candle.id,
            horizon_candle_id=horizon_candle.id,
            event_price=event_candle.close,
            horizon_price=horizon_candle.close,
            return_percent=_calculate_return_percent(event_candle.close, horizon_candle.close),
            status="success",
            skipped_reason=None,
        )
        successful_horizons += 1
        results_created += 1

    event_status = "success" if successful_horizons > 0 else "skipped"
    skipped_reason = None if successful_horizons > 0 else "no_horizon_candles"
    create_study_run_event(
        db,
        study_run_id=study_run_id,
        event_id=event.id,
        status=event_status,
        skipped_reason=skipped_reason,
    )
    if skipped_reason is not None:
        create_study_skipped_event(
            db,
            study_run_id=study_run_id,
            event_id=event.id,
            reason_code=skipped_reason,
            reason_detail="No requested horizon candle could be calculated.",
            context_json={"event_candle_id": event_candle.id},
        )

    return _EventProcessingResult(event.id, event_status, skipped_reason, results_created)


def _find_event_candle(
    candles: list[PriceCandle],
    event_date: date,
) -> tuple[int, PriceCandle | None]:
    for index, candle in enumerate(candles):
        if candle.trading_date >= event_date:
            return index, candle

    return -1, None


def _find_horizon_candle(
    candles: list[PriceCandle],
    event_index: int,
    horizon_trading_days: int,
) -> PriceCandle | None:
    horizon_index = event_index + horizon_trading_days
    if horizon_index >= len(candles):
        return None

    return candles[horizon_index]


def _calculate_return_percent(event_close: Decimal, horizon_close: Decimal) -> Decimal:
    return ((horizon_close - event_close) / event_close * Decimal("100")).quantize(
        PERCENT_QUANT,
        rounding=ROUND_HALF_UP,
    )


def _create_horizon_summaries(
    db: Session,
    *,
    study_run_id: int,
    instrument_id: int,
    horizons: list[int],
    event_results_count: int,
) -> list[HorizonSummaryResult]:
    from app.modules.studies.models import StudyEventResult

    pending: list[HorizonSummaryResult] = []
    for horizon in horizons:
        successful_results = [
            result
            for result in db.query(StudyEventResult)
            .filter(
                StudyEventResult.study_run_id == study_run_id,
                StudyEventResult.horizon_trading_days == horizon,
                StudyEventResult.status == "success",
            )
            .all()
        ]
        returns = [result.return_percent for result in successful_results if result.return_percent is not None]
        positive_count = sum(1 for value in returns if value > 0)
        negative_count = sum(1 for value in returns if value < 0)
        neutral_count = sum(1 for value in returns if value == 0)
        sample_size = len(returns)
        skipped_count = max(event_results_count - sample_size, 0)
        average_return_percent = _average(returns)
        median_return_percent = _median(returns)
        hit_rate_percent = (
            (Decimal(positive_count) / Decimal(sample_size) * Decimal("100")).quantize(
                PERCENT_QUANT,
                rounding=ROUND_HALF_UP,
            )
            if sample_size > 0
            else None
        )
        pending.append(
            HorizonSummaryResult(
                horizon_trading_days=horizon,
                sample_size=sample_size,
                skipped_count=skipped_count,
                positive_count=positive_count,
                negative_count=negative_count,
                neutral_count=neutral_count,
                average_return_percent=average_return_percent,
                median_return_percent=median_return_percent,
                hit_rate_percent=hit_rate_percent,
            ),
        )

    best = _find_best_summary(pending)
    summaries: list[HorizonSummaryResult] = []
    for item in pending:
        item.best_horizon_flag = best is item
        create_study_horizon_summary(
            db,
            study_run_id=study_run_id,
            instrument_id=instrument_id,
            horizon_trading_days=item.horizon_trading_days,
            sample_size=item.sample_size,
            skipped_count=item.skipped_count,
            positive_count=item.positive_count,
            negative_count=item.negative_count,
            neutral_count=item.neutral_count,
            average_return_percent=item.average_return_percent,
            median_return_percent=item.median_return_percent,
            hit_rate_percent=item.hit_rate_percent,
            best_horizon_flag=item.best_horizon_flag,
        )
        summaries.append(item)

    return summaries


def _average(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None

    return (sum(values) / Decimal(len(values))).quantize(PERCENT_QUANT, rounding=ROUND_HALF_UP)


def _median(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None

    return Decimal(str(median(values))).quantize(PERCENT_QUANT, rounding=ROUND_HALF_UP)


def _find_best_summary(summaries: list[HorizonSummaryResult]) -> HorizonSummaryResult | None:
    usable = [item for item in summaries if item.average_return_percent is not None]
    if not usable:
        return None

    return max(usable, key=lambda item: item.average_return_percent)


def _normalize_horizons(horizons: list[int]) -> list[int]:
    normalized = sorted({int(horizon) for horizon in horizons if int(horizon) > 0})
    if not normalized:
        raise EventStudyError("At least one positive horizon is required.")

    return normalized
