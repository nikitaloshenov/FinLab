# Key Rate Decisions Dataset Spec

Status: implemented foundation, active development.

This document describes the dataset strategy for historical Bank of Russia key-rate decisions used by Key Rate Analyzer.

The dataset supports historical event-study analysis. It is not a source of trading recommendations.

## Purpose

The dataset answers:

> When did key-rate decisions happen, and what was the decision direction?

Key Rate Analyzer uses these decisions as event anchors and then measures stock reaction using daily prices.

## Event Definition

A key-rate event is the decision/announcement date when the market receives information about a key-rate decision.

Important distinction:

- the event is not just a row saying "from this date the key rate equals X";
- the event is the moment used as the anchor for market reaction analysis;
- `decision_date` is the current event-study anchor.

## Date Semantics

### decision_date

Main event-study anchor date.

### meeting_date

Meeting date, if stored separately. It may match `decision_date`.

### effective_date

Date when the new rate starts to apply. Useful for reference, but not the primary event-study anchor.

### publication_datetime_msk

Exact publication time in Moscow time. Useful for possible future intraday analysis.

Current daily-price analysis uses `decision_date`, not `effective_date`, as the anchor.

## Current Dataset Flow

```text
curated CSV -> validation/import script -> key_rate_decisions table -> events importer -> generic events layer -> Key Rate Analyzer
```

Do not do this in the MVP flow:

- fragile scraping;
- fake official data;
- direct manual DB inserts without source tracking;
- mixing dev/sample events with ordinary user-facing official analysis.

## Current Table

Current table: `key_rate_decisions`.

Important fields:

- `decision_date`
- `meeting_date`
- `effective_date`
- `publication_datetime_msk`
- `rate_before`
- `rate_after`
- `change_bps`
- `direction`
- `title`
- `description`
- `is_scheduled`
- `is_official`
- `source_url`
- `source_type`
- `source_title`
- `source_note`
- `notes`
- `created_at`
- `updated_at`

The table is the curated decision source. The current analyzer flow uses generic `events` derived from this table.

## Direction and change_bps Logic

Formula:

```text
change_bps = (rate_after - rate_before) * 100
```

Examples:

- `16.00 -> 18.00 = +200 bps`, `rate_hike`;
- `16.00 -> 15.00 = -100 bps`, `rate_cut`;
- `16.00 -> 16.00 = 0 bps`, `rate_hold`.

Generic events use normalized directions:

- `rate_hike` -> `hike`;
- `rate_cut` -> `cut`;
- `rate_hold` -> `hold`.

Use `Decimal` for rates. Avoid floats for rate calculations.

## Source Strategy

MVP source strategy:

```text
official/curated source -> normalized repo dataset -> validation/import script -> database
```

Each row should preserve source context through fields such as:

- `source_type`;
- `source_url`;
- `source_title`;
- `source_note`;
- `notes`.

If a per-row source URL is not available, use a general official source URL and explain this in `source_note`.

## Official and Sample Data

`is_official` meaning:

- `true` - official/imported official or curated official-style data;
- `false` - sample/dev data.

Normal user-facing analysis should not present dev/sample data as official.

## Importer Requirements

Importer behavior:

1. Read curated CSV.
2. Validate required fields.
3. Validate date format.
4. Parse Decimal rates.
5. Validate direction and `change_bps`.
6. Reject duplicate `decision_date` rows inside one import file.
7. Support dry-run mode.
8. Upsert by `decision_date`.
9. Avoid partial writes when validation fails.

Repeated Docker/backend startup may run the importer again; rows should not be duplicated.

## Analyzer Integration

Current analyzer flow:

1. User selects:
   - stock;
   - decision type: all / hike / cut / hold;
   - year range;
   - horizons: 1, 5 and 10 trading days;
   - optional sector comparison.
2. Backend loads generic key-rate decision events.
3. Backend prepares persisted daily prices for the selected instrument if coverage is incomplete.
4. Backend uses `event_date` as the event anchor.
5. Backend finds the first daily price row with `trading_date >= event_date`.
6. Backend calculates horizon returns from event close to close after N trading days.
7. Backend aggregates results and returns used/skipped events.

## Missing Data Rules

If the event price or horizon price is unavailable, the event/horizon is skipped.

Missing market data must not be converted to `0%` because that would falsely mean the stock did not move.

Fresh events can be skipped when not enough following daily prices exist yet.

## Edge Cases

Important edge cases:

- `decision_date` falls on a non-trading day;
- decision announced after market close;
- `rate_hold` event has `change_bps = 0`;
- missing stock prices;
- duplicate event dates;
- different sources disagree on dates;
- old historical data may be incomplete;
- stock was not listed or traded at an older event date;
- dividends, splits and corporate actions can affect price interpretation;
- low event count reduces confidence.

## Later

Potential extensions:

- automated official-source sync after the curated dataset is stable;
- publication-time-aware analysis;
- richer source provenance;
- expected vs unexpected decision classification;
- additional macro-event datasets.
