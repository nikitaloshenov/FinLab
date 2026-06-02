from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.modules.hypotheses.blueprints import build_hypothesis_blueprint_report
from app.modules.hypotheses.historical_validation import (
    analyze_ticker_event_window,
)


RELATIVE_RETURN_THRESHOLD = Decimal("0.5")
SMALL_RETURN_THRESHOLD = Decimal("0.5")
HIGH_VOLATILITY_THRESHOLD = Decimal("10")


def compose_hypothesis_report(
    event_type: str,
    event_direction: str,
    sector: str,
    main_ticker: str,
    benchmark_ticker: str | None,
    user_hypothesis_text: str | None,
    event_date: date | datetime | str,
    candles_by_ticker: dict[str, list[dict[str, Any]]],
    expected_direction: str = "positive",
) -> dict[str, Any]:
    normalized_main_ticker = _normalize_ticker(main_ticker)
    normalized_benchmark_ticker = _normalize_optional_ticker(benchmark_ticker)

    if not normalized_main_ticker:
        raise ValueError("main_ticker is required")

    if normalized_benchmark_ticker == normalized_main_ticker:
        normalized_benchmark_ticker = None

    tickers_for_blueprint = [normalized_main_ticker]

    if normalized_benchmark_ticker is not None:
        tickers_for_blueprint.append(normalized_benchmark_ticker)

    normalized_expected_direction = expected_direction.strip().lower()
    normalized_candles_by_ticker = {
        secid.strip().upper(): candles
        for secid, candles in candles_by_ticker.items()
    }

    blueprint_report = build_hypothesis_blueprint_report(
        event_type=event_type,
        event_direction=event_direction,
        sector=sector,
        tickers=tickers_for_blueprint,
        user_hypothesis_text=user_hypothesis_text,
    )
    blueprint = blueprint_report["blueprint"]

    main_ticker_result = analyze_ticker_event_window(
        secid=normalized_main_ticker,
        candles=normalized_candles_by_ticker.get(normalized_main_ticker, []),
        event_date=event_date,
    )
    benchmark_result = (
        analyze_ticker_event_window(
            secid=normalized_benchmark_ticker,
            candles=normalized_candles_by_ticker.get(
                normalized_benchmark_ticker,
                [],
            ),
            event_date=event_date,
        )
        if normalized_benchmark_ticker is not None
        else None
    )
    relative_result = _build_relative_result(
        main_ticker_result=main_ticker_result,
        benchmark_result=benchmark_result,
    )
    assessment = _build_assessment(
        main_ticker_result=main_ticker_result,
        benchmark_result=benchmark_result,
        relative_result=relative_result,
        expected_direction=normalized_expected_direction,
    )

    return {
        "hypothesis": {
            "event_type": blueprint["event_type"],
            "event_direction": blueprint["event_direction"],
            "sector": blueprint["sector"],
            "main_ticker": normalized_main_ticker,
            "benchmark_ticker": normalized_benchmark_ticker,
            "event_date": _format_event_date(event_date),
            "expected_direction": normalized_expected_direction,
            "user_hypothesis_text": user_hypothesis_text,
        },
        "blueprint": blueprint,
        "historical_validation": {
            "main_ticker_result": main_ticker_result,
            "benchmark_result": benchmark_result,
            "relative_result": relative_result,
        },
        "assessment": assessment,
        "arguments_for": _build_arguments_for(
            blueprint=blueprint,
            assessment=assessment,
            relative_result=relative_result,
        ),
        "arguments_against": _build_arguments_against(
            blueprint=blueprint,
            assessment=assessment,
            main_ticker_result=main_ticker_result,
            benchmark_result=benchmark_result,
            relative_result=relative_result,
        ),
        "limitations": _build_limitations(
            blueprint=blueprint,
            main_ticker_result=main_ticker_result,
            benchmark_result=benchmark_result,
            benchmark_ticker=normalized_benchmark_ticker,
        ),
        "watch_factors": blueprint["watch_factors"],
        "suggested_alerts": _build_suggested_alerts(
            blueprint=blueprint,
            main_ticker_result=main_ticker_result,
            relative_result=relative_result,
        ),
        "metadata": {
            "source": "rule_based_hypothesis_report",
            "is_prediction": False,
            "uses_blueprint": True,
            "uses_historical_validation": True,
        },
    }


def _build_relative_result(
    main_ticker_result: dict[str, Any],
    benchmark_result: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if benchmark_result is None:
        return None

    main_return = main_ticker_result.get("return_after_percent")
    benchmark_return = benchmark_result.get("return_after_percent")

    if (
        main_ticker_result.get("status") != "ok"
        or benchmark_result.get("status") != "ok"
        or main_return is None
        or benchmark_return is None
    ):
        return None

    relative_return = main_return - benchmark_return

    if relative_return > RELATIVE_RETURN_THRESHOLD:
        interpretation = "outperformed"
    elif relative_return < -RELATIVE_RETURN_THRESHOLD:
        interpretation = "underperformed"
    else:
        interpretation = "in_line"

    return {
        "main_ticker": main_ticker_result["secid"],
        "benchmark_ticker": benchmark_result["secid"],
        "main_return_after_percent": main_return,
        "benchmark_return_after_percent": benchmark_return,
        "relative_return_after_percent": relative_return,
        "interpretation": interpretation,
    }


def _build_assessment(
    main_ticker_result: dict[str, Any],
    benchmark_result: dict[str, Any] | None,
    relative_result: dict[str, Any] | None,
    expected_direction: str,
) -> dict[str, str]:
    main_return = main_ticker_result.get("return_after_percent")

    if main_ticker_result.get("status") != "ok" or main_return is None:
        return {
            "overall_result": "insufficient_data",
            "confidence": "low",
            "text": (
                "There is not enough historical candle data for the main ticker. "
                "The report remains a research checklist, not a forecast."
            ),
        }

    if abs(main_return) < SMALL_RETURN_THRESHOLD:
        return {
            "overall_result": "mixed_support",
            "confidence": "low",
            "text": (
                f"{main_ticker_result['secid']} showed a weak reaction after the event, "
                "with movement close to flat. The result should be treated as mixed."
            ),
        }

    main_direction_matches = _return_matches_expected_direction(
        value=main_return,
        expected_direction=expected_direction,
    )

    if expected_direction == "neutral":
        overall_result = "mixed_support"
        confidence = "low"
        text = (
            f"{main_ticker_result['secid']} moved after the event, while the expected direction is neutral. "
            "This creates a mixed historical validation result."
        )
    elif main_direction_matches:
        if _relative_result_strongly_contradicts(relative_result, expected_direction):
            overall_result = "mixed_support"
            confidence = "low"
            text = (
                f"{main_ticker_result['secid']} moved in the expected direction after the event, "
                "but benchmark comparison weakens the support."
            )
        else:
            overall_result = "supports"
            confidence = (
                "medium"
                if _benchmark_available_or_not_requested(benchmark_result)
                else "low"
            )
            text = (
                f"{main_ticker_result['secid']} moved in the expected direction after the event. "
                "This supports the scenario as historical validation, not as a forecast."
            )
    else:
        overall_result = "contradicts"
        confidence = "low"
        text = (
            f"{main_ticker_result['secid']} moved against the expected direction after the event. "
            "This contradicts the scenario in the available historical window."
        )

    if benchmark_result is not None and benchmark_result.get("status") != "ok":
        confidence = "low"

    if _has_high_volatility(main_ticker_result):
        confidence = "low"

    return {
        "overall_result": overall_result,
        "confidence": confidence,
        "text": text,
    }


def _build_arguments_for(
    blueprint: dict[str, Any],
    assessment: dict[str, str],
    relative_result: dict[str, Any] | None,
) -> list[dict[str, str]]:
    arguments = list(blueprint["arguments_for"])

    if assessment["overall_result"] in {"supports", "mixed_support"}:
        arguments.append(
            {
                "type": "historical_validation",
                "message": (
                    "Historical validation for the main ticker provides at least partial support "
                    "for the expected direction."
                ),
            }
        )

    if relative_result and relative_result["interpretation"] == "outperformed":
        arguments.append(
            {
                "type": "market_context",
                "message": (
                    "The main ticker outperformed the benchmark in the validation window."
                ),
            }
        )

    return _deduplicate_arguments(arguments)


def _build_arguments_against(
    blueprint: dict[str, Any],
    assessment: dict[str, str],
    main_ticker_result: dict[str, Any],
    benchmark_result: dict[str, Any] | None,
    relative_result: dict[str, Any] | None,
) -> list[dict[str, str]]:
    arguments = list(blueprint["arguments_against"])

    if assessment["overall_result"] in {"contradicts", "mixed_support"}:
        arguments.append(
            {
                "type": "historical_validation",
                "message": (
                    "Historical validation for the main ticker is weak, mixed, or contrary "
                    "to the expected direction."
                ),
            }
        )

    if relative_result and relative_result["interpretation"] == "underperformed":
        arguments.append(
            {
                "type": "market_context",
                "message": (
                    "The main ticker underperformed the benchmark in the validation window."
                ),
            }
        )

    if benchmark_result is not None and benchmark_result.get("status") != "ok":
        arguments.append(
            {
                "type": "risk",
                "message": "Benchmark validation was unavailable.",
            }
        )

    if _has_high_volatility(main_ticker_result):
        arguments.append(
            {
                "type": "risk",
                "message": "Post-event volatility is elevated for the main ticker.",
            }
        )

    return _deduplicate_arguments(arguments)


def _build_limitations(
    blueprint: dict[str, Any],
    main_ticker_result: dict[str, Any],
    benchmark_result: dict[str, Any] | None,
    benchmark_ticker: str | None,
) -> list[str]:
    limitations = list(blueprint["limitations"])

    _append_result_limitations(limitations, main_ticker_result)

    if benchmark_result is not None:
        _append_result_limitations(limitations, benchmark_result)

        if benchmark_result.get("status") != "ok":
            limitations.append("Benchmark validation was unavailable.")
    elif benchmark_ticker is not None:
        limitations.append("Benchmark validation was unavailable.")

    limitations.append(
        "Historical validation is not a forecast and does not prove causality."
    )

    return _deduplicate_strings(limitations)


def _build_suggested_alerts(
    blueprint: dict[str, Any],
    main_ticker_result: dict[str, Any],
    relative_result: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    suggested_alerts = [
        {
            **template,
            "source": "blueprint",
        }
        for template in blueprint["suggested_alert_templates"]
    ]

    if main_ticker_result.get("status") == "ok":
        price_at_event = main_ticker_result.get("price_at_event")
        price_after = main_ticker_result.get("price_after")

        if price_after is not None:
            suggested_alerts.append(
                {
                    "secid": main_ticker_result["secid"],
                    "condition": "above",
                    "target_price": price_after,
                    "reason": "Watch whether price moves above the latest validation close.",
                    "source": "hypothesis_report",
                }
            )

        if price_at_event is not None:
            suggested_alerts.append(
                {
                    "secid": main_ticker_result["secid"],
                    "condition": "below",
                    "target_price": price_at_event,
                    "reason": "Watch whether price loses the event reference close.",
                    "source": "hypothesis_report",
                }
            )

    if relative_result is not None:
        suggested_alerts.append(
            {
                "secid": main_ticker_result["secid"],
                "condition": None,
                "target_price": None,
                "reason": (
                    "Watch whether the main ticker continues to outperform or underperform the benchmark."
                ),
                "source": "hypothesis_report",
            }
        )

    return suggested_alerts


def _return_matches_expected_direction(
    value: Decimal,
    expected_direction: str,
) -> bool:
    if expected_direction == "positive":
        return value > DECIMAL_ZERO

    if expected_direction == "negative":
        return value < DECIMAL_ZERO

    return value == DECIMAL_ZERO


def _relative_result_strongly_contradicts(
    relative_result: dict[str, Any] | None,
    expected_direction: str,
) -> bool:
    if relative_result is None:
        return False

    if expected_direction == "positive":
        return relative_result["interpretation"] == "underperformed"

    if expected_direction == "negative":
        return relative_result["interpretation"] == "outperformed"

    return False


def _benchmark_available_or_not_requested(
    benchmark_result: dict[str, Any] | None,
) -> bool:
    return benchmark_result is None or benchmark_result.get("status") == "ok"


def _append_result_limitations(
    limitations: list[str],
    result: dict[str, Any],
) -> None:
    for note in result.get("notes", []):
        limitations.append(f"{result['secid']}: {note}")

    if result.get("error"):
        limitations.append(f"{result['secid']}: {result['error']}")


def _normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def _normalize_optional_ticker(ticker: str | None) -> str | None:
    if ticker is None:
        return None

    normalized = ticker.strip().upper()
    return normalized or None


def _format_event_date(event_date: date | datetime | str) -> str:
    if isinstance(event_date, datetime):
        return event_date.date().isoformat()

    if isinstance(event_date, date):
        return event_date.isoformat()

    return str(event_date)


def _has_high_volatility(result: dict[str, Any]) -> bool:
    return (
        result.get("volatility_after_percent") is not None
        and result["volatility_after_percent"] >= HIGH_VOLATILITY_THRESHOLD
    )


def _deduplicate_arguments(
    arguments: list[dict[str, str]],
) -> list[dict[str, str]]:
    seen_messages = set()
    unique_arguments = []

    for argument in arguments:
        message = argument["message"]

        if message in seen_messages:
            continue

        seen_messages.add(message)
        unique_arguments.append(argument)

    return unique_arguments


def _deduplicate_strings(values: list[str]) -> list[str]:
    seen_values = set()
    unique_values = []

    for value in values:
        if value in seen_values:
            continue

        seen_values.add(value)
        unique_values.append(value)

    return unique_values


DECIMAL_ZERO = Decimal("0")

