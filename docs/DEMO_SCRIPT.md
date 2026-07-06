# FinLab Demo Script

This script is intended for a short portfolio/demo walkthrough.

## 1. Open the Application

Open:

- Live demo: https://jirniydizainer.ru
- Local frontend: http://127.0.0.1:5173

Explain briefly:

- FinLab started as a MOEX dashboard with watchlist and alerts.
- The current showcase feature is **Анализ реакции на решения ЦБ**.
- The analyzer is historical event-study, not a forecast and not financial advice.

## 2. Navigate to Key Rate Analyzer

Open the Hypothesis Lab / Key Rate Analyzer section.

What to say:

- The module checks how a selected stock historically changed after Bank of Russia key-rate decisions.
- It uses imported key-rate events and persisted MOEX daily prices.
- Main horizons are 1, 5 and 10 trading days.
- Used/skipped events are shown explicitly.

## Scenario 1: SBER, All Decisions, 2024-2026

Inputs:

- Stock: `SBER`
- Decision type: all decisions
- Period: 2024-2026
- Horizons: 1 / 5 / 10 trading days
- Sector comparison: on

What the user should see:

- Verdict card with a short historical conclusion.
- KPI cards with used events, best horizon, average reaction and sector comparison status.
- Horizon table for 1d, 5d and 10d.
- Used/skipped key-rate decisions.
- Sector comparison if sector data and peer prices are available.

How to explain it:

- Each key-rate decision is treated as an event.
- The event price is the first available daily close on or after the decision date.
- Returns are calculated from event close to close after N trading days.
- Skipped events are shown instead of being silently converted to zero.

Limitations to mention:

- This is historical behavior, not a prediction.
- Fresh decisions can be skipped if there are not enough following prices.
- Sector comparison is peer-based, not an official index.

## Scenario 2: SBERP, Rate Hikes, 2024-2026

Inputs:

- Stock: `SBERP`
- Decision type: rate hikes
- Period: 2024-2026
- Horizons: 1 / 5 / 10 trading days
- Sector comparison: on or off

What the user should see:

- The event sample becomes narrower because only hike events are used.
- The verdict and horizon table update for the filtered event set.
- Used/skipped counters reflect the filtered selection.

How to explain it:

- `event_direction` filters events before the study is run.
- `hike` and `rate_hike` are treated as compatible backend direction values.
- Narrower samples can make conclusions less stable.

## Scenario 3: FLOT, Rate Cuts or All Decisions, 2024-2026

Inputs:

- Stock: `FLOT`
- Decision type: rate cuts or all decisions
- Period: 2024-2026
- Horizons: 1 / 5 / 10 trading days
- Sector comparison: on

What the user should see:

- Main event-study result if daily prices and events are available.
- If sector mapping is missing, sector comparison shows a clear unavailable state.
- Used/skipped events remain visible.

How to explain it:

- The main analysis can run even when sector comparison is unavailable.
- Sector comparison depends on reference data: issuer, sector history and peer instruments.
- No sector is invented as a fallback.
- If persisted prices only cover the beginning of the selected period, the analyzer should import the missing selected-ticker range before running.

Limitations to mention:

- Missing sector mapping is a data readiness limitation, not a calculation failure.
- If MOEX has no usable prices for a period, events/horizons remain skipped honestly.

## Demo Closing

Key points to reinforce:

- The project demonstrates backend/data/product thinking.
- The strongest part is the event-study backend and database flow.
- The frontend is a demo/product layer for explaining backend results.
- The project is intentionally honest about skipped data and limitations.
