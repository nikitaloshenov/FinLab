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
- The final analyzer flow is not fully implemented yet, so README must avoid overclaiming.

### Recommended Next Steps

- Import official historical key rate decisions into the database.
- Build multi-event Key Rate Impact Analyzer logic.
- Add tests around historical event-study calculations.
- Keep README concise and move detailed product logic to dedicated documentation.

### Decisions

- README should stay presentation-focused and honest.
- `KEY_RATE_ANALYZER_SPEC.md` should contain the detailed product logic.
- `FEATURE_ROADMAP.md` should separate implemented, in-development and future work.
- `PROJECT_CONTEXT.md` should remain the main working context for future development tasks.
