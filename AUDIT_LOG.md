# FinLab Audit Log

Short log of important audits and product/engineering decisions.

## 2026-06-03 - Documentation and Product Direction Audit

### Context

Reviewed the current repository direction after the project evolved from Market Watchlist & Alerts toward hypothesis-driven market analysis.

### Findings

- FinLab already has a working market dashboard foundation: MOEX integration, watchlist, latest prices, market candles, price alerts, alert events, backend tests and CI.
- The strongest current product direction is the Key Rate Impact Analyzer.
- The analyzer should focus on one selected stock and multiple historical key rate decisions, not on one manually selected event.
- The `key_rate_decisions` table is the correct foundation for official/imported historical key rate decisions.
- The static key rate events layer is MVP/sample legacy context and should not be presented as official data.

### Risks

- The project can look like a generic dashboard if the hypothesis/event analysis direction is not clearly documented.
- Sample events may be misunderstood as official data unless documentation is explicit.
- At that time, the final analyzer flow was incomplete, so README needed to avoid overclaiming. This has since been addressed by the Key Rate Impact Analyzer MVP.

### Recommended Next Steps

- Import official historical key rate decisions into the database.
- Keep the multi-event Key Rate Impact Analyzer logic aligned with the dataset and current event-close MVP.
- Add tests around historical event-study calculations.
- Keep README concise and move detailed product logic to dedicated documentation.

### Decisions

- README should stay presentation-focused and honest.
- `KEY_RATE_ANALYZER_SPEC.md` should contain the detailed product logic.
- `FEATURE_ROADMAP.md` should separate implemented, in-development and future work.
- `PROJECT_CONTEXT.md` should remain the main working context for future development tasks.

## 2026-06-06 - Key Rate Impact Analyzer MVP Completion Audit

### Context

Reviewed the repository after the Key Rate Impact Analyzer MVP was implemented on top of curated key rate decisions, MOEX candles and the Hypothesis Lab UI.

### Implemented

- Curated historical key rate decisions dataset and CSV importer.
- `key_rate_decisions` database table and read API.
- `POST /api/v1/hypotheses/key-rate-impact/analyze`.
- Event-study backend engine with event-close logic.
- Horizons 1, 3 and 10 trading days in the main frontend flow.
- Optional benchmark comparison.
- Summary, confidence, best horizon, skipped summary, horizon table and optional event details.
- MOEX candles pagination and yearly chunking for long historical ranges.

### Decisions

- The MVP uses the first trading candle with date `>= decision_date` as the event candle.
- Returns are calculated from close of the event candle to close after the selected trading-day horizon.
- Missing event or horizon candles are skipped and must not be treated as `0%` returns.
- The analyzer must remain historical analysis, not a forecast and not financial advice.

### Remaining Risks

- Repeated analyzer calls can be slow without candles/result caching.
- UI result polish and manual demo validation are still important before presenting the project.
- Documentation must stay aligned with the implemented event-close logic and dataset limitations.
