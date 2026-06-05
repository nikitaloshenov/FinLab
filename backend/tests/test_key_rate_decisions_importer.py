from datetime import date, datetime
from decimal import Decimal

import pytest

from app.modules.hypotheses.key_rate_decisions_importer import (
    KeyRateDecisionImportError,
    load_key_rate_decisions_csv,
    parse_bool,
    parse_decision_date,
    parse_decimal_rate,
    parse_key_rate_decision_csv_row,
    parse_optional_date,
)


def test_parse_decimal_rate_supports_dot_comma_and_percent():
    assert parse_decimal_rate("16.00") == Decimal("16.00")
    assert parse_decimal_rate("16,00") == Decimal("16.00")
    assert parse_decimal_rate("16%") == Decimal("16")
    assert parse_decimal_rate("16,00%") == Decimal("16.00")


def test_parse_bool_values():
    assert parse_bool("true") is True
    assert parse_bool("1") is True
    assert parse_bool("yes") is True
    assert parse_bool("y") is True
    assert parse_bool("да") is True
    assert parse_bool("false") is False
    assert parse_bool("0") is False
    assert parse_bool("no") is False
    assert parse_bool("n") is False
    assert parse_bool("нет") is False
    assert parse_bool("", default=True) is True


def test_parse_dates():
    assert parse_decision_date("2026-05-15") == date(2026, 5, 15)
    assert parse_optional_date("") is None
    assert parse_optional_date("2026-05-19") == date(2026, 5, 19)


@pytest.mark.parametrize(
    ("rate_before", "rate_after", "direction", "change_bps"),
    [
        ("16.00", "15.50", "rate_cut", -50),
        ("15.50", "16.00", "rate_hike", 50),
        ("16.00", "16.00", "rate_hold", 0),
    ],
)
def test_parse_row_calculates_direction_and_change_bps(
    rate_before,
    rate_after,
    direction,
    change_bps,
):
    data = parse_key_rate_decision_csv_row(
        {
            **_valid_row(),
            "rate_before": rate_before,
            "rate_after": rate_after,
            "direction": "",
            "change_bps": "",
        }
    )

    assert data["direction"] == direction
    assert data["change_bps"] == change_bps


def test_parse_row_supports_optional_dataset_fields():
    data = parse_key_rate_decision_csv_row(
        {
            **_valid_row(),
            "meeting_date": "2026-05-15",
            "effective_date": "2026-05-19",
            "publication_datetime_msk": "2026-05-15T13:30:00",
            "source_title": "Bank of Russia decision",
            "notes": "Curated row.",
        }
    )

    assert data["meeting_date"] == date(2026, 5, 15)
    assert data["effective_date"] == date(2026, 5, 19)
    assert data["publication_datetime_msk"] == datetime(2026, 5, 15, 13, 30)
    assert data["source_title"] == "Bank of Russia decision"
    assert data["notes"] == "Curated row."


def test_parse_row_rejects_invalid_direction():
    with pytest.raises(KeyRateDecisionImportError, match="Unsupported"):
        parse_key_rate_decision_csv_row(
            {
                **_valid_row(),
                "direction": "invalid",
            }
        )


def test_parse_row_rejects_missing_required_fields():
    with pytest.raises(KeyRateDecisionImportError, match="title is required"):
        parse_key_rate_decision_csv_row(
            {
                **_valid_row(),
                "title": "",
            },
            row_number=2,
        )


def test_parse_row_rejects_contradictory_direction():
    with pytest.raises(KeyRateDecisionImportError, match="Direction does not match"):
        parse_key_rate_decision_csv_row(
            {
                **_valid_row(),
                "rate_before": "16.00",
                "rate_after": "15.50",
                "direction": "rate_hike",
            }
        )


def test_parse_row_rejects_contradictory_change_bps():
    with pytest.raises(KeyRateDecisionImportError, match="change_bps does not match"):
        parse_key_rate_decision_csv_row(
            {
                **_valid_row(),
                "rate_before": "16.00",
                "rate_after": "15.50",
                "change_bps": "-25",
            }
        )


def test_parse_row_rejects_missing_source_url_for_official_row():
    with pytest.raises(KeyRateDecisionImportError, match="source_url is required"):
        parse_key_rate_decision_csv_row(
            {
                **_valid_row(),
                "source_url": "",
                "is_official": "true",
            }
        )


def test_load_key_rate_decisions_csv_parses_rows(tmp_path):
    csv_path = tmp_path / "decisions.csv"
    csv_path.write_text(
        "\n".join(
            [
                _csv_header(),
                _csv_row(decision_date="2026-05-15"),
            ]
        ),
        encoding="utf-8",
    )

    rows = load_key_rate_decisions_csv(csv_path)

    assert len(rows) == 1
    assert rows[0]["decision_date"] == date(2026, 5, 15)


def _valid_row():
    return {
        "decision_date": "2026-05-15",
        "meeting_date": "",
        "effective_date": "",
        "publication_datetime_msk": "",
        "rate_before": "16.00",
        "rate_after": "15.50",
        "change_bps": "-50",
        "direction": "rate_cut",
        "title": "Key rate decision",
        "description": "Official imported decision.",
        "is_scheduled": "true",
        "is_official": "true",
        "source_url": "https://www.cbr.ru/",
        "source_type": "official_curated",
        "source_title": "",
        "source_note": "Synthetic test row.",
        "notes": "",
    }


def _csv_header():
    return (
        "decision_date,meeting_date,effective_date,publication_datetime_msk,"
        "rate_before,rate_after,change_bps,direction,title,description,"
        "is_scheduled,is_official,source_url,source_type,source_title,"
        "source_note,notes"
    )


def _csv_row(decision_date):
    return (
        f"{decision_date},,,,16.00,15.50,-50,rate_cut,Key rate decision,"
        "Official imported decision.,true,true,https://www.cbr.ru/,"
        "official_curated,,Synthetic test row.,"
    )
