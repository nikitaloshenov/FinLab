# FinLab Analytics Database Specification

Status: living architecture document. This is not a migration file and not final SQL design.

The document describes the target/implemented analytics database direction for FinLab. It exists to guide SQLAlchemy models, Alembic migrations and future refactors without breaking the live demo.

## Goal

FinLab is moving from a generic ticker dashboard toward a historical event-study product.

The analytics database should support:

- normalized market reference data;
- persisted daily prices for reproducible analysis;
- generic market/macro events;
- reproducible study runs;
- event-level and horizon-level results;
- peer/sector comparison;
- future event analyzers beyond key-rate decisions.

## Design Principles

1. Do not break live demo tables with large refactors.
2. Add analytics tables incrementally.
3. Keep user/demo state separate from analytics/reference/event data.
4. Use persisted daily prices for event-study, not latest/watchlist prices.
5. Store skipped data explicitly instead of hiding missing data.
6. Preserve data source/provenance wherever possible.
7. Do not treat the `MOEX` stock as the IMOEX market benchmark.

## Current Layers

### User / Demo Layer

Existing product/demo state:

- `watchlist_items`;
- `alerts`;
- `alert_events`;
- anonymous demo-session fields.

This layer should remain simple and should not be mixed with analytics data.

### Legacy Market Layer

Existing legacy tables:

- `tickers`;
- `ticker_latest_prices`.

These remain for current dashboard/watchlist/alerts behavior.

### Reference Layer

Core tables:

- `issuers`;
- `instruments`;
- `sectors`;
- `issuer_sector_history`;
- `benchmarks`;
- `data_sources`.

Important decisions:

- A company/issuer can have multiple instruments, for example `SBER` and `SBERP`.
- Sector membership belongs primarily to the issuer through `issuer_sector_history`.
- Instrument-level sector override can be added later if a real exception appears.
- A market index such as IMOEX should be stored as an `instrument` with `asset_type = index`.
- `benchmarks` should point to a real benchmark/index instrument when available.

### Market Data Layer

Core tables:

- `price_candles`;
- `ingestion_runs`;
- optional/future `trading_calendar`.

`price_candles` decisions:

- `begin_at`: timezone-aware DateTime;
- `trading_date`: Date;
- `interval`: for current analyzer, `1d`;
- OHLCV fields stored as Numeric/Decimal-compatible values;
- `source_id nullable`;
- `ingestion_run_id nullable`;
- unique `(instrument_id, interval, begin_at)`;
- index `(instrument_id, interval, trading_date)`.

`trading_date` exists to make event-study horizon lookup easier: D+1, D+5 and D+10 are trading-day offsets over sorted daily rows.

### Event Layer

Core tables:

- `event_types`;
- `events`;
- `event_values`;
- `event_targets`.

Events should be generic enough to support:

- key-rate decisions;
- inflation releases;
- currency shocks;
- oil shocks;
- dividend events;
- corporate events.

Important fields:

- `events.event_date` as event-study anchor;
- `events.event_datetime nullable`;
- `events.source_event_id nullable`;
- `events.direction nullable`;
- `events.importance nullable`;
- `events.source_id nullable`.

If a source provides a stable event id, store it in `source_event_id` to help prevent duplicates in future importers.

### Study Layer

Core tables:

- `study_runs`;
- `study_run_events`;
- `study_event_results`;
- `study_horizon_summary`;
- `study_skipped_events`;
- optional/future `study_benchmark_results`;
- optional/future `study_comparisons`.

Study runs should store:

- `study_type`;
- `event_type_id`;
- target instrument/issuer/sector fields as needed;
- `params_json`;
- `methodology_version`;
- optional `data_version`;
- optional `data_cutoff_at`;
- status/error/completion fields.

All horizon fields should use `horizon_trading_days`, not ambiguous `horizon_days`.

## Current Key Rate Analyzer Mapping

Current analyzer endpoint:

```text
POST /api/v1/hypotheses/key-rate-impact/v2
```

Current flow:

1. Resolve selected `secid` through `instruments`.
2. Load key-rate decision events from the generic `events` layer.
3. Use daily prices from `price_candles` where `interval = 1d`.
4. Check selected-instrument coverage for the requested period.
5. Import the missing selected-ticker tail if coverage is stale.
6. Run event-study.
7. Persist `study_runs`, event results, horizon summaries and skipped events.
8. Optionally calculate peer-based sector comparison.

## Event-Study Methodology

For each event:

1. Use `events.event_date` as the anchor.
2. Find the first selected-instrument `price_candles` row where:
   - `interval = 1d`;
   - `trading_date >= event_date`.
3. Use this row's close as `event_price`.
4. For each horizon `N`, use the candle at `event_index + N`.
5. Calculate:

```text
return_percent = (horizon_close - event_close) / event_close * 100
```

Skipped cases:

- `no_event_candle`;
- `invalid_event_price`;
- `no_horizon_candles`;
- `invalid_horizon_price`;
- `no_events_found`.

Missing data must not be converted to fake zero returns.

## Sector Comparison

Sector comparison is peer-based:

- resolve current sector through `issuer_sector_history`;
- select active peer instruments from the same sector and asset type;
- exclude the selected instrument;
- use the same events and horizons;
- compare selected average return with peer average/median.

This is not an official sector index.

## Migration Strategy

Do not delete legacy tables early.

Recommended approach:

1. Keep legacy `tickers`, `ticker_latest_prices`, watchlist and alerts intact.
2. Create/extend analytics tables in parallel.
3. Backfill reference and event data.
4. Gradually move analyzer services to analytics tables.
5. Keep old endpoints until compatibility is no longer needed.
6. Remove legacy tables only after the live demo and API paths are fully migrated.

## Future Metrics Layer

Potential future tables:

- `reporting_periods`;
- `metrics_catalog`;
- `metric_observations`.

These are not required for the current Key Rate Analyzer and should not be forced into the first migration set without stable data sources.

## Open Questions

- How much official index data is needed before market benchmark comparison is safe?
- Should sector membership be event-date-aware in the UI?
- Should `trading_calendar` become mandatory for stronger coverage checks?
- How should corporate actions/dividends be reflected in future price interpretation?
