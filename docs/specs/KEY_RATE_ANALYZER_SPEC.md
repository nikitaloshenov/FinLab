# Key Rate Analyzer Spec

Status: implemented MVP, active development.

This document describes the current product and calculation logic for **Анализ реакции на решения ЦБ** / Key Rate Analyzer.

Related documents:

- `KEY_RATE_DATASET_SPEC.md` describes the historical key-rate decisions dataset.
- `../ARCHITECTURE.md` describes how the analyzer fits into the backend architecture.

## Product Question

The analyzer answers:

> How did a selected stock historically change after similar Bank of Russia key-rate decisions?

This is historical analysis, not a forecast and not financial advice.

## Main User Scenario

The user selects:

- stock, for example `SBER`, `SBERP`, `T`, `VTBR`, `CBOM` or another MOEX ticker;
- decision type:
  - all decisions;
  - rate hikes;
  - rate cuts;
  - rate holds;
- year range;
- horizons:
  - 1 trading day;
  - 5 trading days;
  - 10 trading days;
- optional peer-based sector comparison.

The analyzer returns a historical event-study summary.

## Current API

Current endpoint:

```text
POST /api/v1/hypotheses/key-rate-impact/v2
```

Legacy endpoints may still exist for compatibility, but this is the current analyzer flow used by the frontend.

## Data Sources

The analyzer uses:

- imported key-rate decisions;
- generic `events` rows derived from key-rate decisions;
- persisted analytics daily prices in `price_candles`;
- reference data for instruments, issuers and sectors;
- study result tables for run/event/horizon outputs.

The market chart can use a separate MOEX chart flow. Analyzer calculations should use persisted analytics data so results are reproducible and auditable.

## Calculation Flow

For each selected key-rate event:

1. Use `event_date` as the event anchor.
2. Find the first daily price row for the selected instrument where `trading_date >= event_date`.
3. Use its `close` as `event_price`.
4. For each selected horizon `N`, find the row at `event_index + N`.
5. Calculate:

```text
horizon_return = (horizon_close / event_price - 1) * 100
```

All horizons are trading-day horizons, not calendar-day horizons.

If the event price or horizon price is missing, that event/horizon is skipped. Missing data must not be converted to `0%`.

## Data Coverage

Before running analysis, the service checks whether persisted daily prices cover the selected instrument and date range.

Current MVP behavior:

- first available price should be close to the requested start;
- last available price should be close to the effective requested end;
- if only the beginning of the range exists, the analyzer imports the missing selected-ticker tail;
- if data remains unavailable after preparation, skipped events/horizons stay visible in the response.

The service does not perform a full exchange-calendar completeness audit yet.

## Event Direction

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

## Sector Comparison

Sector comparison is optional and peer-based.

Flow:

1. Resolve the selected instrument's issuer.
2. Resolve current sector through `issuer_sector_history`.
3. Select limited peer instruments from the same sector and same asset type.
4. Exclude the selected instrument itself.
5. Calculate peer returns over the same events and horizons.
6. Compare selected stock average return with peer average/median.

This is not an official sector index and should not be described as one.

## Main Result UI

The result should prioritize numeric historical evidence:

1. Verdict card:
   - selected stock;
   - decision type;
   - short historical conclusion;
   - disclaimer that this is not a forecast.
2. KPI cards:
   - used events;
   - best horizon;
   - average reaction;
   - sector comparison status.
3. Horizon table:
   - horizon;
   - average return;
   - median return;
   - positive/negative/neutral count;
   - used/skipped events.
4. Sector comparison:
   - peer count;
   - relative result vs peers;
   - unavailable state when sector/peer data is missing.
5. Used/skipped events:
   - readable skipped reasons;
   - no fake zero returns.
6. Data quality details:
   - data preparation;
   - imported rows;
   - limitations.

## Important Limitations

- Historical reaction does not imply causality.
- Historical reaction is not a price forecast.
- Fresh events may be skipped if there are not enough following prices.
- Low event count makes conclusions less stable.
- Sector comparison is peer-based, not an official sector index.
- Corporate actions, dividends and market context can affect interpretation.

## What Not To Do Now

Do not:

- present the analyzer as financial advice;
- silently substitute missing data with zero;
- use latest/watchlist price in event-study calculations;
- use intraday chart data for the current daily-price analyzer;
- treat `MOEX` stock as the IMOEX market benchmark;
- add new macro-event analyzers before the current flow is stable.

## Later

Potential extensions:

- filter key-rate decisions by change size;
- distinguish expected vs unexpected decisions if reliable data exists;
- market benchmark / IMOEX comparison after proper index data exists;
- saved study history;
- richer data-quality score;
- additional macro or market event types.
