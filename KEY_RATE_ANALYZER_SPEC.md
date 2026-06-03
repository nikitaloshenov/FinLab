# Key Rate Impact Analyzer Spec

This document describes the intended product logic for the Key Rate Impact Analyzer.

Status: in development.

The current repository contains the foundation for this direction, including Hypothesis Lab, MOEX candles access and the `key_rate_decisions` database table. The final multi-event analyzer flow is not fully implemented yet.

## Product Question

The analyzer should answer:

> How did a selected stock historically react to similar key rate decisions?

In Russian:

> Как выбранная акция исторически реагировала на похожие решения по ключевой ставке?

This is historical analysis, not a forecast and not financial advice.

## Product Shift

Old MVP logic:

- choose one key rate event;
- inspect a candle window around that date;
- show one-event result.

Target logic:

- choose one stock;
- choose a key rate scenario;
- analyze all similar historical key rate decisions;
- show the typical reaction across several horizons.

Single-event candle-window analysis can remain useful for debugging or details, but it should not be the main UX.

## Main User Scenario

The user selects:

- stock: for example `SBER`, `SBERP`, `T`, `VTBR`, `CBOM` or manual ticker input;
- key rate scenario:
  - `rate_cut`;
  - `rate_hike`;
  - `rate_hold`;
- analysis horizons:
  - 1 trading day;
  - 3 trading days;
  - 10 trading days;
  - 30 trading days;
- benchmark:
  - none;
  - `IMOEX`, if supported by available market data;
  - `MOEX` as Moscow Exchange stock, not as an index.

The analyzer returns a historical event-study summary.

## Analysis Object

The main analysis object is one selected stock.

Sector can be used as context, filtering help or UI grouping, but it should not be the primary object of analysis in the MVP.

## Key Rate Decisions Dataset

The production-oriented dataset should come from the `key_rate_decisions` table.

Important fields:

- `decision_date`;
- `rate_before`;
- `rate_after`;
- `change_bps`;
- `direction`;
- `title`;
- `description`;
- `is_scheduled`;
- `is_official`;
- `source_url`;
- `source_type`;
- `source_note`.

The table should contain official/imported historical decisions. Do not insert fake sample events into this table.

The legacy `key_rate_events.py` sample layer exists only as MVP/static fallback context and should not be presented as official data.

## Calculation Flow

1. User selects a stock.
2. User selects a rate scenario:
   - `rate_cut`;
   - `rate_hike`;
   - `rate_hold`.
3. Backend loads historical key rate decisions with this direction.
4. For each event, the system finds the stock price on the event date or the next available trading date.
5. For each horizon, the system finds the stock price after:
   - 1 trading day;
   - 3 trading days;
   - 10 trading days;
   - 30 trading days.
6. The system calculates:

```text
return = (price_after / price_event - 1) * 100
```

7. For each horizon, the system calculates:
   - event count;
   - positive count;
   - negative count;
   - neutral count;
   - average return;
   - median return;
   - min return;
   - max return;
   - typical effect;
   - effect strength.
8. If benchmark is enabled, calculate:
   - benchmark return;
   - relative return = stock return - benchmark return;
   - how often the stock outperformed the benchmark;
   - how often the stock underperformed the benchmark.

## Effect Classification

Suggested MVP thresholds:

- `-1%` to `+1%`: neutral / market noise;
- `+1%` to `+3%`: weak growth;
- `+3%` to `+5%`: moderate growth;
- above `+5%`: strong growth;
- `-1%` to `-3%`: weak decline;
- `-3%` to `-5%`: moderate decline;
- below `-5%`: strong decline.

These thresholds are product heuristics and can be revised after real data review.

## Main Result UI

The result should prioritize numeric historical evidence.

Recommended sections:

1. Summary block:
   - company name;
   - rate scenario;
   - analyzed event count;
   - short conclusion;
   - strongest horizon;
   - confidence;
   - human-readable explanation.
2. Horizon table:
   - horizon;
   - average return;
   - median return;
   - growth/decline count;
   - typical effect;
   - effect strength.
3. Benchmark block:
   - relative performance if enabled;
   - clear message if disabled.
4. Event details:
   - event date;
   - decision direction;
   - returns by horizon;
   - benchmark return;
   - relative return.
5. Mechanisms:
   - explanatory context below numeric results.
6. Limitations:
   - historical reaction is not a forecast;
   - correlation does not prove causality;
   - market expectations may already price in the event;
   - reaction depends on central bank comments, company news and market context;
   - low event count limits confidence.

## What Should Not Be the Main UX

Avoid making these the primary result:

- manual selection of one specific event;
- candle window around a single event;
- required "days before event" input;
- price before/event/after as the main metric;
- max drawdown/runup/volatility as the main conclusion;
- technical warnings near the main conclusion;
- overloaded report blocks.

## Company Name Mapping

Initial mapping:

- `SBER` - Сбербанк
- `SBERP` - Сбербанк-п
- `T` - Т-Банк
- `VTBR` - ВТБ
- `CBOM` - МКБ
- `MOEX` - Московская биржа

## MVP Scope

The first strong version should support:

- one selected stock;
- key rate scenario;
- all historical events of selected direction;
- horizons 1/3/10/30 trading days;
- event count;
- growth/decline count;
- average and median return;
- effect strength;
- optional benchmark;
- human-readable conclusion;
- clear limitations.

## Later

Potential extensions:

- filter by rate change size;
- distinguish expected vs unexpected decisions if reliable data exists;
- sector basket analysis;
- confidence score;
- hypothesis-based alerts;
- richer benchmark comparison;
- additional macro or market event types.
