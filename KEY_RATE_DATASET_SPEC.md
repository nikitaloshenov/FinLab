# Key Rate Decisions Dataset Spec

Status: documentation/spec only. No dataset, importer or production data is added by this document.

## 1. Purpose

The Key Rate Decisions Dataset is the data foundation for the Key Rate Impact Analyzer.

The analyzer should use historical key rate decisions as event-study anchors. It should answer how one selected stock historically reacted to similar key rate decisions over several trading horizons.

This is historical analysis, not a forecast, not financial advice and not an investment recommendation.

## 2. Event Definition

A key rate event is the decision, announcement or publication of a Central Bank key rate decision.

Important distinction:

- an event is not just a row saying "from this date the key rate equals X";
- an event is the moment when the market receives information about a decision;
- the stock reaction should be analyzed around this decision event.

For the Key Rate Impact Analyzer, event dates matter because the market reacts to information, not merely to the period during which a rate value is active.

## 3. Date Semantics

### decision_date

The main date for event-study analysis.

It means the date when the key rate decision was announced or published. For MVP daily-candles analysis, this is the anchor date used to study market reaction.

### meeting_date

The meeting date, if it needs to be stored separately.

It may match `decision_date`. It is nullable for MVP and is not part of the current table.

### effective_date

The date when the new rate starts to apply or appears as the active rate value.

It can be useful for reference and data quality checks, but it should not be the main event-study anchor for MVP.

It is nullable for MVP and is not part of the current table.

### publication_datetime_msk

The exact publication time in Moscow time.

It is useful for future intraday analysis, for example to distinguish decisions published before trading, during trading or after market close.

It is nullable for MVP and is not part of the current table.

### MVP Decision

For MVP daily-candles analysis, use `decision_date` as the event anchor.

Do not use `effective_date` as the primary event-study anchor.

## 4. Two Related but Different Datasets

### Key Rate Decisions

Question answered:

> When was a key rate decision made or published?

This dataset is used by the Key Rate Impact Analyzer.

It should represent decision events.

### Key Rate Values / History

Question answered:

> What key rate value was active on a specific date?

This can be useful later for a key rate chart, reference table or macro context, but it is not the main dataset for event-study analysis.

The current `key_rate_decisions` table should represent decision events, not only a history of active rate values.

## 5. Current Table and Desired Fields

Current table: `key_rate_decisions`.

Current fields:

- `id` - primary key.
- `decision_date` - event-study anchor date.
- `rate_before` - key rate before the decision.
- `rate_after` - key rate after the decision.
- `change_bps` - rate change in basis points.
- `direction` - logical direction: `rate_cut`, `rate_hike` or `rate_hold`.
- `title` - short human-readable title.
- `description` - optional longer description.
- `is_scheduled` - whether the decision belongs to a scheduled decision flow.
- `is_official` - whether the row represents official/imported official data.
- `source_url` - URL of the source or source page.
- `source_type` - source classification.
- `source_note` - additional source/data note.
- `created_at` - row creation timestamp.
- `updated_at` - row update timestamp.

Recommended future nullable fields:

- `meeting_date`;
- `effective_date`;
- `publication_datetime_msk`;
- `source_title`;
- `notes`.

These fields are recommended for a future schema refinement if real source review shows they are needed. This document does not require an immediate migration.

## 6. Required vs Nullable Fields

For an MVP official curated dataset, required fields should be:

- `decision_date`;
- `rate_before`;
- `rate_after`;
- `change_bps`;
- `direction`;
- `is_official`;
- `source_type`;
- `source_url`.

Recommended fields:

- `title`;
- `description`;
- `source_note`.

Nullable or future fields:

- `meeting_date`;
- `effective_date`;
- `publication_datetime_msk`;
- `source_title`;
- `notes`.

If a per-row source URL is not available, use a general official source URL and explain that clearly in `source_note`.

## 7. Direction and change_bps Logic

Formula:

```text
change_bps = (rate_after - rate_before) * 100
```

Examples:

- `16.00 -> 18.00 = +200 bps`, `rate_hike`;
- `16.00 -> 15.00 = -100 bps`, `rate_cut`;
- `16.00 -> 16.00 = 0 bps`, `rate_hold`.

Validation rules:

- `change_bps > 0` means `direction` must be `rate_hike`;
- `change_bps < 0` means `direction` must be `rate_cut`;
- `change_bps == 0` means `direction` must be `rate_hold`.

Use `Decimal` for rates. Avoid floats for rate calculations.

## 8. Source Strategy

MVP source strategy:

```text
official source -> curated normalized dataset in repo -> validation/import script -> key_rate_decisions table -> analyzer
```

Do not do this for MVP:

- fragile scraping;
- user-facing CSV upload;
- fake official data;
- direct manual DB inserts without source tracking;
- mixing sample/dev data with official data.

Why:

- data must be verifiable;
- sources must be reproducible;
- each row should have `source_type`, `source_url` and/or `source_note`;
- importer should validate direction, `change_bps`, dates and required fields;
- sample/dev data must not appear in ordinary user-facing analysis as official data.

## 9. Source Types and Official Flag

Recommended `source_type` values:

- `official_curated` - official data manually or semi-automatically checked and stored as a curated repo dataset.
- `official_synced` - data from a future automated sync from an official source.
- `dev_sample` - development/sample data only.

`is_official` meaning:

- `true` - official/imported official data;
- `false` - sample/dev data.

Analyzer rule:

The analyzer should use `is_official = true` by default. Dev/sample data should not appear in normal user-facing analysis output.

## 10. MVP Data Range

The exact MVP range should be chosen after reviewing the official source format.

Recommended approach:

- start with a period where official key rate decisions are available and structurally clear;
- if the official source allows it, cover the full history from the introduction of the key rate;
- if full history is too large for the first pass, start with a limited verified period and clearly state this in dataset metadata or `source_note`.

Do not claim a specific historical range until it is verified and present in the repository.

## 11. Import Strategy

Future import flow:

1. Prepare a curated CSV or JSON dataset.
2. Add an explicit header/schema.
3. Review rows manually before import.
4. Importer validates:
   - date format;
   - Decimal rates;
   - direction;
   - `change_bps`;
   - required fields;
   - duplicate `decision_date`.
5. Importer upserts by `decision_date`.
6. Importer should not import a partially invalid official dataset if validation errors exist.
7. Add dry-run mode before writing to the database.

This is only the strategy. Do not implement an importer in this documentation task.

## 12. Analyzer Integration

Current Key Rate Impact Analyzer MVP flow:

1. User selects:
   - stock;
   - direction: `rate_cut`, `rate_hike` or `rate_hold`;
   - horizons: 1, 3 and 10 trading days in the main frontend flow;
   - optional benchmark.
2. Backend loads `key_rate_decisions` where:
   - `direction = selected_direction`;
   - `is_official = true`.
3. For each decision, backend uses `decision_date` as the event anchor.
4. Backend finds the first trading candle with date `>= decision_date`.
5. Backend uses close of that event candle as `event_price`.
6. Backend calculates horizon returns from event close to close after N trading days.
7. Backend aggregates results.
8. Backend returns summary, horizon table, benchmark comparison and limitations.

## 13. Price Reaction Anchor Logic

Current MVP daily-candles approach:

- `event_date = decision_date`;
- `event_trading_day = first MOEX trading date >= decision_date`;
- `event_price = close on event_trading_day`;
- `horizon_price = close after 1/3/10 trading days from event_trading_day`;
- `stock_return = (horizon_price / event_price - 1) * 100`.

If the event candle or horizon candle is unavailable, the event/horizon is skipped. Missing market data must not be converted to `0%` because that would falsely mean the stock did not move.

Later, if `publication_datetime_msk` and intraday candles become available, the logic can distinguish:

- before trading;
- during trading;
- after market close.

This is not required for MVP.

## 14. Edge Cases

Important edge cases:

- `decision_date` falls on a non-trading day;
- decision announced after market close;
- `rate_hold` event has `change_bps = 0`;
- missing stock candles;
- missing benchmark candles;
- duplicate event dates;
- different sources disagree on dates;
- old historical data may be incomplete;
- stock was not listed or traded at an older event date;
- dividends, splits and corporate actions can affect price interpretation;
- benchmark unavailable;
- very low event count reduces confidence.

## 15. What Not To Do Now

Do not:

- write a CSV importer before this dataset strategy is accepted;
- scrape CBR in MVP;
- call external CBR/news APIs in this step;
- add fake/sample official data;
- redesign frontend before backend/data flow exists;
- present `key_rate_events.py` sample events as official decisions.

## 16. Next Steps After This Spec

Recommended sequence:

1. Review current `key_rate_decisions` schema against this spec.
2. Decide whether nullable fields like `effective_date`, `meeting_date` and `publication_datetime_msk` are needed now.
3. Prepare a curated official seed dataset.
4. Add CSV/JSON template.
5. Implement importer with validation and dry-run.
6. Import official data into local DB.
7. Keep the multi-event Key Rate Impact Analyzer aligned with the imported dataset.
8. Validate demo scenarios and document dataset limitations clearly.
