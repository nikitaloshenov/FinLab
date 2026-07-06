# FinLab Interview Notes

Use these notes to explain FinLab during a code review or interview.

## Short Project Pitch

FinLab is a fullstack fintech project for historical analysis of market hypotheses. The main showcase feature is Key Rate Analyzer: it shows how selected MOEX stocks historically changed after Bank of Russia key-rate decisions.

It is a research/demo tool, not a trading recommendation.

## Why Daily Prices?

Key Rate Analyzer uses persisted daily prices because the research question is about market reaction after macro events, not about the latest watchlist price.

Daily prices give stable trading-day horizons:

- 1 trading day;
- 5 trading days;
- 10 trading days.

Latest price and intraday chart data are not used for event-study because they would mix monitoring data with historical analysis.

## How the Event Price Is Selected

For each key-rate event:

1. Take the event date.
2. Find the first daily price row with `trading_date >= event_date`.
3. Use its close as the event price.

This handles weekends and non-trading days without inventing prices.

## How Horizons Are Calculated

For horizon `N`:

1. Find the event price row index.
2. Take the row at `event_index + N`.
3. Calculate:

```text
return = close_after_N_trading_days / event_close - 1
```

The result is stored as percent return.

## Why Skipped Events Are Better Than Fake Zero Returns

If an event price or horizon price is missing, FinLab skips that event/horizon.

It does not use zero because zero would mean "the stock did not move", while the real meaning is "data is missing".

This is important for honest analytics.

## How event_direction Works

Supported user-facing directions:

- `all`
- `hike`
- `cut`
- `hold`

Compatibility aliases:

- `rate_hike` -> `hike`
- `rate_cut` -> `cut`
- `rate_hold` -> `hold`

`all` means no direction filter.

## How Sector Comparison Works

Sector comparison:

1. Finds the selected stock's current sector through issuer sector history.
2. Selects peer instruments from the same sector and same asset type.
3. Excludes the selected stock itself.
4. Calculates peer event-study returns over the same events and horizons.
5. Compares selected stock average return with peer average/median.

Important: this is peer-based comparison, not an official sector index like IMOEX.

Sector assignment is curated, not guessed from ticker names. The reference seed creates known sector records and assigns `issuer_sector_history` for supported MOEX tickers. If an issuer already has a different current sector, the seed reports a conflict and does not overwrite it silently.

## Data Coverage

The market chart and analyzer use different flows:

- Market Chart can fetch MOEX chart data directly.
- Key Rate Analyzer uses persisted analytics daily prices from `price_candles`.

The analyzer checks whether `price_candles` covers the selected period. If only the beginning of the range is present, it imports the missing selected-ticker tail before running analysis. If data is still missing, affected events/horizons are skipped with readable reasons.

This avoids a misleading result where old partial data looks "ready" for a newer period.

## Data Readiness Trade-Offs

Current data readiness is still MVP-level:

- it checks selected-instrument daily price coverage by range;
- it can import missing selected-ticker prices on demand;
- it tracks skipped events and skipped horizons;
- it does not yet perform a full exchange-calendar completeness audit.

Future improvement:

- stronger calendar-aware completeness validation;
- clearer data quality score;
- cached/imported coverage by instrument and period.

## What the Project Demonstrates

- Backend API design with FastAPI.
- SQLAlchemy models and PostgreSQL schema design.
- Alembic migrations.
- Data ingestion from MOEX and CSV.
- Event-study methodology.
- Separation between monitoring features and analytical features.
- Test-driven hardening of edge cases.
- Product thinking: the UI explains results, limitations and skipped data.

## Likely Interview Questions

**Why not use the latest price?**  
Because event-study needs historical daily prices and trading-day horizons.

**How do you avoid fake precision?**  
By showing used/skipped events and not converting missing data to zero.

**What happens if sector mapping is missing?**  
The main analysis still works; sector comparison returns a clear unavailable state.

**Why can the chart show data while analyzer reports missing data?**  
Because the chart can use a live MOEX chart flow, while the analyzer uses persisted `price_candles` for reproducible historical calculations.

**What is the biggest limitation now?**  
Data readiness and coverage validation are improving, but still MVP-level.

**How would you extend this to other macro events?**  
Reuse the generic events/studies layer and add new event types such as inflation releases, currency shocks or oil price events.

**Is this financial advice?**  
No. It is a historical research/demo tool.
