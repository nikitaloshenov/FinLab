from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


PERCENT_MULTIPLIER = Decimal("100")
DECIMAL_ZERO = Decimal("0")
DECIMAL_ONE = Decimal("1")
DECIMAL_THREE = Decimal("3")
DECIMAL_FIVE = Decimal("5")
DECIMAL_QUANT = Decimal("0.000001")
DEFAULT_HORIZONS = (1, 3, 10, 30)
MIN_EVENTS_FOR_CONFIDENCE = 3


def normalize_candles(candles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []

    for candle in candles:
        normalized_candle = _normalize_candle(candle)

        if normalized_candle is not None:
            normalized.append(normalized_candle)

    return sorted(normalized, key=lambda candle: candle["begin"])


def find_event_trading_day(
    candles: list[dict[str, Any]],
    decision_date: date | datetime | str,
) -> dict[str, Any] | None:
    parsed_decision_date = _parse_date(decision_date)

    if parsed_decision_date is None:
        return None

    for candle in normalize_candles(candles):
        if candle["begin"] >= parsed_decision_date:
            return candle

    return None


def find_baseline_candle(
    candles: list[dict[str, Any]],
    event_trading_day: dict[str, Any],
) -> dict[str, Any] | None:
    event_date = _parse_date(event_trading_day.get("begin"))

    if event_date is None:
        return None

    baseline_candidates = [
        candle
        for candle in normalize_candles(candles)
        if candle["begin"] < event_date
    ]

    return baseline_candidates[-1] if baseline_candidates else None


def find_horizon_candle(
    candles: list[dict[str, Any]],
    event_trading_day: dict[str, Any],
    horizon_days: int,
) -> dict[str, Any] | None:
    if horizon_days < 1:
        return None

    normalized_candles = normalize_candles(candles)

    try:
        event_index = next(
            index
            for index, candle in enumerate(normalized_candles)
            if candle["begin"] == event_trading_day["begin"]
        )
    except StopIteration:
        return None

    horizon_index = event_index + horizon_days

    if horizon_index >= len(normalized_candles):
        return None

    return normalized_candles[horizon_index]


def calculate_return_percent(
    baseline_price: Decimal,
    horizon_price: Decimal,
) -> Decimal | None:
    if baseline_price == DECIMAL_ZERO:
        return None

    return _quantize_percent(
        (horizon_price / baseline_price - Decimal("1")) * PERCENT_MULTIPLIER
    )


def classify_return_strength(return_percent: Decimal) -> dict[str, str]:
    if -DECIMAL_ONE <= return_percent <= DECIMAL_ONE:
        return {
            "effect_type": "market_noise",
            "effect_label": "рыночный шум",
            "direction": "neutral",
            "strength": "neutral",
        }

    if return_percent > DECIMAL_FIVE:
        return {
            "effect_type": "strong_growth",
            "effect_label": "сильный рост",
            "direction": "positive",
            "strength": "strong",
        }

    if return_percent > DECIMAL_THREE:
        return {
            "effect_type": "moderate_growth",
            "effect_label": "умеренный рост",
            "direction": "positive",
            "strength": "moderate",
        }

    if return_percent > DECIMAL_ONE:
        return {
            "effect_type": "weak_growth",
            "effect_label": "слабый рост",
            "direction": "positive",
            "strength": "weak",
        }

    if return_percent < -DECIMAL_FIVE:
        return {
            "effect_type": "strong_decline",
            "effect_label": "сильное падение",
            "direction": "negative",
            "strength": "strong",
        }

    if return_percent < -DECIMAL_THREE:
        return {
            "effect_type": "moderate_decline",
            "effect_label": "умеренное падение",
            "direction": "negative",
            "strength": "moderate",
        }

    return {
        "effect_type": "weak_decline",
        "effect_label": "слабое падение",
        "direction": "negative",
        "strength": "weak",
    }


def analyze_single_decision_reaction(
    decision: dict[str, Any],
    stock_candles: list[dict[str, Any]],
    horizons: tuple[int, ...] | list[int] = DEFAULT_HORIZONS,
) -> dict[str, Any]:
    normalized_candles = normalize_candles(stock_candles)
    decision_date = _parse_date(decision.get("decision_date"))
    event_row = _build_event_base(decision)
    event_row["horizons"] = [
        _skipped_horizon(horizon, "event_unavailable")
        for horizon in horizons
    ]

    if decision_date is None:
        event_row["status"] = "skipped"
        event_row["skip_reason"] = "invalid_decision_date"
        return event_row

    event_candle = find_event_trading_day(normalized_candles, decision_date)

    if event_candle is None:
        event_row["status"] = "skipped"
        event_row["skip_reason"] = "event_trading_day_not_found"
        return event_row

    event_row["event_trading_date"] = event_candle["begin"].isoformat()
    baseline_candle = find_baseline_candle(normalized_candles, event_candle)

    if baseline_candle is None:
        event_row["status"] = "skipped"
        event_row["skip_reason"] = "baseline_not_found"
        event_row["horizons"] = [
            _skipped_horizon(horizon, "baseline_not_found")
            for horizon in horizons
        ]
        return event_row

    event_row["baseline_date"] = baseline_candle["begin"].isoformat()

    horizon_results = []

    for horizon in horizons:
        horizon_candle = find_horizon_candle(
            normalized_candles,
            event_candle,
            int(horizon),
        )

        if horizon_candle is None:
            horizon_results.append(
                _skipped_horizon(int(horizon), "horizon_candle_not_found")
            )
            continue

        return_percent = calculate_return_percent(
            baseline_price=baseline_candle["close"],
            horizon_price=horizon_candle["close"],
        )

        if return_percent is None:
            horizon_results.append(
                _skipped_horizon(int(horizon), "baseline_price_is_zero")
            )
            continue

        classification = classify_return_strength(return_percent)
        horizon_results.append(
            {
                "horizon_days": int(horizon),
                "horizon_date": horizon_candle["begin"].isoformat(),
                "stock_return_percent": return_percent,
                "benchmark_return_percent": None,
                "relative_return_percent": None,
                "classification": classification,
                "status": "ok",
                "skip_reason": None,
            }
        )

    event_row["horizons"] = horizon_results
    ok_count = sum(1 for result in horizon_results if result["status"] == "ok")

    if ok_count == len(horizon_results):
        event_row["status"] = "ok"
        event_row["skip_reason"] = None
    elif ok_count > 0:
        event_row["status"] = "partial"
        event_row["skip_reason"] = "some_horizons_missing"
    else:
        event_row["status"] = "skipped"
        event_row["skip_reason"] = "horizon_candle_not_found"

    return event_row


def build_horizon_summary(
    event_results: list[dict[str, Any]],
    horizons: tuple[int, ...] | list[int] = DEFAULT_HORIZONS,
) -> list[dict[str, Any]]:
    summaries = []

    for horizon in horizons:
        horizon = int(horizon)
        values = _stock_returns_for_horizon(event_results, horizon)
        events_total = len(event_results)
        events_with_data = len(values)
        skipped_events = events_total - events_with_data
        positive_count = sum(1 for value in values if value > DECIMAL_ONE)
        negative_count = sum(1 for value in values if value < -DECIMAL_ONE)
        neutral_count = events_with_data - positive_count - negative_count
        average_return = _average(values)
        median_return = _median(values)
        typical = _typical_effect(
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            average_return=average_return,
            median_return=median_return,
        )

        summaries.append(
            {
                "horizon_days": horizon,
                "events_total": events_total,
                "events_with_data": events_with_data,
                "skipped_events": skipped_events,
                "positive_count": positive_count,
                "negative_count": negative_count,
                "neutral_count": neutral_count,
                "average_return_percent": average_return,
                "median_return_percent": median_return,
                "min_return_percent": min(values) if values else None,
                "max_return_percent": max(values) if values else None,
                "typical_direction": typical["typical_direction"],
                "typical_effect": typical["typical_effect"],
                "effect_strength": typical["effect_strength"],
                "positive_share_percent": _share_percent(
                    positive_count,
                    events_with_data,
                ),
                "negative_share_percent": _share_percent(
                    negative_count,
                    events_with_data,
                ),
            }
        )

    return summaries


def analyze_key_rate_multi_event_reaction(
    main_ticker: str,
    decisions: list[dict[str, Any]],
    stock_candles: list[dict[str, Any]],
    horizons: tuple[int, ...] | list[int] = DEFAULT_HORIZONS,
    benchmark_ticker: str | None = None,
    benchmark_candles: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized_ticker = main_ticker.strip().upper()
    normalized_benchmark_ticker = (
        benchmark_ticker.strip().upper()
        if benchmark_ticker and benchmark_ticker.strip()
        else None
    )
    normalized_horizons = tuple(int(horizon) for horizon in horizons)

    event_results = [
        analyze_single_decision_reaction(
            decision=decision,
            stock_candles=stock_candles,
            horizons=normalized_horizons,
        )
        for decision in decisions
    ]

    benchmark_limitation = None
    benchmark_summary = None

    if normalized_benchmark_ticker is not None:
        if benchmark_candles:
            benchmark_event_results = [
                analyze_single_decision_reaction(
                    decision=decision,
                    stock_candles=benchmark_candles,
                    horizons=normalized_horizons,
                )
                for decision in decisions
            ]
            _merge_benchmark_results(event_results, benchmark_event_results)
            benchmark_summary = _build_benchmark_summary(
                event_results,
                normalized_horizons,
            )
        else:
            benchmark_limitation = "Benchmark comparison was unavailable."

    horizon_summary = build_horizon_summary(event_results, normalized_horizons)
    decisions_used = sum(
        1
        for result in event_results
        if result["status"] in {"ok", "partial"}
    )
    limitations = _build_limitations(
        event_results=event_results,
        decisions_used=decisions_used,
        benchmark_ticker=normalized_benchmark_ticker,
        benchmark_limitation=benchmark_limitation,
    )

    return {
        "main_ticker": normalized_ticker,
        "benchmark_ticker": normalized_benchmark_ticker,
        "horizons": list(normalized_horizons),
        "decisions_total": len(decisions),
        "decisions_used": decisions_used,
        "decisions_skipped": len(decisions) - decisions_used,
        "horizon_summary": horizon_summary,
        "benchmark_summary": benchmark_summary,
        "event_results": event_results,
        "limitations": limitations,
        "metadata": {
            "source": "multi_event_validation",
            "is_prediction": False,
            "uses_official_decisions": all(
                bool(decision.get("is_official")) for decision in decisions
            )
            if decisions
            else False,
            "uses_daily_candles": True,
        },
    }


def _normalize_candle(candle: dict[str, Any]) -> dict[str, Any] | None:
    begin = _parse_date(candle.get("begin"))
    close = _to_decimal(candle.get("close"))

    if begin is None or close is None:
        return None

    open_price = _to_decimal(candle.get("open")) or close
    high_price = _to_decimal(candle.get("high")) or max(open_price, close)
    low_price = _to_decimal(candle.get("low")) or min(open_price, close)
    volume = _to_decimal(candle.get("volume"))

    return {
        "begin": begin,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close,
        "volume": volume,
    }


def _parse_date(value: date | datetime | str | None) -> date | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        normalized_value = value.strip().replace("Z", "+00:00")

        if not normalized_value:
            return None

        try:
            return datetime.fromisoformat(normalized_value).date()
        except ValueError:
            try:
                return date.fromisoformat(normalized_value)
            except ValueError:
                return None

    return None


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _quantize_percent(value: Decimal) -> Decimal:
    return value.quantize(DECIMAL_QUANT)


def _build_event_base(decision: dict[str, Any]) -> dict[str, Any]:
    decision_date = _parse_date(decision.get("decision_date"))

    return {
        "decision_date": decision_date.isoformat() if decision_date else None,
        "event_trading_date": None,
        "baseline_date": None,
        "rate_before": decision.get("rate_before"),
        "rate_after": decision.get("rate_after"),
        "change_bps": decision.get("change_bps"),
        "direction": decision.get("direction"),
        "title": decision.get("title"),
        "is_scheduled": decision.get("is_scheduled"),
        "notes": decision.get("notes"),
        "status": "skipped",
        "skip_reason": None,
    }


def _skipped_horizon(horizon_days: int, reason: str) -> dict[str, Any]:
    return {
        "horizon_days": int(horizon_days),
        "horizon_date": None,
        "stock_return_percent": None,
        "benchmark_return_percent": None,
        "relative_return_percent": None,
        "classification": None,
        "status": "skipped",
        "skip_reason": reason,
    }


def _stock_returns_for_horizon(
    event_results: list[dict[str, Any]],
    horizon_days: int,
) -> list[Decimal]:
    values = []

    for event_result in event_results:
        horizon_result = _find_horizon_result(event_result, horizon_days)

        if (
            horizon_result is not None
            and horizon_result.get("status") == "ok"
            and horizon_result.get("stock_return_percent") is not None
        ):
            values.append(horizon_result["stock_return_percent"])

    return values


def _find_horizon_result(
    event_result: dict[str, Any],
    horizon_days: int,
) -> dict[str, Any] | None:
    for horizon_result in event_result.get("horizons", []):
        if horizon_result.get("horizon_days") == horizon_days:
            return horizon_result

    return None


def _average(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None

    return _quantize_percent(sum(values, DECIMAL_ZERO) / Decimal(len(values)))


def _median(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None

    sorted_values = sorted(values)
    midpoint = len(sorted_values) // 2

    if len(sorted_values) % 2 == 1:
        return sorted_values[midpoint]

    return _quantize_percent(
        (sorted_values[midpoint - 1] + sorted_values[midpoint]) / Decimal("2")
    )


def _share_percent(count: int, total: int) -> Decimal | None:
    if total == 0:
        return None

    return _quantize_percent(Decimal(count) / Decimal(total) * PERCENT_MULTIPLIER)


def _typical_effect(
    positive_count: int,
    negative_count: int,
    neutral_count: int,
    average_return: Decimal | None,
    median_return: Decimal | None,
) -> dict[str, str]:
    events_with_data = positive_count + negative_count + neutral_count

    if events_with_data < MIN_EVENTS_FOR_CONFIDENCE:
        return {
            "typical_direction": "insufficient_data",
            "typical_effect": "insufficient_data",
            "effect_strength": "insufficient_data",
        }

    if neutral_count > positive_count and neutral_count > negative_count:
        return {
            "typical_direction": "neutral",
            "typical_effect": "market_noise",
            "effect_strength": "neutral",
        }

    if (
        positive_count > negative_count
        and average_return is not None
        and median_return is not None
        and average_return > DECIMAL_ZERO
        and median_return > DECIMAL_ZERO
    ):
        classification = classify_return_strength(average_return)
        return {
            "typical_direction": "positive",
            "typical_effect": classification["effect_type"],
            "effect_strength": classification["strength"],
        }

    if (
        negative_count > positive_count
        and average_return is not None
        and median_return is not None
        and average_return < DECIMAL_ZERO
        and median_return < DECIMAL_ZERO
    ):
        classification = classify_return_strength(average_return)
        return {
            "typical_direction": "negative",
            "typical_effect": classification["effect_type"],
            "effect_strength": classification["strength"],
        }

    return {
        "typical_direction": "mixed",
        "typical_effect": "mixed",
        "effect_strength": "mixed",
    }


def _merge_benchmark_results(
    stock_event_results: list[dict[str, Any]],
    benchmark_event_results: list[dict[str, Any]],
) -> None:
    for stock_event, benchmark_event in zip(
        stock_event_results,
        benchmark_event_results,
    ):
        for stock_horizon in stock_event["horizons"]:
            benchmark_horizon = _find_horizon_result(
                benchmark_event,
                stock_horizon["horizon_days"],
            )

            if benchmark_horizon is None:
                continue

            benchmark_return = benchmark_horizon.get("stock_return_percent")
            stock_return = stock_horizon.get("stock_return_percent")

            if benchmark_return is None:
                if stock_horizon["status"] == "ok":
                    stock_horizon["status"] = "partial"
                    stock_horizon["skip_reason"] = "benchmark_missing"
                continue

            stock_horizon["benchmark_return_percent"] = benchmark_return

            if stock_return is not None:
                stock_horizon["relative_return_percent"] = _quantize_percent(
                    stock_return - benchmark_return
                )


def _build_benchmark_summary(
    event_results: list[dict[str, Any]],
    horizons: tuple[int, ...],
) -> list[dict[str, Any]]:
    summaries = []

    for horizon in horizons:
        benchmark_values = []
        relative_values = []

        for event_result in event_results:
            horizon_result = _find_horizon_result(event_result, horizon)

            if horizon_result is None:
                continue

            benchmark_return = horizon_result.get("benchmark_return_percent")
            relative_return = horizon_result.get("relative_return_percent")

            if benchmark_return is not None:
                benchmark_values.append(benchmark_return)

            if relative_return is not None:
                relative_values.append(relative_return)

        outperformed_count = sum(
            1 for value in relative_values if value > DECIMAL_ONE
        )
        underperformed_count = sum(
            1 for value in relative_values if value < -DECIMAL_ONE
        )
        neutral_relative_count = (
            len(relative_values) - outperformed_count - underperformed_count
        )

        summaries.append(
            {
                "horizon_days": horizon,
                "benchmark_events_with_data": len(benchmark_values),
                "average_benchmark_return_percent": _average(benchmark_values),
                "average_relative_return_percent": _average(relative_values),
                "median_relative_return_percent": _median(relative_values),
                "outperformed_count": outperformed_count,
                "underperformed_count": underperformed_count,
                "neutral_relative_count": neutral_relative_count,
                "outperformed_share_percent": _share_percent(
                    outperformed_count,
                    len(relative_values),
                ),
            }
        )

    return summaries


def _build_limitations(
    event_results: list[dict[str, Any]],
    decisions_used: int,
    benchmark_ticker: str | None,
    benchmark_limitation: str | None,
) -> list[str]:
    limitations = [
        "Historical reaction is not a forecast.",
        "Historical reaction does not prove causality.",
        "Corporate actions and dividends may affect interpretation.",
    ]

    if decisions_used < MIN_EVENTS_FOR_CONFIDENCE:
        limitations.append("Small number of events limits confidence.")

    if any(result["status"] in {"skipped", "partial"} for result in event_results):
        limitations.append("Some events were skipped because of missing candles.")

    if any(_has_extraordinary_note(result.get("notes")) for result in event_results):
        limitations.append(
            "Some events are marked as extraordinary or market disruption."
        )

    if benchmark_ticker is not None and (
        benchmark_limitation is not None
        or _has_incomplete_benchmark(event_results)
    ):
        limitations.append("Benchmark comparison was unavailable or incomplete.")

    return _deduplicate_strings(limitations)


def _has_extraordinary_note(notes: Any) -> bool:
    if notes is None:
        return False

    normalized_notes = str(notes).lower()
    markers = ("disruption", "crisis", "extraordinary")

    return any(marker in normalized_notes for marker in markers)


def _has_incomplete_benchmark(event_results: list[dict[str, Any]]) -> bool:
    for event_result in event_results:
        for horizon_result in event_result.get("horizons", []):
            if (
                horizon_result.get("status") in {"ok", "partial"}
                and horizon_result.get("benchmark_return_percent") is None
            ):
                return True

    return False


def _deduplicate_strings(values: list[str]) -> list[str]:
    unique_values = []

    for value in values:
        if value not in unique_values:
            unique_values.append(value)

    return unique_values
