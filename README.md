# FinLab

FinLab is a backend-oriented fullstack fintech project for historical analysis of market hypotheses on the Russian equity market.

- Live demo: https://jirniydizainer.ru
- Swagger API: https://jirniydizainer.ru/docs
- GitHub: https://github.com/nikitaloshenov/FinLab

FinLab is not financial advice, not an investment recommendation and not a production trading system.

## What FinLab Does

FinLab started as a MOEX market dashboard with a watchlist, latest prices, market chart and price alerts. It is now evolving into a hypothesis-driven analysis tool.

The main showcase feature is **Анализ реакции на решения ЦБ**: an event-study module that shows how selected MOEX stocks historically changed after Bank of Russia key-rate decisions.

## Current Project Status

- Legacy dashboard features are still available: Market Chart, Watchlist, Price Alerts and Alert Events.
- The analytics layer is the main development direction.
- Key Rate Analyzer is the main portfolio/showcase feature.
- The project is production-like as a pet project, but it is not production-ready financial software.

## Key Rate Analyzer

The analyzer answers:

> How did a selected stock historically change after similar key-rate decisions?

Current user flow:

1. Choose a MOEX stock.
2. Choose decision type: all decisions, rate hikes, rate cuts or rate holds.
3. Choose a year range.
4. Analyze returns after 1, 5 and 10 trading days.
5. Optionally compare the stock with companies from the same sector.

The backend uses:

- imported historical key-rate decisions;
- persisted analytics daily prices in `price_candles`;
- reference data for instruments, issuers and sectors;
- an event-study engine that stores study runs, event results and horizon summaries.

Methodology:

- event price = close of the first daily price row with `trading_date >= event_date`;
- horizon return = close after N trading days divided by event price minus 1;
- missing event or horizon prices are skipped, not replaced with zero;
- fresh events can be skipped when there are not enough following daily prices yet.

The UI shows:

- verdict;
- KPI cards;
- horizon summary table;
- used/skipped events;
- peer-based sector comparison;
- compact data quality details.

## Data Sources

- MOEX ISS API for market data.
- Curated key-rate decisions dataset imported from CSV.
- Reference tables for instruments, issuers, sectors and sector history.

The analyzer uses persisted analytics data from `price_candles`. The market chart can use a separate MOEX chart flow. This separation is intentional: the chart is a monitoring view, while the analyzer needs reproducible historical data.

The project does not scrape Central Bank or news websites and does not present sample data as official data.

## Why This Project Is Interesting Technically

- FastAPI backend with modular routers/services/repositories/schemas.
- SQLAlchemy models and Alembic migrations.
- PostgreSQL persistence.
- Analytics layer: reference data, events, daily prices, study runs and study results.
- Event-study engine over trading-day horizons.
- MOEX data ingestion and CSV importers.
- Structured API errors.
- Backend unit/API tests with pytest.
- React/Vite frontend for demo and product presentation.
- Docker Compose startup with migrations and data import.
- GitHub Actions CI.

## Main Features

- MOEX Market Chart.
- Watchlist with anonymous demo sessions.
- Latest price refresh.
- Price alerts and alert event history.
- Key Rate Analyzer.
- Peer-based sector comparison.
- Swagger API.
- Dockerized local/demo setup.

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

Hypotheses / analytics:

- `POST /api/v1/hypotheses/key-rate-impact/v2` - current Key Rate Analyzer endpoint.
- `GET /api/v1/hypotheses/key-rate-decisions`
- `GET /api/v1/hypotheses/key-rate-events`
- `POST /api/v1/hypotheses/analyze` - legacy hypothesis endpoint.
- `POST /api/v1/hypotheses/key-rate-impact/analyze` - legacy key-rate analyzer endpoint.

## Local Run With Docker Compose

```powershell
git clone https://github.com/nikitaloshenov/FinLab.git
cd FinLab
docker compose up --build
```

Local URLs:

- Frontend: http://127.0.0.1:5173
- Backend: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs

On backend startup Docker Compose waits for PostgreSQL, runs Alembic migrations and imports the curated key-rate decisions dataset from `backend/app/data/key_rate_decisions_official.csv`. The importer uses upsert, so repeated startup should not duplicate decisions.

### Docker Persistence

PostgreSQL stores data in the named volume `finlab_postgres_data`.

```powershell
docker compose down
```

Stops containers but keeps database data. Watchlist, alerts and imported decisions remain available after the next startup.

```powershell
docker compose down -v
```

Stops containers and removes the volume. This resets the database: watchlist and alerts become empty. On the next startup backend runs migrations and imports key-rate decisions again.

## Demo Deploy

Demo URLs:

- Frontend: https://jirniydizainer.ru
- Backend API: https://jirniydizainer.ru/api/v1
- Swagger: https://jirniydizainer.ru/docs

Production/demo frontend should use a relative API base behind reverse proxy:

```env
VITE_API_BASE_URL=/api/v1
```

If frontend and backend are served from different origins, backend CORS is configured with:

```env
BACKEND_CORS_ORIGINS=https://jirniydizainer.ru,https://www.jirniydizainer.ru
```

## Continuous Deployment

GitHub Actions deploys the project after a successful push to `main`. The same workflow can be started manually with `workflow_dispatch`.

Workflow:

- runs backend tests;
- runs frontend production build;
- SSHes into the server;
- updates `/opt/finlab` to `origin/main`;
- builds and starts Docker Compose with `docker-compose.yml` and `docker-compose.prod.yml`;
- runs Alembic migrations and reference seed;
- checks the public health endpoint.

Required GitHub Secrets:

- `CD_SSH_HOST`
- `CD_SSH_USER`
- `CD_SSH_PORT`
- `CD_SSH_PRIVATE_KEY`
- `CD_DEPLOY_PATH`
- `CD_HEALTHCHECK_URL`

Production `.env` and SSH keys live outside the repository and must not be committed.

## Local Run Without Docker

Backend:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
alembic upgrade head
python scripts/import_key_rate_decisions.py --file app/data/key_rate_decisions_official.csv
python -m uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

## Tests

Backend:

```powershell
cd backend
python -m pytest
```

Frontend build:

```powershell
cd frontend
npm run build
```

Backend tests cover watchlist, alerts, sessions, MOEX client, importers, key-rate decisions, event-study logic, Key Rate Analyzer API and sector comparison.

## Limitations

- FinLab is a research/demo tool, not trading advice.
- Historical reactions do not prove causality and do not guarantee future market behavior.
- Results depend on the quality and completeness of daily prices.
- Fresh events can be skipped if there are not enough subsequent prices for selected horizons.
- Sector comparison is peer-based and does not represent an official sector index.
- Market benchmark / IMOEX comparison is not part of the current UI flow.
- Data readiness logic is still MVP-level, although the analyzer can detect stale coverage and import the missing selected-ticker range on demand.
- Frontend automated tests are currently limited; backend tests are the stronger part of the project.
- Anonymous demo sessions are not a replacement for full user authentication.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Demo script](docs/DEMO_SCRIPT.md)
- [Interview notes](docs/INTERVIEW_NOTES.md)
- [Technical specs](docs/specs/)
- [Historical/internal notes](docs/archive/AUDIT_LOG.md)

## Roadmap Ideas

- Better frontend component decomposition.
- Stronger diagnostics for data readiness and skipped events.
- Saved hypotheses and study history.
- More event-study analyzers after Key Rate Analyzer is stable.
- Optional caching for repeated MOEX/data requests.
- Full auth/users if the demo evolves into a hosted product.

## Author

Nikita Loshchenov

- GitHub: https://github.com/nikitaloshenov/FinLab
- Telegram: https://t.me/JIRNIYDIZAINER
