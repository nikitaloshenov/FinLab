# FinLab Project Context

FinLab is a production-like fullstack fintech pet project in active development.

The project started as a MOEX market monitoring dashboard with watchlists, latest prices, market charts and price alerts. It is now evolving into a hypothesis-driven market analysis tool based on historical market data.

FinLab is not financial advice, not an investment recommendation and not production-ready financial software.

## Current Product Direction

The current main showcase feature is **Анализ реакции на решения ЦБ** / Key Rate Analyzer.

The product question is:

> How did a selected stock historically change after similar Bank of Russia key-rate decisions?

Current implemented flow:

- choose one MOEX stock;
- choose decision type: all / hike / cut / hold;
- choose year range;
- analyze historical reaction after 1, 5 and 10 trading days;
- optionally compare with companies from the same sector;
- show used/skipped events and data quality details.

This is historical analysis, not a forecast.

## Current Analyzer Data Flow

The current frontend calls:

```text
POST /api/v1/hypotheses/key-rate-impact/v2
```

The analyzer uses:

- imported key-rate decisions;
- generic `events` layer;
- persisted analytics daily prices in `price_candles`;
- event-study engine over trading-day horizons;
- optional peer-based sector comparison.

Calculation logic:

- event price = close of the first daily price row with `trading_date >= event_date`;
- horizon price = close after N trading days from the event price row;
- return = `horizon_price / event_price - 1`;
- missing event/horizon prices are skipped, not treated as zero.

Data coverage behavior:

- Market Chart may use a separate MOEX chart flow.
- Key Rate Analyzer uses persisted `price_candles`.
- If `price_candles` contains only the beginning of the selected range, the analyzer should import the missing selected-ticker tail before running.
- If data is still unavailable, events/horizons remain skipped with readable reasons.

## Tech Stack

Backend:

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Pytest
- httpx
- MOEX ISS API integration

Frontend:

- React
- Vite
- JavaScript
- CSS
- API integration with the backend
- Product/demo UI

Infrastructure:

- Docker Compose
- GitHub Actions CI
- Root `.env.example`
- Branch workflow: `main`, `develop`, `feature/*`

## Backend Structure

```text
backend/app/
  core/
    config.py
    database.py
    logging.py
  shared/
    errors.py
  modules/
    market/
    watchlist/
    alerts/
    reference/
    market_data/
    events/
    studies/
    hypotheses/
```

Architecture principles:

- `router.py` is the HTTP API layer.
- `service.py` contains business/application logic.
- `repository.py` contains database access.
- `schemas.py` contains Pydantic request/response models.
- `models.py` contains SQLAlchemy models.
- external clients contain integration code, for example MOEX ISS access.

Avoid placing business logic directly in routers unless it is very small and endpoint-specific.

## Current Backend Modules

### Market

Responsible for legacy ticker/latest-price behavior and Market Chart MOEX candles.

Important behavior:

- fetch ticker data from MOEX ISS;
- create ticker records when needed;
- update `ticker_latest_prices`;
- serve Market Chart candles through `GET /api/v1/market/tickers/{secid}/candles`.

### Watchlist

Responsible for the user's tracked tickers.

Important endpoints:

- `GET /api/v1/watchlist`
- `POST /api/v1/watchlist/items`
- `DELETE /api/v1/watchlist/items/{secid}`
- `POST /api/v1/watchlist/refresh-prices`

Batch refresh should continue working when one ticker fails and should return item-level details.

### Alerts

Responsible for price alerts and alert event history.

Important behavior:

- alerts can be checked manually or in batch;
- triggered alerts create `AlertEvent`;
- alert deletion uses soft delete;
- alert events should remain as history.

### Analytics Modules

Current analytics modules:

- `reference`: instruments, issuers, sectors, sector history, data sources.
- `market_data`: persisted daily prices in `price_candles`, ingestion runs.
- `events`: generic event types and key-rate decision events.
- `studies`: event-study runs, event results, horizon summaries and skipped events.
- `hypotheses`: API orchestration for Key Rate Analyzer and legacy hypothesis endpoints.

Do not present sample/dev events as official data.

## Database State

Current product/analytics tables include:

- `tickers`
- `ticker_latest_prices`
- `watchlist_items`
- `alerts`
- `alert_events`
- `key_rate_decisions`
- `issuers`
- `instruments`
- `sectors`
- `issuer_sector_history`
- `data_sources`
- `price_candles`
- `ingestion_runs`
- `event_types`
- `events`
- `event_values`
- `event_targets`
- `study_runs`
- `study_run_events`
- `study_event_results`
- `study_horizon_summary`
- `study_skipped_events`
- `alembic_version`

The old saved `prices` history table has been removed. Market Chart uses MOEX chart data, while the analyzer uses analytics `price_candles`.

Use `Decimal` for prices and rates. Avoid floats for financial values.

## Frontend Structure

```text
frontend/src/
  main.jsx
  App.jsx
  pages/
    MarketPage.jsx
  features/
    market/
    watchlist/
    alerts/
    hypotheses/
  shared/
    api/
    lib/
  styles.css
```

Current frontend capabilities:

- Market Overview dashboard section;
- Watchlist;
- Market Chart;
- Price Alerts;
- Alert Events;
- Hypothesis Lab / Key Rate Analyzer UI;
- structured API error parsing.

## API and Error Handling

Backend API uses FastAPI routers under `/api/v1`.

Domain/API errors should use the structured format:

```json
{
  "detail": {
    "code": "some_error_code",
    "message": "Human readable message",
    "details": {}
  }
}
```

FastAPI validation errors (`422`) remain standard.

## Testing and CI

Backend tests cover:

- alert condition logic;
- batch behavior;
- MOEX retry/invalid JSON handling;
- market candles parsing/API contract;
- soft delete alerts;
- key-rate decision importers;
- reference data;
- market data importer;
- event-study logic;
- Key Rate Analyzer API;
- sector comparison;
- data coverage/readiness behavior.

GitHub Actions CI runs backend tests and frontend build.

Workflow triggers:

- push to `main`;
- push to `develop`;
- push to `feature/**`;
- pull requests to `main` or `develop`;
- manual `workflow_dispatch`.

## Branch Workflow

- `main` is the stable branch.
- `develop` is the working integration branch.
- `feature/*` branches are used for larger features.

## Important Constraints

Do not break without a dedicated task:

- existing backend module structure;
- existing API contracts;
- migrations;
- CI workflow;
- current dashboard behavior;
- current frontend layout;
- tests;
- `.env`, `.venv`, `node_modules`.

Do not add:

- fake official data;
- web scraping;
- real CBR/news requests without a separate task;
- production claims;
- financial advice wording.

## Current Development Focus

Near-term focus:

- documentation and repository presentation;
- demo validation for Key Rate Analyzer;
- data coverage/readiness hardening;
- frontend decomposition and result readability;
- future macro-event analyzers only after the current analyzer is stable.
