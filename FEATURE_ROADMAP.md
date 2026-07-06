# FinLab Feature Roadmap

This roadmap describes the current product direction. It should be updated as the repository changes.

FinLab is in active development. Items below are grouped by current status, not by marketing priority.

## Already Implemented

Core dashboard:

- MOEX ISS market data integration.
- Ticker model and latest price storage.
- Watchlist management.
- One-ticker price refresh.
- Batch watchlist price refresh.
- Market Chart.
- Price alerts.
- Alert events/history.
- Soft delete for alerts.
- Anonymous demo sessions.
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
- Docker Compose startup with backend/frontend/PostgreSQL.
- Backend Docker startup with migrations and key-rate decision import.

Analytics foundation:

- Reference layer: instruments, issuers, sectors, issuer sector history.
- Market data layer: persisted daily prices in `price_candles`.
- Generic events layer.
- Study runs, event results, horizon summaries and skipped events.
- Key-rate decisions database and CSV importer.
- Key-rate events importer into the generic events layer.
- Event-study backend engine using event-close returns.
- Current Key Rate Analyzer endpoint: `POST /api/v1/hypotheses/key-rate-impact/v2`.
- Event direction filter: all / hike / cut / hold.
- Main UI horizons: 1 / 5 / 10 trading days.
- Used/skipped events.
- Peer-based sector comparison.
- Data coverage check and selected-ticker missing-tail import.

## In Development

Main active direction:

- Stabilizing Key Rate Analyzer for demo and merge.
- Documentation and repository presentation.
- Manual validation on real imported key-rate decisions and MOEX prices.
- UI polish around result readability and limitations.

Important note:

The `key_rate_decisions` table is intended for official/imported historical decisions. It should not be populated with fake sample data.

## Nearest Priority

The current Key Rate Analyzer answers:

> How did one selected stock historically change after similar key-rate decisions?

Near-term tasks:

- Keep README and documentation aligned with the implemented analyzer.
- Validate demo scenarios after importing the curated dataset.
- Improve result explanations and limitations where UI still feels too technical.
- Improve frontend component decomposition.
- Add stronger diagnostics for data coverage/readiness.

## Later

Market and UX:

- Better Market Chart hover/tooltip behavior.
- More chart annotations.
- Cleaner diagnostics for external data failures.
- UI screenshots after stabilization.

Analytics:

- Filter key-rate decisions by change size.
- Distinguish expected vs unexpected decisions if reliable data exists.
- Add other market event types.
- Add saved study history.
- Add confidence/data-quality scoring after enough historical data is available.
- Add market benchmark / IMOEX only after proper index instrument data is available.

Product extensions:

- Portfolio tracker.
- Risk/analyzer module.
- Hypothesis-based alerts.
- Reports/export.
- Telegram/email notifications.

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
- Full production hardening before the main analysis flow is stable.
