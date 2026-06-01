from datetime import date, datetime
from decimal import Decimal

from app.modules.hypotheses.historical_validation import (
    analyze_ticker_event_window,
    build_validation_summary,
    calculate_max_drawdown_percent,
    calculate_max_runup_percent,
    calculate_return_percent,
    calculate_volatility_percent,
    find_event_candle,
    normalize_candles,
)


def test_analyze_ticker_event_window_success_exact_event_date():
    result = analyze_ticker_event_window(
        secid="sber",
        candles=_sample_candles(),
        event_date=date(2026, 5, 15),
    )

    assert result["secid"] == "SBER"
    assert result["status"] == "ok"
    assert result["event_candle_date"] == "2026-05-15"
    assert result["price_before"] == Decimal("100")
    assert result["price_at_event"] == Decimal("105")
    assert result["price_after"] == Decimal("110")
    assert result["candles_used"] == 4
    assert result["error"] is None


def test_event_date_on_non_trading_day_uses_nearest_next_candle():
    result = analyze_ticker_event_window(
        secid="SBER",
        candles=_sample_candles(),
        event_date="2026-05-14",
    )

    assert result["status"] == "ok"
    assert result["event_candle_date"] == "2026-05-15"
    assert any("nearest next candle" in note for note in result["notes"])


def test_event_date_after_all_candles_uses_nearest_previous_candle():
    result = analyze_ticker_event_window(
        secid="SBER",
        candles=_sample_candles(),
        event_date=datetime(2026, 5, 30, 12, 0),
    )

    assert result["status"] == "ok"
    assert result["event_candle_date"] == "2026-05-19"
    assert any("nearest previous candle" in note for note in result["notes"])


def test_empty_candles_returns_failed():
    result = analyze_ticker_event_window(
        secid="SBER",
        candles=[],
        event_date="2026-05-15",
    )

    assert result["status"] == "failed"
    assert result["error"] == "No candles provided"
    assert result["candles_used"] == 0


def test_invalid_event_date_returns_failed():
    result = analyze_ticker_event_window(
        secid="SBER",
        candles=_sample_candles(),
        event_date="not-a-date",
    )

    assert result["status"] == "failed"
    assert result["error"] == "Invalid event date"


def test_no_before_candle_returns_null_before_values_and_note():
    result = analyze_ticker_event_window(
        secid="SBER",
        candles=_sample_candles(),
        event_date="2026-05-13",
    )

    assert result["status"] == "ok"
    assert result["price_before"] is None
    assert result["return_before_percent"] is None
    assert any("No candle before event date" in note for note in result["notes"])


def test_return_after_percent_calculation():
    result = analyze_ticker_event_window(
        secid="SBER",
        candles=_sample_candles(),
        event_date="2026-05-15",
    )

    assert result["return_after_percent"] == Decimal("4.761905")
    assert calculate_return_percent(
        start_price=Decimal("100"),
        end_price=Decimal("110"),
    ) == Decimal("10.000000")


def test_max_drawdown_after_percent_calculation():
    drawdown = calculate_max_drawdown_percent(
        event_price=Decimal("105"),
        after_candles=_sample_candles()[1:],
    )

    assert drawdown == Decimal("-6.666667")


def test_max_runup_after_percent_calculation():
    runup = calculate_max_runup_percent(
        event_price=Decimal("105"),
        after_candles=_sample_candles()[1:],
    )

    assert runup == Decimal("10.476190")


def test_volatility_after_percent_returns_value_when_enough_candles():
    volatility = calculate_volatility_percent(_sample_candles()[1:])

    assert volatility is not None
    assert volatility > Decimal("0")


def test_build_validation_summary_positive_expected_majority_positive():
    summary = build_validation_summary(
        ticker_results=[
            _ticker_result("SBER", Decimal("5")),
            _ticker_result("VTBR", Decimal("2")),
            _ticker_result("MOEX", Decimal("-1")),
        ],
        expected_direction="positive",
    )

    assert summary["overall_result"] == "supports"
    assert summary["positive_count"] == 2
    assert summary["negative_count"] == 1
    assert summary["best_ticker"] == "SBER"
    assert summary["worst_ticker"] == "MOEX"
    assert summary["average_return_after_percent"] == Decimal("2.000000")


def test_build_validation_summary_contradiction():
    summary = build_validation_summary(
        ticker_results=[
            _ticker_result("SBER", Decimal("-5")),
            _ticker_result("VTBR", Decimal("-2")),
            _ticker_result("MOEX", Decimal("1")),
        ],
        expected_direction="positive",
    )

    assert summary["overall_result"] == "contradicts"
    assert summary["positive_count"] == 1
    assert summary["negative_count"] == 2


def test_build_validation_summary_counts_failed_results():
    summary = build_validation_summary(
        ticker_results=[
            _ticker_result("SBER", Decimal("5")),
            {
                "secid": "VTBR",
                "status": "failed",
                "return_after_percent": None,
            },
        ],
        expected_direction="positive",
    )

    assert summary["overall_result"] == "supports"
    assert summary["failed_count"] == 1


def test_build_validation_summary_insufficient_data():
    summary = build_validation_summary(
        ticker_results=[
            {
                "secid": "SBER",
                "status": "failed",
                "return_after_percent": None,
            }
        ],
        expected_direction="positive",
    )

    assert summary["overall_result"] == "insufficient_data"
    assert summary["average_return_after_percent"] is None
    assert summary["best_ticker"] is None
    assert summary["worst_ticker"] is None


def test_normalize_candles_sorts_and_skips_invalid_items():
    candles = normalize_candles(
        [
            {"begin": "2026-05-16", "close": Decimal("110")},
            {"begin": "bad-date", "close": Decimal("120")},
            {"begin": "2026-05-15", "close": Decimal("105")},
            {"begin": "2026-05-17"},
        ]
    )

    assert [candle["begin"].isoformat() for candle in candles] == [
        "2026-05-15",
        "2026-05-16",
    ]


def test_find_event_candle_accepts_raw_candles_and_iso_datetime():
    candle = find_event_candle(
        candles=_sample_candles(),
        event_date="2026-05-15T10:30:00",
    )

    assert candle["begin"] == date(2026, 5, 15)
    assert candle["close"] == Decimal("105")


def test_summary_text_does_not_use_forbidden_words():
    summary = build_validation_summary(
        ticker_results=[
            _ticker_result("SBER", Decimal("5")),
            _ticker_result("VTBR", Decimal("-2")),
        ],
        expected_direction="neutral",
    )
    forbidden_words = [
        "точно",
        "гарантированно",
        "купить",
        "продать",
    ]
    text = summary["text"].lower()

    for word in forbidden_words:
        assert word not in text


def _sample_candles():
    return [
        {
            "begin": "2026-05-13",
            "open": Decimal("99"),
            "high": Decimal("101"),
            "low": Decimal("97"),
            "close": Decimal("100"),
            "volume": Decimal("100000"),
        },
        {
            "begin": "2026-05-15",
            "open": Decimal("102"),
            "high": Decimal("108"),
            "low": Decimal("100"),
            "close": Decimal("105"),
            "volume": Decimal("130000"),
        },
        {
            "begin": "2026-05-18",
            "open": Decimal("104"),
            "high": Decimal("107"),
            "low": Decimal("98"),
            "close": Decimal("103"),
            "volume": Decimal("125000"),
        },
        {
            "begin": "2026-05-19",
            "open": Decimal("104"),
            "high": Decimal("116"),
            "low": Decimal("102"),
            "close": Decimal("110"),
            "volume": Decimal("140000"),
        },
    ]


def _ticker_result(secid, return_after_percent):
    return {
        "secid": secid,
        "status": "ok",
        "return_after_percent": return_after_percent,
    }

