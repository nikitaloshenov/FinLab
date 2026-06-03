from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.modules.hypotheses.key_rate_decisions_repository import (
    key_rate_decision_to_dict,
    list_key_rate_decisions,
)
from app.modules.hypotheses.multi_event_validation import (
    analyze_key_rate_multi_event_reaction,
)
from app.modules.hypotheses.schemas import KeyRateImpactAnalyzeRequest
from app.modules.market.moex_client import (
    MoexClient,
    MoexClientError,
    MoexTickerNotFoundError,
)


logger = logging.getLogger(__name__)

BEFORE_EVENT_BUFFER_DAYS = 10
AFTER_EVENT_BUFFER_EXTRA_DAYS = 10
DAILY_CANDLE_INTERVAL = "1d"


class KeyRateImpactMainTickerCandlesError(Exception):
    pass


def analyze_key_rate_impact(
    db: Session,
    request: KeyRateImpactAnalyzeRequest,
) -> dict[str, Any]:
    main_ticker = request.main_ticker
    benchmark_ticker = request.benchmark_ticker
    limitations: list[str] = []

    if benchmark_ticker == main_ticker:
        benchmark_ticker = None
        limitations.append("Benchmark ticker matched main ticker and was ignored.")

    decisions = [
        key_rate_decision_to_dict(decision)
        for decision in list_key_rate_decisions(
            db,
            direction=request.direction,
            only_official=request.only_official,
            limit=request.max_events or 200,
            offset=0,
        )
    ]

    decisions = sorted(decisions, key=lambda decision: decision["decision_date"])

    if request.max_events is not None:
        decisions = decisions[-request.max_events :]

    if not decisions:
        return _empty_report(
            request=request,
            benchmark_ticker=benchmark_ticker,
            limitations=[
                "No key rate decisions found for selected filters.",
                *limitations,
            ],
        )

    from_date, till_date = _build_candle_date_range(
        decisions=decisions,
        max_horizon=max(request.horizons),
    )

    moex_client = MoexClient()

    try:
        stock_candles = _fetch_daily_candles(
            moex_client=moex_client,
            ticker=main_ticker,
            from_date=from_date,
            till_date=till_date,
        )
    except (MoexClientError, MoexTickerNotFoundError) as error:
        logger.warning(
            "Key rate impact main ticker candles fetch failed: ticker=%s error=%s",
            main_ticker,
            error,
        )
        raise KeyRateImpactMainTickerCandlesError(
            f"Could not fetch candles for ticker {main_ticker}: {error}"
        ) from error

    benchmark_candles = None

    if benchmark_ticker is not None:
        try:
            benchmark_candles = _fetch_daily_candles(
                moex_client=moex_client,
                ticker=benchmark_ticker,
                from_date=from_date,
                till_date=till_date,
            )
        except (MoexClientError, MoexTickerNotFoundError) as error:
            logger.warning(
                "Key rate impact benchmark candles fetch failed: ticker=%s error=%s",
                benchmark_ticker,
                error,
            )
            limitations.append("Benchmark comparison was unavailable or incomplete.")
            benchmark_ticker = None

    report = analyze_key_rate_multi_event_reaction(
        main_ticker=main_ticker,
        decisions=decisions,
        stock_candles=stock_candles,
        horizons=tuple(request.horizons),
        benchmark_ticker=benchmark_ticker,
        benchmark_candles=benchmark_candles,
    )
    report["direction"] = request.direction
    report["metadata"] = {
        **report["metadata"],
        "source": "key_rate_impact_service",
        "engine": "multi_event_validation",
    }

    if not request.include_events:
        report["event_results"] = []

    report["limitations"] = _deduplicate_strings(
        [*report["limitations"], *limitations]
    )

    return report


def _build_candle_date_range(
    decisions: list[dict[str, Any]],
    max_horizon: int,
) -> tuple[str, str]:
    decision_dates = [decision["decision_date"] for decision in decisions]
    earliest_date = min(decision_dates)
    latest_date = max(decision_dates)
    from_date = earliest_date - timedelta(days=BEFORE_EVENT_BUFFER_DAYS)
    till_date = latest_date + timedelta(
        days=max_horizon * 3 + AFTER_EVENT_BUFFER_EXTRA_DAYS,
    )

    return from_date.isoformat(), till_date.isoformat()


def _fetch_daily_candles(
    moex_client: MoexClient,
    ticker: str,
    from_date: str,
    till_date: str,
) -> list[dict[str, Any]]:
    return moex_client.fetch_candles(
        secid=ticker,
        interval=DAILY_CANDLE_INTERVAL,
        from_date=from_date,
        till_date=till_date,
    )


def _empty_report(
    request: KeyRateImpactAnalyzeRequest,
    benchmark_ticker: str | None,
    limitations: list[str],
) -> dict[str, Any]:
    return {
        "main_ticker": request.main_ticker,
        "benchmark_ticker": benchmark_ticker,
        "direction": request.direction,
        "horizons": request.horizons,
        "decisions_total": 0,
        "decisions_used": 0,
        "decisions_skipped": 0,
        "horizon_summary": [],
        "benchmark_summary": None,
        "event_results": [],
        "limitations": _deduplicate_strings(
            [
                *limitations,
                "Historical reaction is not a forecast.",
                "Historical reaction does not prove causality.",
            ]
        ),
        "metadata": {
            "source": "key_rate_impact_service",
            "engine": "multi_event_validation",
            "is_prediction": False,
            "uses_official_decisions": request.only_official,
            "uses_daily_candles": True,
        },
    }


def _deduplicate_strings(values: list[str]) -> list[str]:
    unique_values = []

    for value in values:
        if value not in unique_values:
            unique_values.append(value)

    return unique_values
