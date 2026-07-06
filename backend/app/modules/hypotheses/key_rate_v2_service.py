from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from statistics import median

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.events.models import Event
from app.modules.events.service import KEY_RATE_EVENT_TYPE_CODE, import_key_rate_decisions_to_events
from app.modules.market_data.models import PriceCandle
from app.modules.market_data.service import CandleImportResult, import_daily_candles
from app.modules.reference.models import Instrument, IssuerSectorHistory, Sector
from app.modules.studies.models import StudyEventResult
from app.modules.studies.repository import (
    get_event_type_by_code,
    get_preferred_instrument_by_secid,
    list_events_by_type,
)
from app.modules.studies.service import EventStudyRunResult, run_event_study


DEFAULT_KEY_RATE_V2_HORIZONS = [1, 5, 10]
MAX_KEY_RATE_V2_HORIZON = 60
SAMPLE_RESULTS_LIMIT = 5
PERCENT_QUANT = Decimal("0.000001")
DAILY_CANDLE_COVERAGE_START_TOLERANCE_DAYS = 14
DAILY_CANDLE_COVERAGE_END_TOLERANCE_DAYS = 14


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
class KeyRateV2SectorInfo:
    code: str
    name: str


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
class DailyCandleCoverage:
    candles_count: int
    earliest_date: date | None
    latest_date: date | None


@dataclass
class KeyRateV2SampleResult:
    event_id: int
    event_date: date | None
    event_title: str | None
    horizon_trading_days: int
    event_price: Decimal | None
    horizon_price: Decimal | None
    return_percent: Decimal | None
    status: str
    skipped_reason: str | None


@dataclass
class KeyRateV2EventHorizonResult:
    horizon_trading_days: int
    return_percent: Decimal | None
    status: str
    skipped_reason: str | None


@dataclass
class KeyRateV2EventResult:
    event_id: int
    event_date: date
    direction: str | None
    title: str
    horizons: list[KeyRateV2EventHorizonResult] = field(default_factory=list)
    reason: str | None = None


@dataclass
class KeyRateV2EventsInfo:
    found_total: int
    used_total: int
    skipped_total: int
    used: list[KeyRateV2EventResult] = field(default_factory=list)
    skipped: list[KeyRateV2EventResult] = field(default_factory=list)


@dataclass
class KeyRateV2SectorPeerSkipped:
    secid: str
    reason: str


@dataclass
class KeyRateV2SectorSummary:
    horizon_trading_days: int
    selected_average_return_percent: Decimal | None
    sector_average_return_percent: Decimal | None
    sector_median_return_percent: Decimal | None
    excess_return_percent: Decimal | None
    selected_rank_in_sector: int | None
    sector_instrument_count: int
    sector_hit_rate_percent: Decimal | None


@dataclass
class KeyRateV2SectorDataPreparation:
    auto_prepare_sector_data: bool
    sector_peer_candles_importer_ran_count: int
    sector_peer_candles_rows_loaded: int
    peers_prepared: int
    peers_skipped_due_to_missing_data: int


@dataclass
class KeyRateV2SectorComparison:
    status: str
    sector: KeyRateV2SectorInfo | None = None
    selected_secid: str | None = None
    peers_total: int = 0
    peers_used: int = 0
    peer_secids: list[str] = field(default_factory=list)
    peers_skipped: list[KeyRateV2SectorPeerSkipped] = field(default_factory=list)
    summary: list[KeyRateV2SectorSummary] = field(default_factory=list)
    data_preparation: KeyRateV2SectorDataPreparation | None = None


@dataclass
class KeyRateV2AnalyzeResult:
    study_run_id: int | None
    secid: str
    instrument: KeyRateV2InstrumentInfo
    event_type: str
    event_direction: str
    events_total: int
    events_processed: int
    events_skipped: int
    horizons: list[int]
    summary: list
    data_preparation: KeyRateV2DataPreparationInfo
    status: str
    events: KeyRateV2EventsInfo
    sample_results: list[KeyRateV2SampleResult] = field(default_factory=list)
    sector_comparison: KeyRateV2SectorComparison | None = None


def analyze_key_rate_impact_v2(
    db: Session,
    *,
    secid: str,
    date_from: date | None = None,
    date_to: date | None = None,
    horizons: list[int] | None = None,
    auto_prepare_data: bool = True,
    refresh_candles: bool = False,
    include_sector_comparison: bool = True,
    sector_peer_limit: int = 8,
    auto_prepare_sector_data: bool = False,
    event_direction: str = "all",
) -> KeyRateV2AnalyzeResult:
    normalized_horizons = _normalize_horizons(horizons or DEFAULT_KEY_RATE_V2_HORIZONS)
    normalized_event_direction = _normalize_event_direction(event_direction)
    event_direction_filter = (
        None if normalized_event_direction == "all" else normalized_event_direction
    )
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
            direction=event_direction_filter,
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
                direction=event_direction_filter,
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
            import_from, import_to = _determine_missing_candle_import_range(
                db,
                instrument_id=instrument.id,
                required_from=required_from,
                required_to=required_to,
            )
            try:
                if import_from is not None and import_to is not None:
                    import_result = import_daily_candles(
                        db,
                        secid=instrument.secid,
                        date_from=import_from,
                        date_to=import_to,
                        interval="1d",
                    )
                else:
                    import_result = CandleImportResult(
                        secid=instrument.secid,
                        interval="1d",
                        date_from=required_from,
                        date_to=_effective_required_to(required_to),
                        rows_loaded=0,
                        ingestion_run_id=0,
                        status="skipped",
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
        event_direction=event_direction_filter,
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
    sector_comparison = _build_sector_comparison(
        db,
        selected_instrument=instrument,
        events=events,
        horizons=normalized_horizons,
        selected_summary=study_result.summary,
        required_from=required_from,
        required_to=required_to,
        include_sector_comparison=include_sector_comparison,
        sector_peer_limit=sector_peer_limit,
        auto_prepare_sector_data=auto_prepare_sector_data,
    )

    return _build_result(
        db,
        instrument=instrument,
        study_result=study_result,
        data_preparation=data_preparation,
        sector_comparison=sector_comparison,
        event_direction=normalized_event_direction,
    )


def _build_result(
    db: Session,
    *,
    instrument: Instrument,
    study_result: EventStudyRunResult,
    data_preparation: KeyRateV2DataPreparationInfo,
    sector_comparison: KeyRateV2SectorComparison | None,
    event_direction: str,
) -> KeyRateV2AnalyzeResult:
    sample_results = []
    events_info = KeyRateV2EventsInfo(
        found_total=study_result.events_total,
        used_total=study_result.events_processed,
        skipped_total=study_result.events_skipped,
    )
    if study_result.study_run_id is not None:
        all_event_rows = db.execute(
            select(StudyEventResult, Event)
            .join(Event, Event.id == StudyEventResult.event_id)
            .where(StudyEventResult.study_run_id == study_result.study_run_id)
            .order_by(Event.event_date, Event.id, StudyEventResult.horizon_trading_days),
        ).all()
        events_info = _build_events_info(
            all_event_rows,
            found_total=study_result.events_total,
            used_total=study_result.events_processed,
            skipped_total=study_result.events_skipped,
        )
        sample_results = [
            KeyRateV2SampleResult(
                event_id=result.event_id,
                event_date=event.event_date,
                event_title=event.title,
                horizon_trading_days=result.horizon_trading_days,
                event_price=result.event_price,
                horizon_price=result.horizon_price,
                return_percent=result.return_percent,
                status=result.status,
                skipped_reason=result.skipped_reason,
            )
            for result, event in db.execute(
                select(StudyEventResult, Event)
                .join(Event, Event.id == StudyEventResult.event_id)
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
            sector=sector_comparison.sector.code
            if sector_comparison is not None and sector_comparison.sector is not None
            else None,
        ),
        event_type=study_result.event_type,
        event_direction=event_direction,
        events_total=study_result.events_total,
        events_processed=study_result.events_processed,
        events_skipped=study_result.events_skipped,
        horizons=study_result.horizons,
        summary=study_result.summary,
        data_preparation=data_preparation,
        status=study_result.status,
        events=events_info,
        sample_results=sample_results,
        sector_comparison=sector_comparison,
    )


def _build_events_info(
    rows,
    *,
    found_total: int,
    used_total: int,
    skipped_total: int,
) -> KeyRateV2EventsInfo:
    grouped: dict[int, KeyRateV2EventResult] = {}

    for result, event in rows:
        event_result = grouped.get(event.id)
        if event_result is None:
            event_result = KeyRateV2EventResult(
                event_id=event.id,
                event_date=event.event_date,
                direction=event.direction,
                title=event.title,
            )
            grouped[event.id] = event_result

        event_result.horizons.append(
            KeyRateV2EventHorizonResult(
                horizon_trading_days=result.horizon_trading_days,
                return_percent=result.return_percent,
                status=result.status,
                skipped_reason=result.skipped_reason,
            ),
        )

    used = []
    skipped = []
    for event_result in grouped.values():
        has_success = any(item.status == "success" for item in event_result.horizons)
        if has_success:
            used.append(event_result)
            continue

        skipped_reasons = [
            item.skipped_reason for item in event_result.horizons if item.skipped_reason
        ]
        event_result.reason = skipped_reasons[0] if skipped_reasons else "unknown"
        skipped.append(event_result)

    return KeyRateV2EventsInfo(
        found_total=found_total,
        used_total=used_total,
        skipped_total=skipped_total,
        used=used,
        skipped=skipped,
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


def _normalize_event_direction(event_direction: str | None) -> str:
    if event_direction is None:
        return "all"

    normalized = event_direction.strip().lower()
    aliases = {
        "": "all",
        "all": "all",
        "hike": "hike",
        "rate_hike": "hike",
        "cut": "cut",
        "rate_cut": "cut",
        "hold": "hold",
        "rate_hold": "hold",
    }

    if normalized not in aliases:
        raise KeyRateV2DataNotPreparedError(
            "event_direction must be one of all, hike, cut, hold.",
        )

    return aliases[normalized]


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

    coverage = _get_daily_candle_coverage(
        db,
        instrument_id=instrument_id,
        required_from=required_from,
        required_to=required_to,
    )

    if (
        not coverage.candles_count
        or coverage.earliest_date is None
        or coverage.latest_date is None
    ):
        return False

    if coverage.candles_count < 2:
        return False

    if (
        coverage.earliest_date
        > required_from + timedelta(days=DAILY_CANDLE_COVERAGE_START_TOLERANCE_DAYS)
    ):
        return False

    effective_required_to = _effective_required_to(required_to)
    if (
        coverage.latest_date
        < effective_required_to - timedelta(days=DAILY_CANDLE_COVERAGE_END_TOLERANCE_DAYS)
    ):
        return False

    return True


def _get_daily_candle_coverage(
    db: Session,
    *,
    instrument_id: int,
    required_from: date,
    required_to: date,
) -> DailyCandleCoverage:
    effective_required_to = _effective_required_to(required_to)
    candles_count, earliest_date, latest_date = db.execute(
        select(
            func.count(PriceCandle.id),
            func.min(PriceCandle.trading_date),
            func.max(PriceCandle.trading_date),
        ).where(
            PriceCandle.instrument_id == instrument_id,
            PriceCandle.interval == "1d",
            PriceCandle.trading_date >= required_from,
            PriceCandle.trading_date <= effective_required_to,
        ),
    ).one()

    return DailyCandleCoverage(
        candles_count=candles_count or 0,
        earliest_date=earliest_date,
        latest_date=latest_date,
    )


def _determine_missing_candle_import_range(
    db: Session,
    *,
    instrument_id: int,
    required_from: date,
    required_to: date,
) -> tuple[date | None, date | None]:
    effective_required_to = _effective_required_to(required_to)
    coverage = _get_daily_candle_coverage(
        db,
        instrument_id=instrument_id,
        required_from=required_from,
        required_to=required_to,
    )

    if coverage.earliest_date is None or coverage.latest_date is None:
        return required_from, effective_required_to

    if (
        coverage.earliest_date
        > required_from + timedelta(days=DAILY_CANDLE_COVERAGE_START_TOLERANCE_DAYS)
    ):
        return required_from, effective_required_to

    import_from = coverage.latest_date + timedelta(days=1)
    if import_from > effective_required_to:
        return None, None

    return import_from, effective_required_to


def _effective_required_to(required_to: date) -> date:
    return min(required_to, date.today())


def _build_sector_comparison(
    db: Session,
    *,
    selected_instrument: Instrument,
    events,
    horizons: list[int],
    selected_summary: list,
    required_from: date | None,
    required_to: date | None,
    include_sector_comparison: bool,
    sector_peer_limit: int,
    auto_prepare_sector_data: bool,
) -> KeyRateV2SectorComparison:
    data_preparation = KeyRateV2SectorDataPreparation(
        auto_prepare_sector_data=auto_prepare_sector_data,
        sector_peer_candles_importer_ran_count=0,
        sector_peer_candles_rows_loaded=0,
        peers_prepared=0,
        peers_skipped_due_to_missing_data=0,
    )

    if not include_sector_comparison:
        return KeyRateV2SectorComparison(
            status="disabled",
            selected_secid=selected_instrument.secid,
            data_preparation=data_preparation,
        )

    sector = _get_current_sector(db, selected_instrument)
    if sector is None:
        return KeyRateV2SectorComparison(
            status="no_sector_mapping",
            selected_secid=selected_instrument.secid,
            data_preparation=data_preparation,
        )

    peers_total, peers = _list_sector_peers(
        db,
        selected_instrument=selected_instrument,
        sector_id=sector.id,
        limit=sector_peer_limit,
    )
    sector_info = KeyRateV2SectorInfo(code=sector.code, name=sector.name)
    if not peers:
        return KeyRateV2SectorComparison(
            status="no_peers",
            sector=sector_info,
            selected_secid=selected_instrument.secid,
            peers_total=peers_total,
            data_preparation=data_preparation,
        )

    peer_returns_by_horizon: dict[int, list[tuple[str, Decimal]]] = {
        horizon: [] for horizon in horizons
    }
    peer_secids: list[str] = []
    peers_skipped: list[KeyRateV2SectorPeerSkipped] = []

    for peer in peers:
        candles = _list_daily_candles(db, instrument_id=peer.id)
        has_required_candles = _has_daily_candles(
            db,
            instrument_id=peer.id,
            required_from=required_from,
            required_to=required_to,
        )
        if not has_required_candles and auto_prepare_sector_data:
            try:
                if required_from is not None and required_to is not None:
                    import_from, import_to = _determine_missing_candle_import_range(
                        db,
                        instrument_id=peer.id,
                        required_from=required_from,
                        required_to=required_to,
                    )
                    if import_from is None or import_to is None:
                        import_result = CandleImportResult(
                            secid=peer.secid,
                            interval="1d",
                            date_from=required_from,
                            date_to=_effective_required_to(required_to),
                            rows_loaded=0,
                            ingestion_run_id=0,
                            status="skipped",
                        )
                    else:
                        import_result = import_daily_candles(
                            db,
                            secid=peer.secid,
                            date_from=import_from,
                            date_to=import_to,
                            interval="1d",
                        )
                    data_preparation.sector_peer_candles_importer_ran_count += 1
                    data_preparation.sector_peer_candles_rows_loaded += import_result.rows_loaded
                    candles = _list_daily_candles(db, instrument_id=peer.id)
                    has_required_candles = _has_daily_candles(
                        db,
                        instrument_id=peer.id,
                        required_from=required_from,
                        required_to=required_to,
                    )
            except Exception:
                peers_skipped.append(
                    KeyRateV2SectorPeerSkipped(secid=peer.secid, reason="candle_import_failed"),
                )
                data_preparation.peers_skipped_due_to_missing_data += 1
                continue

        if not candles or not has_required_candles:
            peers_skipped.append(
                KeyRateV2SectorPeerSkipped(secid=peer.secid, reason="missing_daily_candles"),
            )
            data_preparation.peers_skipped_due_to_missing_data += 1
            continue

        returns = _calculate_peer_returns(events=events, candles=candles, horizons=horizons)
        if not any(returns.values()):
            peers_skipped.append(
                KeyRateV2SectorPeerSkipped(secid=peer.secid, reason="insufficient_event_data"),
            )
            data_preparation.peers_skipped_due_to_missing_data += 1
            continue

        peer_secids.append(peer.secid)
        data_preparation.peers_prepared += 1
        for horizon, horizon_returns in returns.items():
            if horizon_returns:
                peer_average = _average(horizon_returns)
                if peer_average is not None:
                    peer_returns_by_horizon[horizon].append((peer.secid, peer_average))

    if not peer_secids:
        return KeyRateV2SectorComparison(
            status="insufficient_data",
            sector=sector_info,
            selected_secid=selected_instrument.secid,
            peers_total=peers_total,
            peers_used=0,
            peer_secids=[],
            peers_skipped=peers_skipped,
            data_preparation=data_preparation,
        )

    selected_average_by_horizon = {
        item.horizon_trading_days: item.average_return_percent for item in selected_summary
    }
    summary = [
        _build_sector_summary(
            horizon=horizon,
            selected_average=selected_average_by_horizon.get(horizon),
            peer_returns=peer_returns_by_horizon[horizon],
        )
        for horizon in horizons
    ]

    return KeyRateV2SectorComparison(
        status="success" if any(item.sector_instrument_count > 0 for item in summary) else "insufficient_data",
        sector=sector_info,
        selected_secid=selected_instrument.secid,
        peers_total=peers_total,
        peers_used=len(peer_secids),
        peer_secids=peer_secids,
        peers_skipped=peers_skipped,
        summary=summary,
        data_preparation=data_preparation,
    )


def _get_current_sector(db: Session, instrument: Instrument) -> Sector | None:
    if instrument.issuer_id is None:
        return None

    return db.scalar(
        select(Sector)
        .join(IssuerSectorHistory, IssuerSectorHistory.sector_id == Sector.id)
        .where(IssuerSectorHistory.issuer_id == instrument.issuer_id)
        .order_by(IssuerSectorHistory.valid_from.desc(), IssuerSectorHistory.id.desc())
        .limit(1),
    )


def _list_sector_peers(
    db: Session,
    *,
    selected_instrument: Instrument,
    sector_id: int,
    limit: int,
) -> tuple[int, list[Instrument]]:
    base_query = (
        select(Instrument)
        .join(IssuerSectorHistory, IssuerSectorHistory.issuer_id == Instrument.issuer_id)
        .where(
            IssuerSectorHistory.sector_id == sector_id,
            Instrument.id != selected_instrument.id,
            Instrument.is_active.is_(True),
            Instrument.asset_type == selected_instrument.asset_type,
        )
        .distinct()
    )
    peers_total = db.scalar(
        select(func.count(func.distinct(Instrument.id)))
        .select_from(Instrument)
        .join(IssuerSectorHistory, IssuerSectorHistory.issuer_id == Instrument.issuer_id)
        .where(
            IssuerSectorHistory.sector_id == sector_id,
            Instrument.id != selected_instrument.id,
            Instrument.is_active.is_(True),
            Instrument.asset_type == selected_instrument.asset_type,
        ),
    )
    peers = list(
        db.scalars(
            base_query.order_by(Instrument.secid).limit(limit),
        ).all(),
    )

    return peers_total or 0, peers


def _list_daily_candles(db: Session, *, instrument_id: int) -> list[PriceCandle]:
    return list(
        db.scalars(
            select(PriceCandle)
            .where(
                PriceCandle.instrument_id == instrument_id,
                PriceCandle.interval == "1d",
            )
            .order_by(PriceCandle.trading_date, PriceCandle.begin_at, PriceCandle.id),
        ).all(),
    )


def _calculate_peer_returns(
    *,
    events,
    candles: list[PriceCandle],
    horizons: list[int],
) -> dict[int, list[Decimal]]:
    returns_by_horizon: dict[int, list[Decimal]] = {horizon: [] for horizon in horizons}
    for event in events:
        event_index, event_candle = _find_event_candle(candles, event.event_date)
        if event_candle is None or event_candle.close is None or event_candle.close <= 0:
            continue

        for horizon in horizons:
            horizon_candle = _find_horizon_candle(candles, event_index, horizon)
            if horizon_candle is None or horizon_candle.close is None:
                continue

            returns_by_horizon[horizon].append(
                _calculate_return_percent(event_candle.close, horizon_candle.close),
            )

    return returns_by_horizon


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


def _build_sector_summary(
    *,
    horizon: int,
    selected_average: Decimal | None,
    peer_returns: list[tuple[str, Decimal]],
) -> KeyRateV2SectorSummary:
    values = [value for _, value in peer_returns]
    sector_average = _average(values)
    sector_median = _median(values)
    excess_return = (
        (selected_average - sector_average).quantize(PERCENT_QUANT, rounding=ROUND_HALF_UP)
        if selected_average is not None and sector_average is not None
        else None
    )
    rank = _selected_rank(selected_average=selected_average, peer_returns=values)
    hit_rate = (
        (Decimal(sum(1 for value in values if value > 0)) / Decimal(len(values)) * Decimal("100")).quantize(
            PERCENT_QUANT,
            rounding=ROUND_HALF_UP,
        )
        if values
        else None
    )

    return KeyRateV2SectorSummary(
        horizon_trading_days=horizon,
        selected_average_return_percent=selected_average,
        sector_average_return_percent=sector_average,
        sector_median_return_percent=sector_median,
        excess_return_percent=excess_return,
        selected_rank_in_sector=rank,
        sector_instrument_count=len(values),
        sector_hit_rate_percent=hit_rate,
    )


def _average(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None

    return (sum(values) / Decimal(len(values))).quantize(PERCENT_QUANT, rounding=ROUND_HALF_UP)


def _median(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None

    return Decimal(str(median(values))).quantize(PERCENT_QUANT, rounding=ROUND_HALF_UP)


def _selected_rank(
    *,
    selected_average: Decimal | None,
    peer_returns: list[Decimal],
) -> int | None:
    if selected_average is None or not peer_returns:
        return None

    return 1 + sum(1 for value in peer_returns if value > selected_average)
