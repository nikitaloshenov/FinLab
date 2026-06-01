from datetime import date
from decimal import Decimal

import pytest

from app.modules.hypotheses.blueprints import UnsupportedHypothesisBlueprintError
from app.modules.hypotheses.report_composer import compose_hypothesis_report


def test_compose_hypothesis_report_success_for_banks_rate_cut():
    report = compose_hypothesis_report(
        event_type="key_rate",
        event_direction="rate_cut",
        sector="banks",
        tickers=["sber", " vtbr "],
        user_hypothesis_text="Lower rates may support banks.",
        event_date=date(2026, 5, 15),
        candles_by_ticker={
            "SBER": _positive_candles(),
            "VTBR": _positive_candles(),
        },
    )

    assert report["hypothesis"]["tickers"] == ["SBER", "VTBR"]
    assert report["hypothesis"]["event_date"] == "2026-05-15"
    assert report["hypothesis"]["user_hypothesis_text"] == (
        "Lower rates may support banks."
    )
    assert report["blueprint"]["sector"] == "banks"
    assert len(report["historical_validation"]["ticker_results"]) == 2
    assert report["assessment"]["overall_result"] == "supports"


def test_report_contains_main_sections_and_metadata():
    report = _compose_positive_report()

    assert report["hypothesis"]
    assert report["blueprint"]
    assert report["historical_validation"]["summary"]
    assert report["assessment"]
    assert report["metadata"]["source"] == "rule_based_hypothesis_report"
    assert report["metadata"]["is_prediction"] is False
    assert report["metadata"]["uses_blueprint"] is True
    assert report["metadata"]["uses_historical_validation"] is True


def test_assessment_supports_when_validation_supports():
    report = _compose_positive_report()

    assert report["assessment"]["overall_result"] == "supports"
    assert report["assessment"]["confidence"] == "medium"


def test_assessment_mixed_support_when_ticker_returns_are_mixed():
    report = compose_hypothesis_report(
        event_type="key_rate",
        event_direction="rate_cut",
        sector="banks",
        tickers=["SBER", "VTBR"],
        user_hypothesis_text=None,
        event_date="2026-05-15",
        candles_by_ticker={
            "SBER": _positive_candles(),
            "VTBR": _negative_candles(),
        },
    )

    assert report["assessment"]["overall_result"] == "mixed_support"
    assert report["assessment"]["confidence"] == "low"


def test_missing_candles_for_one_ticker_creates_failed_result():
    report = compose_hypothesis_report(
        event_type="key_rate",
        event_direction="rate_cut",
        sector="banks",
        tickers=["SBER", "VTBR"],
        user_hypothesis_text=None,
        event_date="2026-05-15",
        candles_by_ticker={
            "SBER": _positive_candles(),
        },
    )
    ticker_results = report["historical_validation"]["ticker_results"]
    vtbr_result = next(result for result in ticker_results if result["secid"] == "VTBR")

    assert vtbr_result["status"] == "failed"
    assert vtbr_result["error"] == "No candles provided"
    assert report["historical_validation"]["summary"]["failed_count"] == 1
    assert report["assessment"]["confidence"] == "low"


def test_empty_tickers_raises_value_error():
    with pytest.raises(ValueError):
        compose_hypothesis_report(
            event_type="key_rate",
            event_direction="rate_cut",
            sector="banks",
            tickers=[],
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
            tickers=["SBER"],
            user_hypothesis_text=None,
            event_date="2026-05-15",
            candles_by_ticker={
                "SBER": _positive_candles(),
            },
        )


def test_arguments_limitations_and_suggested_alerts_are_non_empty():
    report = _compose_positive_report()

    assert report["arguments_for"]
    assert report["arguments_against"]
    assert report["limitations"]
    assert report["watch_factors"]
    assert report["suggested_alerts"]


def test_invalid_event_date_results_in_insufficient_data_report():
    report = compose_hypothesis_report(
        event_type="key_rate",
        event_direction="rate_cut",
        sector="banks",
        tickers=["SBER"],
        user_hypothesis_text=None,
        event_date="invalid-date",
        candles_by_ticker={
            "SBER": _positive_candles(),
        },
    )

    assert report["assessment"]["overall_result"] == "insufficient_data"
    assert report["assessment"]["confidence"] == "low"
    assert report["historical_validation"]["ticker_results"][0]["error"] == (
        "Invalid event date"
    )


def test_expected_direction_is_case_insensitive():
    report = compose_hypothesis_report(
        event_type="key_rate",
        event_direction="rate_hike",
        sector="broad_market",
        tickers=["IMOEX"],
        user_hypothesis_text=None,
        event_date="2026-05-15",
        candles_by_ticker={
            "IMOEX": _negative_candles(),
        },
        expected_direction=" NEGATIVE ",
    )

    assert report["hypothesis"]["expected_direction"] == "negative"
    assert report["assessment"]["overall_result"] == "supports"


def test_report_strings_do_not_use_forbidden_words():
    report = _compose_positive_report()
    forbidden_words = [
        "точно",
        "гарантированно",
        "купить",
        "продать",
    ]
    generated_text = " ".join(_collect_strings(report)).lower()

    for word in forbidden_words:
        assert word not in generated_text


def _compose_positive_report():
    return compose_hypothesis_report(
        event_type="key_rate",
        event_direction="rate_cut",
        sector="banks",
        tickers=["SBER", "VTBR"],
        user_hypothesis_text="Lower rates may support banks.",
        event_date="2026-05-15",
        candles_by_ticker={
            "SBER": _positive_candles(),
            "VTBR": _positive_candles(),
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


def _negative_candles():
    return [
        {
            "begin": "2026-05-14",
            "open": Decimal("101"),
            "high": Decimal("102"),
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

