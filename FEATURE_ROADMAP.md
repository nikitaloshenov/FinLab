# FinLab Feature Roadmap

This roadmap describes the current product direction. It should be updated as the repository changes.

FinLab is in active development. Items below are grouped by current status, not by marketing priority.

## Already Implemented

Core market dashboard:

- MOEX ISS market data integration.
- Ticker model and latest price storage.
- Watchlist management.
- One-ticker price refresh.
- Batch watchlist price refresh.
- Market Chart based on MOEX candles.
- Price alerts.
- Alert events/history.
- Soft delete for alerts.
- Structured API errors.
- Backend logging.
- React/Vite dashboard UI.

Backend and infrastructure:

- FastAPI backend.
- PostgreSQL database.
- SQLAlchemy models and repositories.
- Alembic migrations.
- Backend unit tests.
- API integration tests with FastAPI TestClient.
- GitHub Actions CI.
- Pinned direct dependencies.
- Docker Compose for PostgreSQL.
- Development script for Docker/PostgreSQL startup.

Hypotheses foundation:

- Hypothesis Lab MVP UI.
- Single-event hypothesis analysis endpoint.
- Static MVP key rate events sample layer.
- Key rate decisions database foundation.
- Read API for key rate decisions.
- Curated key rate decisions CSV dataset.
- CSV importer with dry-run/upsert flow.
- Key Rate Impact Analyzer MVP.
- Event-study backend engine using event-close returns.
- Optional benchmark comparison.
- MOEX candles pagination and yearly chunking for long ranges.

## In Development

Main active direction:

- Stabilizing the Key Rate Impact Analyzer MVP for demo and merge.
- Documentation and repository presentation.
- Manual validation on real imported key rate decisions and MOEX candles.
- UI polish around result readability and limitations.

Important note:

The `key_rate_decisions` table is intended for official/imported historical decisions. It should not be populated with fake sample data.

## Nearest Priority

The current Key Rate Impact Analyzer MVP answers:

> How did one selected stock historically react to similar key rate decisions?

Near-term tasks:

- Keep README and documentation aligned with the implemented analyzer.
- Validate demo scenarios after importing the curated dataset.
- Improve result explanations and limitations where UI still feels too technical.
- Add cache/performance strategy for repeated candles and analyzer requests.

## Later

Market and UX:

- Better Market Chart hover/tooltip behavior.
- More chart annotations.
- Cleaner diagnostics for external data failures.
- UI screenshots after stabilization.

Analytics:

- Filter key rate decisions by change size.
- Distinguish expected vs unexpected decisions if reliable data exists.
- Add other market event types.
- Add sector/basket analysis as secondary context.
- Add confidence scoring after enough historical data is available.

Product extensions:

- Portfolio tracker.
- Risk/analyzer module.
- Hypothesis-based alerts.
- Reports/export.
- Telegram/email notifications.
- Deployment/demo environment.

Long-term ideas:

- More advanced backtesting.
- Deeper benchmark comparison.
- Possible data science or ML extensions after enough clean historical data and domain understanding.

## Not Planned Right Now

These would add complexity before the core product is stable:

- Kubernetes.
- Kafka.
- Microservices.
- Complex auth/RBAC.
- Celery/Redis before a clear background processing need.
- UI framework migration.
- Production deployment before the main analysis flow is stable.
