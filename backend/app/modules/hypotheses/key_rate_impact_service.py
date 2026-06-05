from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
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
PERCENT_MULTIPLIER = Decimal("100")
MIN_EVENTS_FOR_BEST_HORIZON = 3

COMPANY_NAMES = {
    "SBER": "Сбербанк",
    "SBERP": "Сбербанк-п",
    "T": "Т-Банк",
    "VTBR": "ВТБ",
    "CBOM": "МКБ",
    "MOEX": "Московская биржа",
    "ROSN": "Роснефть",
    "NVTK": "Новатэк",
    "LKOH": "Лукойл",
    "GAZP": "Газпром",
    "GMKN": "Норникель",
    "YDEX": "Яндекс",
}

DIRECTION_LABELS = {
    "rate_cut": "снижение ключевой ставки",
    "rate_hike": "повышение ключевой ставки",
    "rate_hold": "сохранение ключевой ставки",
}

TYPICAL_EFFECT_LABELS = {
    "market_noise": "рыночный шум",
    "weak_growth": "слабый рост",
    "moderate_growth": "умеренный рост",
    "strong_growth": "сильный рост",
    "weak_decline": "слабое падение",
    "moderate_decline": "умеренное падение",
    "strong_decline": "сильное падение",
    "mixed": "смешанная реакция",
    "insufficient_data": "недостаточно данных",
}

TYPICAL_DIRECTION_LABELS = {
    "positive": "чаще рост",
    "negative": "чаще падение",
    "neutral": "нейтрально",
    "mixed": "смешанно",
    "insufficient_data": "недостаточно данных",
}

CONFIDENCE_LABELS = {
    "low": "низкая",
    "medium": "средняя",
    "high": "высокая",
}


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
        "main_candles": _build_candles_metadata(stock_candles),
    }

    if benchmark_candles is not None:
        report["metadata"]["benchmark_candles"] = _build_candles_metadata(
            benchmark_candles,
        )

    report["limitations"] = _deduplicate_strings(
        [*report["limitations"], *limitations]
    )
    _apply_response_polish(report, request)

    if not request.include_events:
        report["event_results"] = []

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
    candles_by_begin: dict[str, dict[str, Any]] = {}

    for chunk_from, chunk_till in _iter_year_chunks(from_date, till_date):
        chunk_candles = moex_client.fetch_candles(
            secid=ticker,
            interval=DAILY_CANDLE_INTERVAL,
            from_date=chunk_from,
            till_date=chunk_till,
        )

        for candle in chunk_candles:
            begin = candle.get("begin")

            if begin is None:
                continue

            candles_by_begin[str(begin)] = candle

    return sorted(candles_by_begin.values(), key=lambda candle: str(candle["begin"]))


def _iter_year_chunks(from_date: str, till_date: str) -> list[tuple[str, str]]:
    start = date.fromisoformat(from_date)
    end = date.fromisoformat(till_date)

    if end < start:
        return [(from_date, till_date)]

    chunks = []
    current = start

    while current <= end:
        year_end = date(current.year, 12, 31)
        chunk_end = min(year_end, end)
        chunks.append((current.isoformat(), chunk_end.isoformat()))
        current = chunk_end + timedelta(days=1)

    return chunks


def _build_candles_metadata(candles: list[dict[str, Any]]) -> dict[str, Any]:
    begins = sorted(str(candle["begin"]) for candle in candles if candle.get("begin"))

    return {
        "count": len(candles),
        "earliest_date": begins[0] if begins else None,
        "latest_date": begins[-1] if begins else None,
    }


def _empty_report(
    request: KeyRateImpactAnalyzeRequest,
    benchmark_ticker: str | None,
    limitations: list[str],
) -> dict[str, Any]:
    report = {
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

    _apply_response_polish(report, request)

    return report


def _apply_response_polish(
    report: dict[str, Any],
    request: KeyRateImpactAnalyzeRequest,
) -> None:
    _add_horizon_labels(report)
    report["best_horizon"] = _build_best_horizon(report)
    report["skipped_summary"] = _build_skipped_summary(report)
    report["confidence"] = _build_confidence(report)
    report["summary"] = _build_summary(report, request)


def _add_horizon_labels(report: dict[str, Any]) -> None:
    for item in report.get("horizon_summary", []):
        item["horizon_label"] = _horizon_label(item["horizon_days"])
        item["typical_effect_label"] = TYPICAL_EFFECT_LABELS.get(
            item.get("typical_effect"),
            item.get("typical_effect"),
        )
        item["typical_direction_label"] = TYPICAL_DIRECTION_LABELS.get(
            item.get("typical_direction"),
            item.get("typical_direction"),
        )


def _build_summary(
    report: dict[str, Any],
    request: KeyRateImpactAnalyzeRequest,
) -> dict[str, Any]:
    main_ticker = report["main_ticker"]
    company_name = COMPANY_NAMES.get(main_ticker, main_ticker)
    direction_label = DIRECTION_LABELS.get(report["direction"], report["direction"])
    result_type = _derive_result_type(report)

    return {
        "title": f"{company_name} после события: {direction_label}",
        "main_ticker": main_ticker,
        "company_name": company_name,
        "direction": report["direction"],
        "direction_label": direction_label,
        "events_total": report["decisions_total"],
        "events_used": report["decisions_used"],
        "events_skipped": report["decisions_skipped"],
        "short_conclusion": _build_short_conclusion(
            result_type=result_type,
            company_name=company_name,
            direction_label=direction_label,
            events_used=report["decisions_used"],
            events_total=report["decisions_total"],
        ),
        "result_type": result_type,
        "is_prediction": bool(report.get("metadata", {}).get("is_prediction")),
    }


def _derive_result_type(report: dict[str, Any]) -> str:
    directions = [
        item.get("typical_direction")
        for item in report.get("horizon_summary", [])
        if item.get("typical_direction") != "insufficient_data"
    ]

    if not directions:
        return "insufficient_data"

    positive_count = directions.count("positive")
    negative_count = directions.count("negative")
    neutral_count = directions.count("neutral")
    mixed_count = directions.count("mixed")

    if mixed_count > 0:
        return "mixed"

    if positive_count > negative_count and positive_count > neutral_count:
        return "positive"

    if negative_count > positive_count and negative_count > neutral_count:
        return "negative"

    if neutral_count >= positive_count and neutral_count >= negative_count:
        return "neutral"

    return "mixed"


def _build_short_conclusion(
    result_type: str,
    company_name: str,
    direction_label: str,
    events_used: int,
    events_total: int,
) -> str:
    if result_type == "insufficient_data" or events_used < MIN_EVENTS_FOR_BEST_HORIZON:
        return (
            "Данных недостаточно для устойчивого вывода. Ниже показаны "
            "отдельные исторические наблюдения."
        )

    if result_type == "positive":
        reaction_text = "исторически чаще была положительной"
    elif result_type == "negative":
        reaction_text = "исторически чаще была отрицательной"
    elif result_type == "neutral":
        reaction_text = "исторически чаще была нейтральной"
    elif result_type == "mixed":
        reaction_text = "исторически была смешанной"
    else:
        reaction_text = "не может быть надежно оценена из-за нехватки данных"

    return (
        f"{company_name}: {direction_label}; реакция {reaction_text}. "
        f"Вывод основан на {events_used} событиях из {events_total}. "
        "Историческая реакция не является прогнозом."
    )


def _build_best_horizon(report: dict[str, Any]) -> dict[str, Any] | None:
    usable_horizons = [
        item
        for item in report.get("horizon_summary", [])
        if item.get("events_with_data", 0) >= MIN_EVENTS_FOR_BEST_HORIZON
        and item.get("typical_direction") != "insufficient_data"
    ]

    if not usable_horizons:
        return None

    best = max(usable_horizons, key=_horizon_strength_score)

    return {
        "horizon_days": best["horizon_days"],
        "horizon_label": _horizon_label(best["horizon_days"]),
        "typical_direction": best["typical_direction"],
        "typical_effect": best["typical_effect"],
        "typical_effect_label": TYPICAL_EFFECT_LABELS.get(
            best.get("typical_effect"),
            best.get("typical_effect"),
        ),
        "average_return_percent": best["average_return_percent"],
        "median_return_percent": best["median_return_percent"],
        "events_with_data": best["events_with_data"],
        "reason": _best_horizon_reason(best),
    }


def _horizon_strength_score(item: dict[str, Any]) -> Decimal:
    median_return = item.get("median_return_percent")
    average_return = item.get("average_return_percent")

    if median_return is not None:
        return abs(median_return)

    if average_return is not None:
        return abs(average_return)

    return Decimal("0")


def _best_horizon_reason(item: dict[str, Any]) -> str:
    if item.get("typical_direction") == "insufficient_data":
        return (
            "На этом горизонте есть отдельные данные, но событий мало, поэтому "
            "интерпретация должна быть осторожной."
        )

    if item.get("typical_direction") in {"mixed", "neutral"}:
        return (
            "На этом горизонте движение заметнее, но реакция остается осторожной "
            "для интерпретации."
        )

    return (
        "На этом горизонте эффект выглядит наиболее выраженным среди доступных "
        "данных."
    )


def _build_confidence(report: dict[str, Any]) -> dict[str, Any]:
    reasons = []

    if report["decisions_used"] < 5:
        reasons.append("Использовано мало событий.")

    if _skipped_ratio(report) >= Decimal("0.5"):
        reasons.append("Часть событий пропущена из-за отсутствия свечей.")

    if _has_extraordinary_or_disruption_notes(report):
        reasons.append(
            "В датасете есть нестандартные рыночные события."
        )

    if _mixed_or_neutral_horizons_are_common(report):
        reasons.append("Реакция по горизонтам смешанная.")

    level = "low" if reasons else "medium"

    if not reasons:
        reasons.append("Количество пригодных событий достаточно для MVP-оценки.")

    return {
        "level": level,
        "label": CONFIDENCE_LABELS[level],
        "reasons": reasons,
    }


def _skipped_ratio(report: dict[str, Any]) -> Decimal:
    if report["decisions_total"] == 0:
        return Decimal("0")

    return Decimal(report["decisions_skipped"]) / Decimal(report["decisions_total"])


def _mixed_or_neutral_horizons_are_common(report: dict[str, Any]) -> bool:
    usable_horizons = [
        item
        for item in report.get("horizon_summary", [])
        if item.get("typical_direction") != "insufficient_data"
    ]

    if not usable_horizons:
        return True

    mixed_or_neutral_count = sum(
        1
        for item in usable_horizons
        if item.get("typical_direction") in {"mixed", "neutral"}
    )

    return mixed_or_neutral_count >= len(usable_horizons) / 2


def _has_extraordinary_or_disruption_notes(report: dict[str, Any]) -> bool:
    markers = ("extraordinary", "market disruption", "crisis", "disruption")

    for event in report.get("event_results", []):
        notes = str(event.get("notes") or "").lower()

        if any(marker in notes for marker in markers):
            return True

    return False


def _build_skipped_summary(report: dict[str, Any]) -> dict[str, Any]:
    skipped_total = report["decisions_skipped"]
    decisions_total = report["decisions_total"]
    skipped_share = (
        Decimal(skipped_total) / Decimal(decisions_total) * PERCENT_MULTIPLIER
        if decisions_total > 0
        else Decimal("0")
    )
    reason_counts: dict[str, int] = {}

    for event in report.get("event_results", []):
        if event.get("status") != "skipped":
            continue

        reason = event.get("skip_reason")

        if reason is None:
            continue

        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    return {
        "skipped_total": skipped_total,
        "skipped_share_percent": skipped_share,
        "reasons": [
            {"reason": reason, "count": count}
            for reason, count in sorted(reason_counts.items())
        ],
    }


def _horizon_label(horizon_days: int) -> str:
    if horizon_days == 1:
        return "1 торговый день"

    if horizon_days in {2, 3, 4}:
        return f"{horizon_days} торговых дня"

    return f"{horizon_days} торговых дней"


def _deduplicate_strings(values: list[str]) -> list[str]:
    unique_values = []

    for value in values:
        if value not in unique_values:
            unique_values.append(value)

    return unique_values
