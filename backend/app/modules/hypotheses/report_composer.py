from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.modules.hypotheses.blueprints import build_hypothesis_blueprint_report
from app.modules.hypotheses.historical_validation import (
    analyze_ticker_event_window,
    build_validation_summary,
)


def compose_hypothesis_report(
    event_type: str,
    event_direction: str,
    sector: str,
    tickers: list[str],
    user_hypothesis_text: str | None,
    event_date: date | datetime | str,
    candles_by_ticker: dict[str, list[dict[str, Any]]],
    expected_direction: str = "positive",
) -> dict[str, Any]:
    normalized_tickers = _normalize_tickers(tickers)

    if not normalized_tickers:
        raise ValueError("At least one ticker is required")

    normalized_expected_direction = expected_direction.strip().lower()
    normalized_candles_by_ticker = {
        secid.strip().upper(): candles
        for secid, candles in candles_by_ticker.items()
    }

    blueprint_report = build_hypothesis_blueprint_report(
        event_type=event_type,
        event_direction=event_direction,
        sector=sector,
        tickers=normalized_tickers,
        user_hypothesis_text=user_hypothesis_text,
    )
    blueprint = blueprint_report["blueprint"]

    ticker_results = [
        analyze_ticker_event_window(
            secid=secid,
            candles=normalized_candles_by_ticker.get(secid, []),
            event_date=event_date,
        )
        for secid in normalized_tickers
    ]
    validation_summary = build_validation_summary(
        ticker_results=ticker_results,
        expected_direction=normalized_expected_direction,
    )
    assessment = _build_assessment(
        validation_summary=validation_summary,
        ticker_results=ticker_results,
    )

    return {
        "hypothesis": {
            "event_type": blueprint["event_type"],
            "event_direction": blueprint["event_direction"],
            "sector": blueprint["sector"],
            "tickers": normalized_tickers,
            "event_date": _format_event_date(event_date),
            "expected_direction": normalized_expected_direction,
            "user_hypothesis_text": user_hypothesis_text,
        },
        "blueprint": blueprint,
        "historical_validation": {
            "ticker_results": ticker_results,
            "summary": validation_summary,
        },
        "assessment": assessment,
        "arguments_for": _build_arguments_for(
            blueprint=blueprint,
            validation_summary=validation_summary,
        ),
        "arguments_against": _build_arguments_against(
            blueprint=blueprint,
            validation_summary=validation_summary,
            ticker_results=ticker_results,
        ),
        "limitations": _build_limitations(
            blueprint=blueprint,
            ticker_results=ticker_results,
        ),
        "watch_factors": blueprint["watch_factors"],
        "suggested_alerts": _build_suggested_alerts(
            blueprint=blueprint,
            ticker_results=ticker_results,
        ),
        "metadata": {
            "source": "rule_based_hypothesis_report",
            "is_prediction": False,
            "uses_blueprint": True,
            "uses_historical_validation": True,
        },
    }


def _build_assessment(
    validation_summary: dict[str, Any],
    ticker_results: list[dict[str, Any]],
) -> dict[str, str]:
    validation_result = validation_summary["overall_result"]
    ok_count = _count_ok_ticker_results(ticker_results)
    failed_count = validation_summary["failed_count"]

    if validation_result == "insufficient_data":
        return {
            "overall_result": "insufficient_data",
            "confidence": "low",
            "text": (
                "There is not enough historical candle data for a reliable validation. "
                "The report remains a research checklist, not a forecast."
            ),
        }

    confidence = "low"

    if (
        validation_result == "supports"
        and ok_count >= 2
        and failed_count == 0
    ):
        confidence = "medium"

    if validation_result == "supports":
        text = (
            "The blueprint logic and historical validation lean in the same direction. "
            "This supports the hypothesis as a research scenario, but does not predict future prices."
        )
    elif validation_result == "contradicts":
        text = (
            "The blueprint logic exists, but historical validation leans against the expected direction. "
            "The assessment should be treated cautiously."
        )
    else:
        text = (
            "The blueprint logic exists, but historical validation is mixed across selected tickers. "
            "The scenario needs additional context before any practical conclusion."
        )

    return {
        "overall_result": validation_result,
        "confidence": confidence,
        "text": text,
    }


def _build_arguments_for(
    blueprint: dict[str, Any],
    validation_summary: dict[str, Any],
) -> list[dict[str, str]]:
    arguments = list(blueprint["arguments_for"])

    if validation_summary["overall_result"] in {"supports", "mixed_support"}:
        arguments.append(
            {
                "type": "historical_validation",
                "message": (
                    "Historical validation provides at least partial support "
                    "for the expected direction among selected tickers."
                ),
            }
        )

    return _deduplicate_arguments(arguments)


def _build_arguments_against(
    blueprint: dict[str, Any],
    validation_summary: dict[str, Any],
    ticker_results: list[dict[str, Any]],
) -> list[dict[str, str]]:
    arguments = list(blueprint["arguments_against"])

    if validation_summary["overall_result"] in {"contradicts", "mixed_support"}:
        arguments.append(
            {
                "type": "historical_validation",
                "message": (
                    "Historical validation is not uniform across selected tickers "
                    "and may weaken the scenario."
                ),
            }
        )

    if validation_summary["failed_count"] > 0:
        arguments.append(
            {
                "type": "risk",
                "message": (
                    "Some selected tickers did not have enough usable candle data "
                    "for validation."
                ),
            }
        )

    if _has_high_volatility(ticker_results):
        arguments.append(
            {
                "type": "risk",
                "message": (
                    "Post-event volatility is elevated for at least one selected ticker."
                ),
            }
        )

    return _deduplicate_arguments(arguments)


def _build_limitations(
    blueprint: dict[str, Any],
    ticker_results: list[dict[str, Any]],
) -> list[str]:
    limitations = list(blueprint["limitations"])

    for result in ticker_results:
        for note in result.get("notes", []):
            limitations.append(f"{result['secid']}: {note}")

        if result.get("error"):
            limitations.append(f"{result['secid']}: {result['error']}")

    limitations.append(
        "Historical validation is not a forecast and does not prove causality."
    )

    return _deduplicate_strings(limitations)


def _build_suggested_alerts(
    blueprint: dict[str, Any],
    ticker_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    suggested_alerts = [
        {
            **template,
            "source": "blueprint",
        }
        for template in blueprint["suggested_alert_templates"]
    ]

    for result in ticker_results:
        if result.get("status") != "ok":
            continue

        price_at_event = result.get("price_at_event")
        price_after = result.get("price_after")

        if price_after is not None:
            suggested_alerts.append(
                {
                    "secid": result["secid"],
                    "condition": "above",
                    "target_price": price_after,
                    "reason": "Watch whether price moves above the latest validation close.",
                    "source": "hypothesis_report",
                }
            )

        if price_at_event is not None:
            suggested_alerts.append(
                {
                    "secid": result["secid"],
                    "condition": "below",
                    "target_price": price_at_event,
                    "reason": "Watch whether price loses the event reference close.",
                    "source": "hypothesis_report",
                }
            )

    return suggested_alerts


def _normalize_tickers(tickers: list[str]) -> list[str]:
    return [
        ticker.strip().upper()
        for ticker in tickers
        if ticker and ticker.strip()
    ]


def _format_event_date(event_date: date | datetime | str) -> str:
    if isinstance(event_date, datetime):
        return event_date.date().isoformat()

    if isinstance(event_date, date):
        return event_date.isoformat()

    return str(event_date)


def _count_ok_ticker_results(ticker_results: list[dict[str, Any]]) -> int:
    return sum(
        1
        for result in ticker_results
        if result.get("status") == "ok"
        and result.get("return_after_percent") is not None
    )


def _has_high_volatility(ticker_results: list[dict[str, Any]]) -> bool:
    high_volatility_threshold = Decimal("10")

    return any(
        result.get("volatility_after_percent") is not None
        and result["volatility_after_percent"] >= high_volatility_threshold
        for result in ticker_results
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

