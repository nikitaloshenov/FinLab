from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.events.service import KEY_RATE_EVENT_TYPE_CODE, import_key_rate_decisions_to_events
from app.modules.market_data.models import PriceCandle
from app.modules.market_data.service import CandleImportResult, import_daily_candles
from app.modules.reference.models import Instrument
from app.modules.studies.models import StudyEventResult
from app.modules.studies.repository import (
    get_event_type_by_code,
    get_preferred_instrument_by_secid,
    list_events_by_type,
)
from app.modules.studies.service import EventStudyRunResult, run_event_study


DEFAULT_KEY_RATE_V2_HORIZONS = [1, 5, 10, 20]
MAX_KEY_RATE_V2_HORIZON = 60
SAMPLE_RESULTS_LIMIT = 5


class KeyRateV2Error(Exception):
    pass


class KeyRateV2UnknownInstrumentError(KeyRateV2Error):
    pass


class KeyRateV2DataNotPreparedError(KeyRateV2Error):
    pass


class KeyRateV2PreparationError(KeyRateV2Error):
    pass


@dataclass
class KeyRateV2InstrumentInfo:
    secid: str
    name: str | None
    asset_type: str
    sector: str | None = None


@dataclass
class KeyRateV2DataPreparationInfo:
    key_rate_events_ready: bool
    key_rate_events_importer_ran: bool
    candles_ready: bool
    candles_importer_ran: bool
    candles_rows_loaded: int
    required_from: date | None
    required_to: date | None


@dataclass
class KeyRateV2SampleResult:
    event_id: int
    horizon_trading_days: int
    event_price: Decimal | None
    horizon_price: Decimal | None
    return_percent: Decimal | None
    status: str
    skipped_reason: str | None


@dataclass
class KeyRateV2AnalyzeResult:
    study_run_id: int | None
    secid: str
    instrument: KeyRateV2InstrumentInfo
    event_type: str
    events_total: int
    events_processed: int
    events_skipped: int
    horizons: list[int]
    summary: list
    data_preparation: KeyRateV2DataPreparationInfo
    status: str
    sample_results: list[KeyRateV2SampleResult] = field(default_factory=list)


def analyze_key_rate_impact_v2(
    db: Session,
    *,
    secid: str,
    date_from: date | None = None,
    date_to: date | None = None,
    horizons: list[int] | None = None,
    auto_prepare_data: bool = True,
    refresh_candles: bool = False,
) -> KeyRateV2AnalyzeResult:
    normalized_horizons = _normalize_horizons(horizons or DEFAULT_KEY_RATE_V2_HORIZONS)
    instrument = get_preferred_instrument_by_secid(db, secid)
    if instrument is None:
        raise KeyRateV2UnknownInstrumentError(f"Unknown instrument: {secid.strip().upper()}")

    events_ready = False
    events_importer_ran = False
    event_type = get_event_type_by_code(db, KEY_RATE_EVENT_TYPE_CODE)
    events = []
    if event_type is not None:
        events = list_events_by_type(
            db,
            event_type_id=event_type.id,
            date_from=date_from,
            date_to=date_to,
        )
        events_ready = len(events) > 0

    if not events_ready and auto_prepare_data:
        import_key_rate_decisions_to_events(db)
        events_importer_ran = True
        event_type = get_event_type_by_code(db, KEY_RATE_EVENT_TYPE_CODE)
        if event_type is not None:
            events = list_events_by_type(
                db,
                event_type_id=event_type.id,
                date_from=date_from,
                date_to=date_to,
            )
            events_ready = len(events) > 0

    if event_type is None:
        raise KeyRateV2DataNotPreparedError(
            "Key rate decision events are not prepared. Enable auto_prepare_data or import events first.",
        )

    if not events_ready and not auto_prepare_data:
        raise KeyRateV2DataNotPreparedError(
            "No key rate decision events found for the selected range.",
        )

    required_from, required_to = _determine_required_candle_range(
        events=events,
        date_from=date_from,
        date_to=date_to,
        horizons=normalized_horizons,
    )
    candles_ready = _has_daily_candles(
        db,
        instrument_id=instrument.id,
        required_from=required_from,
        required_to=required_to,
    )
    candles_importer_ran = False
    candles_rows_loaded = 0

    if required_from is not None and required_to is not None:
        if refresh_candles or (not candles_ready and auto_prepare_data):
            try:
                import_result = import_daily_candles(
                    db,
                    secid=instrument.secid,
                    date_from=required_from,
                    date_to=required_to,
                    interval="1d",
                )
            except Exception as error:
                raise KeyRateV2PreparationError(f"Failed to prepare daily candles: {error}") from error

            candles_importer_ran = True
            candles_rows_loaded = import_result.rows_loaded
            candles_ready = _has_daily_candles(
                db,
                instrument_id=instrument.id,
                required_from=required_from,
                required_to=required_to,
            )

    study_result = run_event_study(
        db,
        secid=instrument.secid,
        event_type_code=KEY_RATE_EVENT_TYPE_CODE,
        horizons=normalized_horizons,
        date_from=date_from,
        date_to=date_to,
    )
    data_preparation = KeyRateV2DataPreparationInfo(
        key_rate_events_ready=events_ready,
        key_rate_events_importer_ran=events_importer_ran,
        candles_ready=candles_ready,
        candles_importer_ran=candles_importer_ran,
        candles_rows_loaded=candles_rows_loaded,
        required_from=required_from,
        required_to=required_to,
    )

    return _build_result(
        db,
        instrument=instrument,
        study_result=study_result,
        data_preparation=data_preparation,
    )


def _build_result(
    db: Session,
    *,
    instrument: Instrument,
    study_result: EventStudyRunResult,
    data_preparation: KeyRateV2DataPreparationInfo,
) -> KeyRateV2AnalyzeResult:
    sample_results = []
    if study_result.study_run_id is not None:
        sample_results = [
            KeyRateV2SampleResult(
                event_id=result.event_id,
                horizon_trading_days=result.horizon_trading_days,
                event_price=result.event_price,
                horizon_price=result.horizon_price,
                return_percent=result.return_percent,
                status=result.status,
                skipped_reason=result.skipped_reason,
            )
            for result in db.scalars(
                select(StudyEventResult)
                .where(StudyEventResult.study_run_id == study_result.study_run_id)
                .order_by(StudyEventResult.event_id, StudyEventResult.horizon_trading_days)
                .limit(SAMPLE_RESULTS_LIMIT),
            ).all()
        ]

    return KeyRateV2AnalyzeResult(
        study_run_id=study_result.study_run_id,
        secid=study_result.secid,
        instrument=KeyRateV2InstrumentInfo(
            secid=instrument.secid,
            name=instrument.name,
            asset_type=instrument.asset_type,
            sector=None,
        ),
        event_type=study_result.event_type,
        events_total=study_result.events_total,
        events_processed=study_result.events_processed,
        events_skipped=study_result.events_skipped,
        horizons=study_result.horizons,
        summary=study_result.summary,
        data_preparation=data_preparation,
        status=study_result.status,
        sample_results=sample_results,
    )


def _normalize_horizons(horizons: list[int]) -> list[int]:
    normalized = sorted({int(horizon) for horizon in horizons if int(horizon) > 0})
    if not normalized:
        raise KeyRateV2DataNotPreparedError("At least one positive horizon is required.")

    if any(horizon > MAX_KEY_RATE_V2_HORIZON for horizon in normalized):
        raise KeyRateV2DataNotPreparedError(
            f"Horizons must be less than or equal to {MAX_KEY_RATE_V2_HORIZON}.",
        )

    return normalized


def _determine_required_candle_range(
    *,
    events,
    date_from: date | None,
    date_to: date | None,
    horizons: list[int],
) -> tuple[date | None, date | None]:
    if date_from is not None:
        required_from = date_from
    elif events:
        required_from = min(event.event_date for event in events)
    else:
        required_from = None

    if date_to is not None:
        base_to = date_to
    elif events:
        base_to = max(event.event_date for event in events)
    else:
        base_to = None

    if base_to is None:
        return required_from, None

    buffer_days = max(45, max(horizons) * 3)
    return required_from, base_to + timedelta(days=buffer_days)


def _has_daily_candles(
    db: Session,
    *,
    instrument_id: int,
    required_from: date | None,
    required_to: date | None,
) -> bool:
    if required_from is None or required_to is None:
        return False

    candles_count = db.scalar(
        select(func.count())
        .select_from(PriceCandle)
        .where(
            PriceCandle.instrument_id == instrument_id,
            PriceCandle.interval == "1d",
            PriceCandle.trading_date >= required_from,
            PriceCandle.trading_date <= required_to,
        ),
    )

    return bool(candles_count)
