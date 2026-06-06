# FinLab

FinLab is a production-like fullstack fintech pet project for monitoring MOEX securities, managing watchlists and price alerts, and evolving into a hypothesis-driven market analysis tool based on historical data.

The project started as a Market Watchlist & Alerts dashboard and now includes a Key Rate Impact Analyzer MVP: a tool for studying how selected stocks historically reacted to similar key rate decisions.

## Project Status

- Active development.
- Backend and frontend MVP are working.
- Not production-ready yet.
- Not financial advice and not an investment recommendation.
- Screenshots will be added after UI stabilization.

## Why This Project Exists

FinLab is built to show more than a simple CRUD dashboard. The goal is to combine market monitoring with historical hypothesis validation:

- monitor MOEX securities;
- keep a personal watchlist;
- refresh latest prices;
- track price alerts;
- inspect market candles;
- analyze historical stock reactions to market or macro events.

## Current Features

- MOEX ISS market data integration.
- Watchlist management.
- Latest price refresh for one ticker or the whole watchlist.
- Market Chart based on MOEX candles.
- Price alerts.
- Alert events/history.
- Hypothesis Lab foundation.
- Key Rate Impact Analyzer MVP.
- Curated historical key rate decisions dataset and CSV importer.
- Key rate decisions database table.
- FastAPI backend API.
- PostgreSQL persistence.
- Alembic migrations.
- React/Vite frontend.
- Backend unit and API integration tests.
- GitHub Actions CI.
- Branch workflow: `main`, `develop`, `feature/*`.

## Main Development Direction

The current product direction is the Key Rate Impact Analyzer.

Current MVP question:

> How did a selected stock historically react to similar key rate decisions?

Current MVP analysis flow:

- choose one stock;
- choose a key rate scenario: rate cut, rate hike or rate hold;
- analyze similar historical decisions;
- compare horizons: 1, 3 and 10 trading days;
- optionally compare with a benchmark;
- show a human-readable conclusion and limitations.

The analyzer uses imported curated key rate decisions and MOEX daily candles. For each decision, it uses the first trading candle on or after `decision_date` as the event candle, then compares the event close with closes after the selected trading-day horizons. Missing candles are skipped, not treated as zero returns.

This is historical analysis, not a forecast and not financial advice.

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
- Backend API integration
- Dashboard UI

Infrastructure:

- Docker Compose for PostgreSQL
- GitHub Actions CI
- Root `.env.example`

## Architecture

Backend modules follow a simple layered structure:

- `router.py` - HTTP endpoints.
- `service.py` - business logic.
- `repository.py` - database access.
- `schemas.py` - Pydantic request/response schemas.
- `models.py` - SQLAlchemy models.
- external clients - integration with outside APIs such as MOEX ISS.

Main backend modules:

- `market`
- `watchlist`
- `alerts`
- `hypotheses`

Frontend is organized around a dashboard page and feature-level sections for market data, watchlist, alerts and hypotheses.

## API Overview

Health:

- `GET /api/v1/health`
- `GET /api/v1/health/db`

Market:

- `GET /api/v1/market/tickers`
- `GET /api/v1/market/tickers/{secid}/moex`
- `POST /api/v1/market/tickers/{secid}/refresh`
- `GET /api/v1/market/tickers/{secid}/price`
- `GET /api/v1/market/tickers/{secid}/candles`

Watchlist:

- `GET /api/v1/watchlist`
- `POST /api/v1/watchlist/items`
- `DELETE /api/v1/watchlist/items/{secid}`
- `POST /api/v1/watchlist/refresh-prices`

Alerts:

- `GET /api/v1/alerts`
- `POST /api/v1/alerts`
- `POST /api/v1/alerts/{alert_id}/check`
- `POST /api/v1/alerts/check-active`
- `DELETE /api/v1/alerts/{alert_id}`
- `GET /api/v1/alerts/events`

Hypotheses:

- `POST /api/v1/hypotheses/analyze`
- `GET /api/v1/hypotheses/key-rate-events`
- `GET /api/v1/hypotheses/key-rate-decisions`
- `POST /api/v1/hypotheses/key-rate-impact/analyze`

## Run with Docker Compose

From the repository root:

```powershell
docker compose up --build
```

Local URLs:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Swagger: http://localhost:8000/docs

On backend startup Docker Compose waits for PostgreSQL, runs Alembic migrations and imports the curated key rate decisions dataset from `backend/app/data/key_rate_decisions_official.csv`. The importer uses upsert logic, so repeated local starts should not duplicate decisions.

This setup is intended for local development/demo, not production deployment.

## Local Setup

Create a backend env file from the root template:

```powershell
cd backend
Copy-Item ..\.env.example .\.env
```

Start PostgreSQL:

```powershell
docker compose up -d postgres
```

Or use the helper script from the project root:

```powershell
.\scripts\start-dev.ps1
```

Run backend:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --reload
```

Run frontend:

```powershell
cd frontend
npm install
npm run dev
```

Local URLs:

- Backend: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- Frontend: http://localhost:5173

## Tests

```powershell
cd backend
python -m pytest
```

CI also runs backend tests and frontend build.

## Documentation

- [Project Context](PROJECT_CONTEXT.md)
- [Feature Roadmap](FEATURE_ROADMAP.md)
- [Key Rate Analyzer Spec](KEY_RATE_ANALYZER_SPEC.md)
- [Key Rate Dataset Spec](KEY_RATE_DATASET_SPEC.md)
- [Audit Log](AUDIT_LOG.md)

## Engineering Focus

This project demonstrates:

- backend API design;
- modular FastAPI architecture;
- SQLAlchemy models and repositories;
- Alembic migrations;
- external market data integration;
- error handling and validation;
- backend testing;
- CI setup;
- frontend-backend integration;
- product-oriented development around financial market data.

## Limitations

- The project is in active development.
- It is not production-ready.
- It has no authentication yet.
- It depends on external market data availability.
- It should not be used for real trading decisions.
- UI and analysis flows may change.
- No public deployment URL is provided yet.

## For Employers

FinLab demonstrates the ability to design and develop a backend-focused fullstack application with real external data, database persistence, API design, migrations, testing, CI, frontend integration and a clear product development direction.
