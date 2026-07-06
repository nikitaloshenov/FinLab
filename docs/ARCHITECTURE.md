# FinLab Architecture Summary

FinLab is a fullstack fintech/event-study project with a FastAPI backend, PostgreSQL database and React/Vite frontend.

## High-Level Flow

```text
Frontend -> API client -> FastAPI routers -> services -> repositories -> PostgreSQL
                                                       -> MOEX ISS API
```

## Product Layers

FinLab currently has two product layers.

### Legacy Dashboard Layer

These modules come from the original market dashboard:

- `market`
  - ticker lookup;
  - latest price refresh;
  - MOEX chart endpoint.
- `watchlist`
  - anonymous-session watchlist;
  - add/remove tickers;
  - manual batch refresh of latest prices.
- `alerts`
  - price alert CRUD;
  - manual/batch alert checks;
  - soft delete alerts;
  - alert event history.

These features remain useful for the demo, but they are no longer the main architectural direction.

### Analytics Layer

The analytics layer is the current main direction:

- `reference`
  - instruments;
  - issuers;
  - sectors;
  - issuer sector history;
  - benchmark/reference entities.
- `market_data`
  - persisted daily prices in `price_candles`;
  - candle ingestion;
  - source/provenance-oriented market data storage.
- `events`
  - generic event types;
  - key-rate decision events;
  - imported event records used by event-study.
- `studies`
  - study runs;
  - event-level results;
  - horizon summaries;
  - skipped events;
  - event-study engine.
- `hypotheses`
  - public API orchestration for Key Rate Analyzer;
  - request/response schemas;
  - data preparation;
  - sector comparison assembly.

## Key Rate Analyzer Flow

Current endpoint:

```text
POST /api/v1/hypotheses/key-rate-impact/v2
```

Flow:

```text
normalize request
  -> resolve selected instrument
  -> load/import key-rate decision events
  -> check selected instrument daily-price coverage
  -> import missing selected-instrument price range if needed
  -> run event-study over persisted daily prices
  -> build used/skipped events
  -> optionally compare with sector peers
  -> return verdict data for frontend
```

Main UI horizons are 1, 5 and 10 trading days.

## Market Chart vs Analyzer Data

The market chart and analyzer intentionally have different data flows:

- Market Chart is a monitoring UI and can request MOEX chart data directly.
- Key Rate Analyzer is a historical analysis module and uses persisted analytics data from `price_candles`.

This means a chart can display market data while the analyzer still needs to prepare or backfill `price_candles`. The analyzer now checks both start and end coverage for the selected period. If the database contains only the beginning of the range, it imports the missing tail for the selected `secid`. If data still cannot be calculated, events/horizons are skipped with a readable reason instead of using fake zero returns.

## Frontend Structure

Important frontend files:

- `frontend/src/features/hypotheses/HypothesisLabSection.jsx`
  - form state;
  - selected stock, event direction, year range, horizons;
  - request payload construction;
  - analyze button and loading/error state.
- `frontend/src/features/hypotheses/HypothesisResultPanel.jsx`
  - verdict;
  - KPI cards;
  - horizon table;
  - sector comparison;
  - used/skipped events;
  - data quality details.
- `frontend/src/features/hypotheses/api.js`
  - calls the current Key Rate Analyzer endpoint.

## Important Engineering Choices

- Daily prices are used for event-study, not latest price or intraday chart data.
- Missing event/horizon data is skipped, not converted to zero.
- Sector comparison uses peer companies from reference data, not an official sector index.
- Anonymous demo sessions are used for watchlist/alerts, not full authentication.
- Docker startup runs migrations and imports key-rate decisions for demo readiness.

## Known Architecture Trade-Offs

- Legacy market/watchlist/alerts and analytics modules coexist.
- Data readiness checks are still MVP-level, although stale-tail coverage is now detected.
- Frontend analyzer components are functional but can be decomposed further.
- Demo deploy is production-like, not production-grade.
