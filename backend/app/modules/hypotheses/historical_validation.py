from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any


PERCENT_MULTIPLIER = Decimal("100")
DECIMAL_ZERO = Decimal("0")
DECIMAL_QUANT = Decimal("0.000001")


def normalize_candles(candles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []

    for candle in candles:
        normalized_candle = _normalize_candle(candle)

        if normalized_candle is not None:
            normalized.append(normalized_candle)

    return sorted(normalized, key=lambda candle: candle["begin"])


def find_event_candle(
    candles: list[dict[str, Any]],
    event_date: date | datetime | str,
) -> dict[str, Any] | None:
    normalized_candles = normalize_candles(candles)
    parsed_event_date = _parse_date(event_date)

    if parsed_event_date is None:
        return None

    event_candle, _ = _find_event_candle_with_note(
        normalized_candles,
        parsed_event_date,
    )

    return event_candle


def calculate_return_percent(
    start_price: Decimal,
    end_price: Decimal,
) -> Decimal | None:
    if start_price == DECIMAL_ZERO:
        return None

    return _quantize_percent(
        (end_price - start_price) / start_price * PERCENT_MULTIPLIER
    )


def calculate_max_drawdown_percent(
    event_price: Decimal,
    after_candles: list[dict[str, Any]],
) -> Decimal | None:
    if event_price == DECIMAL_ZERO or not after_candles:
        return None

    normalized_candles = normalize_candles(after_candles)

    if not normalized_candles:
        return None

    min_after_price = min(
        min(candle["low"], candle["close"])
        for candle in normalized_candles
    )

    return calculate_return_percent(
        start_price=event_price,
        end_price=min_after_price,
    )


def calculate_max_runup_percent(
    event_price: Decimal,
    after_candles: list[dict[str, Any]],
) -> Decimal | None:
    if event_price == DECIMAL_ZERO or not after_candles:
        return None

    normalized_candles = normalize_candles(after_candles)

    if not normalized_candles:
        return None

    max_after_price = max(
        max(candle["high"], candle["close"])
        for candle in normalized_candles
    )

    return calculate_return_percent(
        start_price=event_price,
        end_price=max_after_price,
    )


def calculate_volatility_percent(
    after_candles: list[dict[str, Any]],
) -> Decimal | None:
    normalized_candles = normalize_candles(after_candles)

    if len(normalized_candles) < 2:
        return None

    returns = []

    for previous, current in zip(normalized_candles, normalized_candles[1:]):
        return_percent = calculate_return_percent(
            start_price=previous["close"],
            end_price=current["close"],
        )

        if return_percent is not None:
            returns.append(return_percent)

    if len(returns) < 2:
        return None

    with localcontext() as context:
        context.prec = 28
        mean_return = sum(returns, DECIMAL_ZERO) / Decimal(len(returns))
        variance = (
            sum((value - mean_return) ** 2 for value in returns)
            / Decimal(len(returns))
        )

        return _quantize_percent(variance.sqrt())


def analyze_ticker_event_window(
    secid: str,
    candles: list[dict[str, Any]],
    event_date: date | datetime | str,
) -> dict[str, Any]:
    normalized_secid = secid.strip().upper()
    notes: list[str] = []

    parsed_event_date = _parse_date(event_date)

    if parsed_event_date is None:
        return _failed_result(
            secid=normalized_secid,
            error="Invalid event date",
            candles_used=0,
            notes=notes,
        )

    normalized_candles = normalize_candles(candles)

    if not normalized_candles:
        return _failed_result(
            secid=normalized_secid,
            error="No candles provided",
            candles_used=0,
            notes=notes,
        )

    skipped_count = len(candles) - len(normalized_candles)

    if skipped_count > 0:
        notes.append(f"Skipped invalid candles: {skipped_count}")

    event_candle, event_note = _find_event_candle_with_note(
        candles=normalized_candles,
        event_date=parsed_event_date,
    )

    if event_candle is None:
        return _failed_result(
            secid=normalized_secid,
            error="Event candle not found",
            candles_used=len(normalized_candles),
            notes=notes,
        )

    if event_note is not None:
        notes.append(event_note)

    event_index = normalized_candles.index(event_candle)
    before_candles = normalized_candles[:event_index]
    after_candles = normalized_candles[event_index:]

    if not before_candles:
        notes.append("No candle before event date")

    if len(after_candles) < 2:
        notes.append("Not enough candles after event date for volatility")

    price_before = (
        before_candles[-1]["close"]
        if before_candles
        else None
    )
    price_at_event = event_candle["close"]
    price_after = after_candles[-1]["close"] if after_candles else None

    if price_at_event == DECIMAL_ZERO:
        notes.append("Event price is zero, return calculations are limited")

    return {
        "secid": normalized_secid,
        "status": "ok",
        "event_candle_date": event_candle["begin"].isoformat(),
        "price_before": price_before,
        "price_at_event": price_at_event,
        "price_after": price_after,
        "return_before_percent": (
            calculate_return_percent(price_before, price_at_event)
            if price_before is not None
            else None
        ),
        "return_after_percent": (
            calculate_return_percent(price_at_event, price_after)
            if price_after is not None
            else None
        ),
        "max_drawdown_after_percent": calculate_max_drawdown_percent(
            event_price=price_at_event,
            after_candles=after_candles,
        ),
        "max_runup_after_percent": calculate_max_runup_percent(
            event_price=price_at_event,
            after_candles=after_candles,
        ),
        "volatility_after_percent": calculate_volatility_percent(after_candles),
        "candles_used": len(normalized_candles),
        "notes": notes,
        "error": None,
    }


def build_validation_summary(
    ticker_results: list[dict[str, Any]],
    expected_direction: str,
) -> dict[str, Any]:
    ok_results = [
        result
        for result in ticker_results
        if result.get("status") == "ok"
        and result.get("return_after_percent") is not None
    ]
    failed_count = sum(
        1
        for result in ticker_results
        if result.get("status") != "ok"
        or result.get("return_after_percent") is None
    )

    if not ok_results:
        return {
            "overall_result": "insufficient_data",
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "failed_count": failed_count,
            "best_ticker": None,
            "worst_ticker": None,
            "average_return_after_percent": None,
            "text": (
                "Historical validation has insufficient data. "
                "This is not a forecast."
            ),
        }

    positive_count = sum(
        1
        for result in ok_results
        if result["return_after_percent"] > DECIMAL_ZERO
    )
    negative_count = sum(
        1
        for result in ok_results
        if result["return_after_percent"] < DECIMAL_ZERO
    )
    neutral_count = sum(
        1
        for result in ok_results
        if result["return_after_percent"] == DECIMAL_ZERO
    )

    best_result = max(
        ok_results,
        key=lambda result: result["return_after_percent"],
    )
    worst_result = min(
        ok_results,
        key=lambda result: result["return_after_percent"],
    )
    average_return = _quantize_percent(
        sum(
            result["return_after_percent"]
            for result in ok_results
        )
        / Decimal(len(ok_results))
    )
    normalized_direction = expected_direction.strip().lower()

    overall_result = _get_overall_result(
        expected_direction=normalized_direction,
        positive_count=positive_count,
        negative_count=negative_count,
        neutral_count=neutral_count,
    )

    return {
        "overall_result": overall_result,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "neutral_count": neutral_count,
        "failed_count": failed_count,
        "best_ticker": best_result["secid"],
        "worst_ticker": worst_result["secid"],
        "average_return_after_percent": average_return,
        "text": _build_summary_text(
            overall_result=overall_result,
            expected_direction=normalized_direction,
            ok_count=len(ok_results),
            failed_count=failed_count,
        ),
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


def _find_event_candle_with_note(
    candles: list[dict[str, Any]],
    event_date: date,
) -> tuple[dict[str, Any] | None, str | None]:
    if not candles:
        return None, None

    for candle in candles:
        if candle["begin"] == event_date:
            return candle, None

    for candle in candles:
        if candle["begin"] > event_date:
            return (
                candle,
                "Event date was not a trading day; nearest next candle was used",
            )

    return (
        candles[-1],
        "Event date is after available candles; nearest previous candle was used",
    )


def _failed_result(
    secid: str,
    error: str,
    candles_used: int,
    notes: list[str],
) -> dict[str, Any]:
    return {
        "secid": secid,
        "status": "failed",
        "event_candle_date": None,
        "price_before": None,
        "price_at_event": None,
        "price_after": None,
        "return_before_percent": None,
        "return_after_percent": None,
        "max_drawdown_after_percent": None,
        "max_runup_after_percent": None,
        "volatility_after_percent": None,
        "candles_used": candles_used,
        "notes": notes,
        "error": error,
    }


def _get_overall_result(
    expected_direction: str,
    positive_count: int,
    negative_count: int,
    neutral_count: int,
) -> str:
    if expected_direction == "positive":
        if positive_count > negative_count and positive_count > neutral_count:
            return "supports"

        if negative_count > positive_count and negative_count >= neutral_count:
            return "contradicts"

        return "mixed_support"

    if expected_direction == "negative":
        if negative_count > positive_count and negative_count > neutral_count:
            return "supports"

        if positive_count > negative_count and positive_count >= neutral_count:
            return "contradicts"

        return "mixed_support"

    return "mixed_support"


def _build_summary_text(
    overall_result: str,
    expected_direction: str,
    ok_count: int,
    failed_count: int,
) -> str:
    if overall_result == "supports":
        stance = "leans in the expected direction"
    elif overall_result == "contradicts":
        stance = "leans against the expected direction"
    else:
        stance = "is mixed"

    return (
        "Historical validation "
        f"{stance} for expected_direction={expected_direction}. "
        f"Validated tickers: {ok_count}; failed or incomplete: {failed_count}. "
        "This is not a forecast and does not prove causality."
    )


def _quantize_percent(value: Decimal) -> Decimal:
    return value.quantize(DECIMAL_QUANT)

