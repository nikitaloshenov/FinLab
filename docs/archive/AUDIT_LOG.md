# FinLab Audit Log

Historical/internal notes for important audits and product/engineering decisions.

This file is not the main public documentation. For current project overview use `README.md`, `docs/ARCHITECTURE.md` and `docs/DEMO_SCRIPT.md`.

## 2026-06-03 - Documentation and Product Direction Audit

### Context

Reviewed the repository direction after the project evolved from Market Watchlist & Alerts toward hypothesis-driven market analysis.

### Findings

- FinLab already had a working market dashboard foundation: MOEX integration, watchlist, latest prices, market chart, price alerts, alert events, backend tests and CI.
- The strongest product direction was historical event analysis.
- The `key_rate_decisions` table was the correct foundation for imported historical key-rate decisions.
- Static/sample key-rate events should not be presented as official data.

### Decisions

- README should stay presentation-focused and honest.
- Detailed product/data logic should live in dedicated spec docs.
- `PROJECT_CONTEXT.md` should remain the main working context for future development tasks.

## 2026-06-06 - Key Rate Impact Analyzer MVP Completion Audit

### Context

Reviewed the repository after the first Key Rate Impact Analyzer MVP was implemented on top of curated key-rate decisions, MOEX data and Hypothesis Lab UI.

### Implemented At That Point

- Curated historical key-rate decisions dataset and CSV importer.
- `key_rate_decisions` database table and read API.
- Legacy endpoint `POST /api/v1/hypotheses/key-rate-impact/analyze`.
- Event-close logic over trading-day horizons.
- Summary, confidence, best horizon, skipped summary and horizon table.
- MOEX long-range candle fetching improvements.

### Decisions

- The analyzer must use the first trading price with date `>= decision_date` as the event price.
- Missing event or horizon data must be skipped and must not be treated as `0%` returns.
- The analyzer must remain historical analysis, not a forecast and not financial advice.

## 2026-07-06 - Key Rate Analyzer Current Flow And Data Coverage

### Context

Reviewed documentation after the current Key Rate Analyzer frontend cutover and backend data coverage fix.

### Current State

- Current frontend calls `POST /api/v1/hypotheses/key-rate-impact/v2`.
- Main UI horizons are 1, 5 and 10 trading days.
- Event direction filter supports all / hike / cut / hold.
- Results include used/skipped events.
- Sector comparison is peer-based and not an official sector index.
- Analyzer uses persisted analytics daily prices in `price_candles`.
- Market Chart may use a separate MOEX chart flow.

### Data Coverage Decision

The analyzer should not treat a selected period as ready when `price_candles` contains only the beginning of that period.

Current expected behavior:

- check both start and end coverage for selected instrument daily prices;
- if the tail is missing, import the missing selected-ticker range;
- if data remains unavailable, keep affected events/horizons skipped with readable reasons;
- never substitute missing returns with fake zero.

### Remaining Risks

- Data readiness is still MVP-level and not a full exchange-calendar completeness audit.
- Frontend analyzer components can be decomposed further.
- Demo validation should keep checking realistic scenarios such as SBER/SBERP/FLOT for 2024-2026.
