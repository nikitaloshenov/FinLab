from app.core.database import Base
from app.modules.alerts import models as alerts_models
from app.modules.events.models import (
    BenchmarkConstituent,
    Event,
    EventTarget,
    EventType,
    EventValue,
)
from app.modules.hypotheses import models as hypotheses_models
from app.modules.market import models as market_models
from app.modules.market_data.models import IngestionRun, PriceCandle, TradingCalendar
from app.modules.reference import models as reference_models
from app.modules.studies.models import (
    StudyBenchmarkResult,
    StudyComparison,
    StudyEventResult,
    StudyHorizonSummary,
    StudyRun,
    StudyRunEvent,
    StudySkippedEvent,
)
from app.modules.watchlist import models as watchlist_models


def test_analytics_core_models_are_registered_in_metadata():
    expected_tables = {
        "trading_calendar",
        "ingestion_runs",
        "price_candles",
        "event_types",
        "events",
        "event_values",
        "event_targets",
        "benchmark_constituents",
        "study_runs",
        "study_run_events",
        "study_event_results",
        "study_benchmark_results",
        "study_comparisons",
        "study_horizon_summary",
        "study_skipped_events",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_analytics_core_model_table_names():
    assert TradingCalendar.__tablename__ == "trading_calendar"
    assert IngestionRun.__tablename__ == "ingestion_runs"
    assert PriceCandle.__tablename__ == "price_candles"
    assert EventType.__tablename__ == "event_types"
    assert Event.__tablename__ == "events"
    assert EventValue.__tablename__ == "event_values"
    assert EventTarget.__tablename__ == "event_targets"
    assert BenchmarkConstituent.__tablename__ == "benchmark_constituents"
    assert StudyRun.__tablename__ == "study_runs"
    assert StudyRunEvent.__tablename__ == "study_run_events"
    assert StudyEventResult.__tablename__ == "study_event_results"
    assert StudyBenchmarkResult.__tablename__ == "study_benchmark_results"
    assert StudyComparison.__tablename__ == "study_comparisons"
    assert StudyHorizonSummary.__tablename__ == "study_horizon_summary"
    assert StudySkippedEvent.__tablename__ == "study_skipped_events"


def test_analytics_core_constraints_and_indexes_are_registered():
    price_candles_table = Base.metadata.tables["price_candles"]
    events_table = Base.metadata.tables["events"]
    study_event_results_table = Base.metadata.tables["study_event_results"]

    price_constraints = {constraint.name for constraint in price_candles_table.constraints}
    event_constraints = {constraint.name for constraint in events_table.constraints}
    result_constraints = {constraint.name for constraint in study_event_results_table.constraints}
    price_indexes = {index.name for index in price_candles_table.indexes}

    assert "uq_price_candles_instrument_interval_begin_at" in price_constraints
    assert "uq_events_event_type_event_date_title" in event_constraints
    assert "uq_study_event_results_run_event_instrument_horizon" in result_constraints
    assert "ix_price_candles_instrument_interval_trading_date" in price_indexes


def test_legacy_tables_remain_registered_in_metadata():
    legacy_tables = {
        "tickers",
        "ticker_latest_prices",
        "watchlist_items",
        "alerts",
        "alert_events",
        "key_rate_decisions",
    }

    assert legacy_tables.issubset(Base.metadata.tables.keys())
