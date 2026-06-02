from datetime import date
from decimal import Decimal

import pytest

from app.modules.hypotheses.blueprints import UnsupportedHypothesisBlueprintError
from app.modules.hypotheses.report_composer import compose_hypothesis_report


def test_compose_hypothesis_report_success_with_main_and_benchmark():
    report = compose_hypothesis_report(
        event_type="key_rate",
        event_direction="rate_cut",
        sector="banks",
        main_ticker="sber",
        benchmark_ticker=" imoex ",
        user_hypothesis_text="Lower rates may support SBER.",
        event_date=date(2026, 5, 15),
        candles_by_ticker={
            "SBER": _positive_candles(),
            "IMOEX": _benchmark_candles(),
        },
    )

    assert report["hypothesis"]["main_ticker"] == "SBER"
    assert report["hypothesis"]["benchmark_ticker"] == "IMOEX"
    assert report["historical_validation"]["main_ticker_result"]["secid"] == "SBER"
    assert report["historical_validation"]["benchmark_result"]["secid"] == "IMOEX"
    assert report["historical_validation"]["relative_result"]["main_ticker"] == "SBER"
    assert report["assessment"]["overall_result"] == "supports"
    assert report["assessment"]["confidence"] == "medium"


def test_report_contains_main_sections_and_metadata():
    report = _compose_positive_report()

    assert report["hypothesis"]
    assert report["blueprint"]
    assert report["historical_validation"]["main_ticker_result"]
    assert report["assessment"]
    assert report["arguments_for"]
    assert report["arguments_against"]
    assert report["limitations"]
    assert report["metadata"]["source"] == "rule_based_hypothesis_report"
    assert report["metadata"]["is_prediction"] is False
    assert report["metadata"]["uses_blueprint"] is True
    assert report["metadata"]["uses_historical_validation"] is True


def test_relative_result_interprets_outperformance():
    report = _compose_positive_report()
    relative_result = report["historical_validation"]["relative_result"]

    assert relative_result["main_return_after_percent"] == Decimal("4.761905")
    assert relative_result["benchmark_return_after_percent"] == Decimal("0.952381")
    assert relative_result["relative_return_after_percent"] == Decimal("3.809524")
    assert relative_result["interpretation"] == "outperformed"


def test_assessment_does_not_support_near_zero_main_return():
    report = compose_hypothesis_report(
        event_type="key_rate",
        event_direction="rate_cut",
        sector="banks",
        main_ticker="SBER",
        benchmark_ticker="IMOEX",
        user_hypothesis_text=None,
        event_date="2026-05-15",
        candles_by_ticker={
            "SBER": _near_zero_candles(),
            "IMOEX": _benchmark_candles(),
        },
    )

    assert report["assessment"]["overall_result"] == "mixed_support"
    assert report["assessment"]["confidence"] == "low"


def test_negative_main_return_for_positive_expected_direction_contradicts():
    report = compose_hypothesis_report(
        event_type="key_rate",
        event_direction="rate_cut",
        sector="banks",
        main_ticker="SBER",
        benchmark_ticker="IMOEX",
        user_hypothesis_text=None,
        event_date="2026-05-15",
        candles_by_ticker={
            "SBER": _negative_candles(),
            "IMOEX": _benchmark_candles(),
        },
    )

    assert report["assessment"]["overall_result"] == "contradicts"
    assert report["assessment"]["confidence"] == "low"


def test_main_rises_but_underperforms_benchmark_is_mixed():
    report = compose_hypothesis_report(
        event_type="key_rate",
        event_direction="rate_cut",
        sector="banks",
        main_ticker="SBER",
        benchmark_ticker="IMOEX",
        user_hypothesis_text=None,
        event_date="2026-05-15",
        candles_by_ticker={
            "SBER": _positive_candles(),
            "IMOEX": _strong_benchmark_candles(),
        },
    )

    assert report["historical_validation"]["relative_result"]["interpretation"] == (
        "underperformed"
    )
    assert report["assessment"]["overall_result"] == "mixed_support"
    assert report["assessment"]["confidence"] == "low"


def test_benchmark_failure_keeps_report_and_adds_limitation():
    report = compose_hypothesis_report(
        event_type="key_rate",
        event_direction="rate_cut",
        sector="banks",
        main_ticker="SBER",
        benchmark_ticker="IMOEX",
        user_hypothesis_text=None,
        event_date="2026-05-15",
        candles_by_ticker={
            "SBER": _positive_candles(),
            "IMOEX": [],
        },
    )

    assert report["historical_validation"]["benchmark_result"]["status"] == "failed"
    assert report["historical_validation"]["relative_result"] is None
    assert "Benchmark validation was unavailable." in report["limitations"]
    assert report["assessment"]["overall_result"] == "supports"
    assert report["assessment"]["confidence"] == "low"


def test_same_benchmark_as_main_is_ignored():
    report = compose_hypothesis_report(
        event_type="key_rate",
        event_direction="rate_cut",
        sector="banks",
        main_ticker="SBER",
        benchmark_ticker="sber",
        user_hypothesis_text=None,
        event_date="2026-05-15",
        candles_by_ticker={
            "SBER": _positive_candles(),
        },
    )

    assert report["hypothesis"]["benchmark_ticker"] is None
    assert report["historical_validation"]["benchmark_result"] is None
    assert report["historical_validation"]["relative_result"] is None


def test_empty_main_ticker_raises_value_error():
    with pytest.raises(ValueError):
        compose_hypothesis_report(
            event_type="key_rate",
            event_direction="rate_cut",
            sector="banks",
            main_ticker=" ",
            benchmark_ticker="IMOEX",
            user_hypothesis_text=None,
            event_date="2026-05-15",
            candles_by_ticker={},
        )


def test_unsupported_blueprint_raises():
    with pytest.raises(UnsupportedHypothesisBlueprintError):
        compose_hypothesis_report(
            event_type="dividend",
            event_direction="increase",
            sector="banks",
            main_ticker="SBER",
            benchmark_ticker="IMOEX",
            user_hypothesis_text=None,
            event_date="2026-05-15",
            candles_by_ticker={
                "SBER": _positive_candles(),
            },
        )


def test_numeric_suggested_alerts_are_only_for_main_ticker():
    report = _compose_positive_report()
    numeric_alerts = [
        alert
        for alert in report["suggested_alerts"]
        if alert.get("source") == "hypothesis_report"
        and alert.get("target_price") is not None
    ]

    assert numeric_alerts
    assert {alert["secid"] for alert in numeric_alerts} == {"SBER"}


def test_report_strings_do_not_use_forbidden_words():
    report = _compose_positive_report()
    forbidden_words = [
        "точно",
        "гарантированно",
        "купить",
        "продать",
        "акция вырастет",
    ]
    generated_text = " ".join(_collect_strings(report)).lower()

    for word in forbidden_words:
        assert word not in generated_text


def _compose_positive_report():
    return compose_hypothesis_report(
        event_type="key_rate",
        event_direction="rate_cut",
        sector="banks",
        main_ticker="SBER",
        benchmark_ticker="IMOEX",
        user_hypothesis_text="Lower rates may support SBER.",
        event_date="2026-05-15",
        candles_by_ticker={
            "SBER": _positive_candles(),
            "IMOEX": _benchmark_candles(),
        },
    )


def _positive_candles():
    return [
        {
            "begin": "2026-05-14",
            "open": Decimal("99"),
            "high": Decimal("101"),
            "low": Decimal("98"),
            "close": Decimal("100"),
            "volume": Decimal("100000"),
        },
        {
            "begin": "2026-05-15",
            "open": Decimal("101"),
            "high": Decimal("106"),
            "low": Decimal("100"),
            "close": Decimal("105"),
            "volume": Decimal("120000"),
        },
        {
            "begin": "2026-05-18",
            "open": Decimal("105"),
            "high": Decimal("112"),
            "low": Decimal("104"),
            "close": Decimal("110"),
            "volume": Decimal("130000"),
        },
    ]


def _benchmark_candles():
    return [
        {
            "begin": "2026-05-14",
            "open": Decimal("100"),
            "high": Decimal("101"),
            "low": Decimal("99"),
            "close": Decimal("100"),
            "volume": Decimal("100000"),
        },
        {
            "begin": "2026-05-15",
            "open": Decimal("100"),
            "high": Decimal("106"),
            "low": Decimal("100"),
            "close": Decimal("105"),
            "volume": Decimal("120000"),
        },
        {
            "begin": "2026-05-18",
            "open": Decimal("105"),
            "high": Decimal("107"),
            "low": Decimal("104"),
            "close": Decimal("106"),
            "volume": Decimal("130000"),
        },
    ]


def _strong_benchmark_candles():
    return [
        {
            "begin": "2026-05-14",
            "open": Decimal("100"),
            "high": Decimal("101"),
            "low": Decimal("99"),
            "close": Decimal("100"),
            "volume": Decimal("100000"),
        },
        {
            "begin": "2026-05-15",
            "open": Decimal("100"),
            "high": Decimal("106"),
            "low": Decimal("100"),
            "close": Decimal("105"),
            "volume": Decimal("120000"),
        },
        {
            "begin": "2026-05-18",
            "open": Decimal("105"),
            "high": Decimal("125"),
            "low": Decimal("104"),
            "close": Decimal("120"),
            "volume": Decimal("130000"),
        },
    ]


def _negative_candles():
    return [
        {
            "begin": "2026-05-14",
            "open": Decimal("100"),
            "high": Decimal("101"),
            "low": Decimal("99"),
            "close": Decimal("100"),
            "volume": Decimal("100000"),
        },
        {
            "begin": "2026-05-15",
            "open": Decimal("100"),
            "high": Decimal("101"),
            "low": Decimal("95"),
            "close": Decimal("98"),
            "volume": Decimal("120000"),
        },
        {
            "begin": "2026-05-18",
            "open": Decimal("98"),
            "high": Decimal("99"),
            "low": Decimal("90"),
            "close": Decimal("92"),
            "volume": Decimal("130000"),
        },
    ]


def _near_zero_candles():
    return [
        {
            "begin": "2026-05-14",
            "open": Decimal("100"),
            "high": Decimal("101"),
            "low": Decimal("99"),
            "close": Decimal("100"),
            "volume": Decimal("100000"),
        },
        {
            "begin": "2026-05-15",
            "open": Decimal("100"),
            "high": Decimal("101"),
            "low": Decimal("99"),
            "close": Decimal("100"),
            "volume": Decimal("120000"),
        },
        {
            "begin": "2026-05-18",
            "open": Decimal("100"),
            "high": Decimal("101"),
            "low": Decimal("99"),
            "close": Decimal("100.2"),
            "volume": Decimal("130000"),
        },
    ]


def _collect_strings(value):
    if isinstance(value, str):
        return [value]

    if isinstance(value, dict):
        strings = []
        for item in value.values():
            strings.extend(_collect_strings(item))
        return strings

    if isinstance(value, list):
        strings = []
        for item in value:
            strings.extend(_collect_strings(item))
        return strings

    return []

