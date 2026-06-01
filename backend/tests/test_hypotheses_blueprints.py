import pytest

from app.modules.hypotheses.blueprints import (
    UnsupportedHypothesisBlueprintError,
    build_hypothesis_blueprint_report,
    get_hypothesis_blueprint,
    list_supported_blueprints,
)


def test_list_supported_blueprints_returns_non_empty_list():
    blueprints = list_supported_blueprints()

    assert blueprints
    assert {
        "event_type",
        "event_direction",
        "sector",
        "title",
    }.issubset(blueprints[0])


def test_get_hypothesis_blueprint_key_rate_cut_banks():
    blueprint = get_hypothesis_blueprint(
        event_type="key_rate",
        event_direction="rate_cut",
        sector="banks",
    )

    assert blueprint["event_type"] == "key_rate"
    assert blueprint["event_direction"] == "rate_cut"
    assert blueprint["sector"] == "banks"
    assert blueprint["title"]
    assert blueprint["suggested_alert_templates"]


def test_get_hypothesis_blueprint_is_case_insensitive():
    blueprint = get_hypothesis_blueprint(
        event_type=" KEY_RATE ",
        event_direction=" RATE_CUT ",
        sector=" BANKS ",
    )

    assert blueprint["event_type"] == "key_rate"
    assert blueprint["event_direction"] == "rate_cut"
    assert blueprint["sector"] == "banks"


def test_get_hypothesis_blueprint_unsupported_raises():
    with pytest.raises(UnsupportedHypothesisBlueprintError):
        get_hypothesis_blueprint(
            event_type="dividend",
            event_direction="increase",
            sector="banks",
        )


def test_banks_rate_cut_blueprint_contains_expected_mechanisms():
    blueprint = get_hypothesis_blueprint(
        event_type="key_rate",
        event_direction="rate_cut",
        sector="banks",
    )
    mechanism_ids = {mechanism["id"] for mechanism in blueprint["mechanisms"]}

    assert "funding_cost" in mechanism_ids
    assert "credit_demand" in mechanism_ids
    assert "net_interest_margin" in mechanism_ids
    assert "market_expectations" in mechanism_ids


def test_banks_rate_hike_blueprint_contains_expected_risk_mechanism():
    blueprint = get_hypothesis_blueprint(
        event_type="key_rate",
        event_direction="rate_hike",
        sector="banks",
    )
    mechanism_ids = {mechanism["id"] for mechanism in blueprint["mechanisms"]}

    assert (
        "asset_quality_risk" in mechanism_ids
        or "credit_slowdown" in mechanism_ids
    )


def test_blueprint_contains_analysis_sections():
    blueprint = get_hypothesis_blueprint(
        event_type="key_rate",
        event_direction="rate_cut",
        sector="broad_market",
    )

    assert blueprint["arguments_for"]
    assert blueprint["arguments_against"]
    assert blueprint["watch_factors"]
    assert blueprint["limitations"]


def test_build_hypothesis_blueprint_report_includes_user_context():
    report = build_hypothesis_blueprint_report(
        event_type="key_rate",
        event_direction="rate_cut",
        sector="banks",
        tickers=["sber", " vtbr "],
        user_hypothesis_text="Lower rates can support bank stocks.",
    )

    assert report["selected_tickers"] == ["SBER", "VTBR"]
    assert report["user_hypothesis_text"] == "Lower rates can support bank stocks."
    assert report["blueprint"]["sector"] == "banks"


def test_build_hypothesis_blueprint_report_metadata():
    report = build_hypothesis_blueprint_report(
        event_type="key_rate",
        event_direction="rate_hike",
        sector="broad_market",
    )

    assert report["metadata"]["source"] == "rule_based_blueprint"
    assert report["metadata"]["is_prediction"] is False
    assert report["metadata"]["requires_price_validation"] is True


def test_generated_blueprint_messages_do_not_use_forbidden_words():
    forbidden_words = [
        "точно",
        "гарантированно",
        "купить",
        "продать",
    ]

    payloads = [
        get_hypothesis_blueprint("key_rate", "rate_cut", "banks"),
        get_hypothesis_blueprint("key_rate", "rate_hike", "banks"),
        get_hypothesis_blueprint("key_rate", "rate_cut", "broad_market"),
        get_hypothesis_blueprint("key_rate", "rate_hike", "broad_market"),
    ]

    generated_text = " ".join(_collect_strings(payloads)).lower()

    for word in forbidden_words:
        assert word not in generated_text


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

