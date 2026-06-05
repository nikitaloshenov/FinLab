# FinLab Project Context

FinLab is a production-like fullstack fintech pet project in active development.

The project started as a MOEX market monitoring dashboard with watchlists, latest prices, market charts and price alerts. It is now gradually evolving into a hypothesis-driven market analysis tool based on historical market data.

FinLab is not financial advice, not an investment recommendation and not production-ready yet.

## Current Product Direction

The current main development focus is the Key Rate Impact Analyzer MVP and its demo/readiness polish.

The target product question is:

> How did a selected stock historically react to similar key rate decisions?

The implemented MVP moves from a single-event candle-window analysis toward a multi-event event-study flow:

- choose one stock;
- choose a key rate scenario: `rate_cut`, `rate_hike` or `rate_hold`;
- optionally choose a benchmark;
- analyze similar historical key rate decisions;
- compare returns over 1, 3 and 10 trading days in the main frontend flow.

The Key Rate Impact Analyzer MVP is implemented. It uses curated/imported historical key rate decisions from the `key_rate_decisions` table and MOEX daily candles. The current calculation uses event-close logic:

- event candle = first trading candle with date `>= decision_date`;
- event price = close of that event candle;
- horizon return = close after N trading days divided by event price minus 1;
- missing event or horizon candles are skipped, not treated as zero returns.

The analyzer returns `summary`, `confidence`, `best_horizon`, `skipped_summary`, `horizon_summary` and optional `event_results`. It remains historical analysis, not a forecast.

Related specs:

- `KEY_RATE_ANALYZER_SPEC.md` describes the intended analyzer product logic.
- `KEY_RATE_DATASET_SPEC.md` describes the dataset strategy for historical key rate decisions.

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
- Dashboard UI

Infrastructure:

- Docker Compose for PostgreSQL
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
    hypotheses/
```

Architecture principles:

- `router.py` is the HTTP API layer.
- `service.py` contains business logic.
- `repository.py` contains database access.
- `schemas.py` contains Pydantic request/response models.
- `models.py` contains SQLAlchemy models.
- external clients contain integration code, for example MOEX ISS access.

Avoid placing business logic directly in routers unless it is very small and endpoint-specific.

## Current Backend Modules

### Market

Responsible for tickers, latest prices and MOEX candles.

Important behavior:

- fetch ticker data from MOEX ISS;
- create ticker records when needed;
- update `ticker_latest_prices`;
- serve Market Chart candles directly from MOEX through:
  - `GET /api/v1/market/tickers/{secid}/candles`

PostgreSQL stores product state, not market candles. Historical candles are currently requested from MOEX.

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

### Hypotheses

Responsible for hypothesis/event analysis.

Current state:

- `POST /api/v1/hypotheses/analyze` exists and must not be changed casually;
- static MVP key rate events exist as a legacy/sample layer;
- `key_rate_decisions` database table exists for official/imported key rate decisions;
- `GET /api/v1/hypotheses/key-rate-decisions` reads the DB table and returns an empty list if no data has been imported.
- `POST /api/v1/hypotheses/key-rate-impact/analyze` runs the Key Rate Impact Analyzer MVP over imported decisions and MOEX candles.

Do not present sample events as official data.

## Database State

Current product tables include:

- `tickers`
- `ticker_latest_prices`
- `watchlist_items`
- `alerts`
- `alert_events`
- `key_rate_decisions`
- `alembic_version`

The old saved `prices` history table has been removed. Market Chart uses MOEX candles directly.

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
- Market Chart based on MOEX candles;
- Price Alerts;
- Alert Events;
- Hypothesis Lab UI;
- structured API error parsing.

The frontend is a working MVP and may change while the Key Rate Impact Analyzer is stabilized.

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
- MOEX candles parsing/API contract;
- soft delete alerts;
- hypotheses blueprints/report composer/historical validation;
- key rate events sample layer;
- key rate decisions repository/API foundation.

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

- official/imported Historical Key Rate Decisions Dataset;
- Key Rate Impact Analyzer;
- transition from a dashboard/watchlist app toward historical event analysis;
- documentation and repository presentation;
- better tests around the new analyzer flow.
