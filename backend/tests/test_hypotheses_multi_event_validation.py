from datetime import date, datetime
from decimal import Decimal

from app.modules.hypotheses.multi_event_validation import (
    analyze_key_rate_multi_event_reaction,
    analyze_single_decision_reaction,
    build_horizon_summary,
    calculate_return_percent,
    classify_return_strength,
    find_event_trading_day,
    find_horizon_candle,
    normalize_candles,
)


def test_normalize_candles_sorts_dates_and_skips_invalid_rows():
    candles = normalize_candles(
        [
            {"begin": datetime(2024, 7, 29, 10, 0), "close": "103"},
            {"begin": "bad-date", "close": "999"},
            {"begin": date(2024, 7, 25), "close": Decimal("100")},
            {"begin": "2024-07-26T00:00:00", "close": "101"},
            {"begin": "2024-07-30"},
        ]
    )

    assert [candle["begin"].isoformat() for candle in candles] == [
        "2024-07-25",
        "2024-07-26",
        "2024-07-29",
    ]
    assert candles[0]["close"] == Decimal("100")


def test_event_anchor_uses_event_day_candle():
    candles = normalize_candles(_stock_candles())
    event_candle = find_event_trading_day(candles, date(2024, 7, 26))

    assert event_candle["begin"] == date(2024, 7, 26)
    assert event_candle["close"] == Decimal("101")


def test_event_anchor_on_non_trading_day_uses_next_trading_day():
    candles = normalize_candles(_stock_candles())
    event_candle = find_event_trading_day(candles, "2024-07-27")

    assert event_candle["begin"] == date(2024, 7, 29)
    assert event_candle["close"] == Decimal("103")


def test_first_available_event_candle_does_not_require_previous_baseline():
    result = analyze_single_decision_reaction(
        decision=_decision("2024-07-25"),
        stock_candles=_stock_candles(),
        horizons=(1,),
    )

    assert result["status"] == "ok"
    assert result["event_trading_date"] == "2024-07-25"
    assert result["baseline_date"] is None
    assert result["event_price"] == Decimal("100")
    assert result["horizons"][0]["stock_return_percent"] == Decimal("1.000000")


def test_horizon_logic_calculates_trading_day_returns():
    candles = normalize_candles(_stock_candles())
    event_candle = find_event_trading_day(candles, "2024-07-26")

    assert find_horizon_candle(candles, event_candle, 1)["begin"] == date(
        2024, 7, 29
    )
    assert find_horizon_candle(candles, event_candle, 3)["begin"] == date(
        2024, 7, 31
    )
    assert calculate_return_percent(
        Decimal("100"),
        Decimal("108"),
    ) == Decimal("8.000000")


def test_insufficient_horizon_data_marks_horizon_skipped():
    result = analyze_single_decision_reaction(
        decision=_decision("2024-07-26"),
        stock_candles=_stock_candles(),
        horizons=(1, 30),
    )

    assert result["status"] == "partial"
    assert result["horizons"][0]["status"] == "ok"
    assert result["horizons"][1]["status"] == "skipped"
    assert result["horizons"][1]["skip_reason"] == "missing_horizon_candle"


def test_return_classification_thresholds():
    assert classify_return_strength(Decimal("0.50"))["effect_type"] == (
        "market_noise"
    )
    assert classify_return_strength(Decimal("2.00"))["effect_type"] == (
        "weak_growth"
    )
    assert classify_return_strength(Decimal("4.00"))["effect_type"] == (
        "moderate_growth"
    )
    assert classify_return_strength(Decimal("6.00"))["effect_type"] == (
        "strong_growth"
    )
    assert classify_return_strength(Decimal("-2.00"))["effect_type"] == (
        "weak_decline"
    )
    assert classify_return_strength(Decimal("-4.00"))["effect_type"] == (
        "moderate_decline"
    )
    assert classify_return_strength(Decimal("-6.00"))["effect_type"] == (
        "strong_decline"
    )


def test_single_decision_reaction_returns_event_row():
    result = analyze_single_decision_reaction(
        decision=_decision("2024-07-26"),
        stock_candles=_stock_candles(),
        horizons=(1, 3),
    )

    assert result["decision_date"] == "2024-07-26"
    assert result["event_trading_date"] == "2024-07-26"
    assert result["baseline_date"] is None
    assert result["event_price"] == Decimal("101")
    assert result["status"] == "ok"
    assert result["horizons"][0]["stock_return_percent"] == Decimal("1.980198")
    assert result["horizons"][1]["stock_return_percent"] == Decimal("6.930693")


def test_missing_event_candle_skips_without_fake_zero_return():
    result = analyze_single_decision_reaction(
        decision=_decision("2024-09-01"),
        stock_candles=_stock_candles(),
        horizons=(1,),
    )

    assert result["status"] == "skipped"
    assert result["skip_reason"] == "missing_event_candle"
    assert result["horizons"][0]["stock_return_percent"] is None


def test_empty_candles_skip_without_fake_zero_return():
    result = analyze_single_decision_reaction(
        decision=_decision("2024-07-26"),
        stock_candles=[],
        horizons=(1,),
    )

    assert result["status"] == "skipped"
    assert result["skip_reason"] == "empty_candles"
    assert result["horizons"][0]["stock_return_percent"] is None


def test_horizon_summary_aggregates_counts_and_returns():
    event_results = [
        _event_result(1, Decimal("4")),
        _event_result(1, Decimal("-2")),
        _event_result(1, Decimal("0.5")),
        _event_result(1, Decimal("6")),
        _event_result(1, None),
    ]

    summary = build_horizon_summary(event_results, horizons=(1,))[0]

    assert summary["events_total"] == 5
    assert summary["events_with_data"] == 4
    assert summary["skipped_events"] == 1
    assert summary["positive_count"] == 2
    assert summary["negative_count"] == 1
    assert summary["neutral_count"] == 1
    assert summary["average_return_percent"] == Decimal("2.125000")
    assert summary["median_return_percent"] == Decimal("2.250000")
    assert summary["min_return_percent"] == Decimal("-2")
    assert summary["max_return_percent"] == Decimal("6")
    assert summary["typical_direction"] == "positive"


def test_multi_event_report_shape_and_skipped_counts():
    report = analyze_key_rate_multi_event_reaction(
        main_ticker="sber",
        decisions=[
            _decision("2024-07-26"),
            _decision("2024-08-02"),
            _decision("2024-08-09"),
            _decision("2024-09-01"),
        ],
        stock_candles=_long_stock_candles(),
        horizons=(1, 3, 10, 30),
    )

    assert report["main_ticker"] == "SBER"
    assert report["benchmark_ticker"] is None
    assert report["decisions_total"] == 4
    assert report["decisions_used"] == 3
    assert report["decisions_skipped"] == 1
    assert [item["horizon_days"] for item in report["horizon_summary"]] == [
        1,
        3,
        10,
        30,
    ]
    assert report["metadata"]["source"] == "multi_event_validation"
    assert report["metadata"]["is_prediction"] is False


def test_benchmark_returns_and_relative_summary_are_calculated():
    report = analyze_key_rate_multi_event_reaction(
        main_ticker="SBER",
        decisions=[_decision("2024-07-26"), _decision("2024-08-02")],
        stock_candles=_long_stock_candles(),
        horizons=(1,),
        benchmark_ticker="IMOEX",
        benchmark_candles=_benchmark_candles(),
    )

    first_horizon = report["event_results"][0]["horizons"][0]
    benchmark_summary = report["benchmark_summary"][0]

    assert first_horizon["stock_return_percent"] == Decimal("1.980198")
    assert first_horizon["benchmark_return_percent"] == Decimal("1.000000")
    assert first_horizon["relative_return_percent"] == Decimal("0.980198")
    assert benchmark_summary["benchmark_events_with_data"] == 2
    assert benchmark_summary["average_relative_return_percent"] == Decimal(
        "0.906766"
    )
    assert benchmark_summary["outperformed_count"] == 0


def test_missing_benchmark_data_does_not_fail_report():
    report = analyze_key_rate_multi_event_reaction(
        main_ticker="SBER",
        decisions=[_decision("2024-07-26")],
        stock_candles=_stock_candles(),
        horizons=(1,),
        benchmark_ticker="IMOEX",
        benchmark_candles=None,
    )

    assert report["benchmark_summary"] is None
    assert any("Benchmark comparison" in item for item in report["limitations"])


def test_limitations_include_small_sample_skipped_and_disruption_notes():
    report = analyze_key_rate_multi_event_reaction(
        main_ticker="SBER",
        decisions=[
            _decision(
                "2024-07-26",
                notes="Extraordinary crisis decision; market disruption.",
            ),
            _decision("2024-09-01"),
        ],
        stock_candles=_stock_candles(),
        horizons=(1,),
    )

    assert "Small number of events limits confidence." in report["limitations"]
    assert (
        "Some events were skipped because of missing candles."
        in report["limitations"]
    )
    assert (
        "Some events are marked as extraordinary or market disruption."
        in report["limitations"]
    )


def test_generated_strings_do_not_contain_forbidden_words():
    report = analyze_key_rate_multi_event_reaction(
        main_ticker="SBER",
        decisions=[_decision("2024-07-26")],
        stock_candles=_stock_candles(),
        horizons=(1,),
    )
    forbidden_words = [
        "точно",
        "гарантированно",
        "купить",
        "продать",
    ]
    text = str(report).lower()

    for word in forbidden_words:
        assert word not in text


def _decision(decision_date, notes=None):
    return {
        "decision_date": decision_date,
        "direction": "rate_hike",
        "rate_before": Decimal("16.00"),
        "rate_after": Decimal("18.00"),
        "change_bps": 200,
        "title": "Bank of Russia increases the key rate",
        "is_scheduled": True,
        "is_official": True,
        "notes": notes,
    }


def _stock_candles():
    return [
        _candle("2024-07-25", "100"),
        _candle("2024-07-26", "101"),
        _candle("2024-07-29", "103"),
        _candle("2024-07-30", "105"),
        _candle("2024-07-31", "108"),
    ]


def _long_stock_candles():
    return [
        _candle("2024-07-25", "100"),
        _candle("2024-07-26", "101"),
        _candle("2024-07-29", "103"),
        _candle("2024-07-30", "105"),
        _candle("2024-07-31", "108"),
        _candle("2024-08-01", "110"),
        _candle("2024-08-02", "112"),
        _candle("2024-08-05", "114"),
        _candle("2024-08-06", "115"),
        _candle("2024-08-07", "116"),
        _candle("2024-08-08", "117"),
        _candle("2024-08-09", "118"),
        _candle("2024-08-12", "119"),
        _candle("2024-08-13", "120"),
        _candle("2024-08-14", "121"),
        _candle("2024-08-15", "122"),
        _candle("2024-08-16", "123"),
        _candle("2024-08-19", "124"),
        _candle("2024-08-20", "125"),
        _candle("2024-08-21", "126"),
        _candle("2024-08-22", "127"),
    ]


def _benchmark_candles():
    return [
        _candle("2024-07-25", "100"),
        _candle("2024-07-26", "100"),
        _candle("2024-07-29", "101"),
        _candle("2024-07-30", "102"),
        _candle("2024-07-31", "103"),
        _candle("2024-08-01", "104"),
        _candle("2024-08-02", "105"),
        _candle("2024-08-05", "106"),
        _candle("2024-08-06", "107"),
    ]


def _candle(begin, close):
    close_value = Decimal(close)

    return {
        "begin": begin,
        "open": close_value,
        "high": close_value,
        "low": close_value,
        "close": close_value,
        "volume": Decimal("1000"),
    }


def _event_result(horizon_days, value):
    return {
        "status": "ok" if value is not None else "skipped",
        "horizons": [
            {
                "horizon_days": horizon_days,
                "stock_return_percent": value,
                "status": "ok" if value is not None else "skipped",
            }
        ],
    }
