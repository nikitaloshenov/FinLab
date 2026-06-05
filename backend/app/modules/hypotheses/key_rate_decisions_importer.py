from __future__ import annotations

import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from app.modules.hypotheses.key_rate_decisions import (
    calculate_change_bps,
    calculate_key_rate_direction,
    normalize_key_rate_direction,
)


EXPECTED_COLUMNS = [
    "decision_date",
    "meeting_date",
    "effective_date",
    "publication_datetime_msk",
    "rate_before",
    "rate_after",
    "change_bps",
    "direction",
    "title",
    "description",
    "is_scheduled",
    "is_official",
    "source_url",
    "source_type",
    "source_title",
    "source_note",
    "notes",
]


class KeyRateDecisionImportError(Exception):
    pass


def normalize_empty(value) -> str | None:
    if value is None:
        return None

    normalized_value = str(value).strip()

    return normalized_value or None


def parse_decimal_rate(value) -> Decimal:
    normalized_value = normalize_empty(value)

    if normalized_value is None:
        raise KeyRateDecisionImportError("Decimal value is required.")

    cleaned_value = (
        normalized_value.replace("%", "")
        .replace(" ", "")
        .replace(",", ".")
        .strip()
    )

    try:
        return Decimal(cleaned_value)
    except InvalidOperation as error:
        raise KeyRateDecisionImportError(
            f"Invalid decimal value: {value!r}"
        ) from error


def parse_optional_decimal_rate(value) -> Decimal | None:
    if normalize_empty(value) is None:
        return None

    return parse_decimal_rate(value)


def parse_bool(value, default=None) -> bool | None:
    normalized_value = normalize_empty(value)

    if normalized_value is None:
        return default

    normalized_value = normalized_value.lower()

    if normalized_value in {"true", "1", "yes", "y", "да"}:
        return True

    if normalized_value in {"false", "0", "no", "n", "нет"}:
        return False

    raise KeyRateDecisionImportError(f"Invalid boolean value: {value!r}")


def parse_decision_date(value) -> date:
    normalized_value = normalize_empty(value)

    if normalized_value is None:
        raise KeyRateDecisionImportError("decision_date is required.")

    try:
        return date.fromisoformat(normalized_value)
    except ValueError as error:
        raise KeyRateDecisionImportError(
            f"Invalid date value: {value!r}. Expected YYYY-MM-DD."
        ) from error


def parse_optional_date(value) -> date | None:
    if normalize_empty(value) is None:
        return None

    return parse_decision_date(value)


def parse_optional_datetime_msk(value) -> datetime | None:
    normalized_value = normalize_empty(value)

    if normalized_value is None:
        return None

    try:
        return datetime.fromisoformat(normalized_value)
    except ValueError as error:
        raise KeyRateDecisionImportError(
            "Invalid publication_datetime_msk value: "
            f"{value!r}. Expected ISO datetime like 2024-10-25T13:30:00."
        ) from error


def parse_key_rate_decision_csv_row(
    row: dict,
    row_number: int | None = None,
) -> dict[str, Any]:
    try:
        data = {
            "decision_date": parse_decision_date(row.get("decision_date")),
            "meeting_date": parse_optional_date(row.get("meeting_date")),
            "effective_date": parse_optional_date(row.get("effective_date")),
            "publication_datetime_msk": parse_optional_datetime_msk(
                row.get("publication_datetime_msk")
            ),
            "rate_before": parse_decimal_rate(row.get("rate_before")),
            "rate_after": parse_decimal_rate(row.get("rate_after")),
            "title": _require_text(row.get("title"), field_name="title"),
            "description": normalize_empty(row.get("description")),
            "is_scheduled": parse_bool(row.get("is_scheduled"), default=True),
            "is_official": parse_bool(row.get("is_official"), default=True),
            "source_url": normalize_empty(row.get("source_url")),
            "source_type": normalize_empty(row.get("source_type"))
            or "official_curated",
            "source_title": normalize_empty(row.get("source_title")),
            "source_note": normalize_empty(row.get("source_note")),
            "notes": normalize_empty(row.get("notes")),
        }

        direction = normalize_empty(row.get("direction"))
        change_bps = normalize_empty(row.get("change_bps"))

        if direction is None:
            data["direction"] = calculate_key_rate_direction(
                data["rate_before"],
                data["rate_after"],
            )
        else:
            data["direction"] = normalize_key_rate_direction(direction)

        if change_bps is None:
            data["change_bps"] = calculate_change_bps(
                data["rate_before"],
                data["rate_after"],
            )
        else:
            data["change_bps"] = _parse_change_bps(change_bps)

        return validate_key_rate_decision_import_row(data)
    except (KeyRateDecisionImportError, ValueError) as error:
        raise KeyRateDecisionImportError(
            _with_row_number(str(error), row_number)
        ) from error


def load_key_rate_decisions_csv(path) -> list[dict[str, Any]]:
    csv_path = Path(path)

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        _validate_csv_header(reader.fieldnames)

        return [
            parse_key_rate_decision_csv_row(row, row_number=index)
            for index, row in enumerate(reader, start=2)
        ]


def validate_key_rate_decision_import_row(data: dict) -> dict:
    rate_before = data["rate_before"]
    rate_after = data["rate_after"]
    calculated_direction = calculate_key_rate_direction(rate_before, rate_after)
    calculated_change_bps = calculate_change_bps(rate_before, rate_after)

    if data["direction"] != calculated_direction:
        raise KeyRateDecisionImportError(
            "Direction does not match rate_before/rate_after: "
            f"direction={data['direction']} expected={calculated_direction}."
        )

    if data["change_bps"] != calculated_change_bps:
        raise KeyRateDecisionImportError(
            "change_bps does not match rate_before/rate_after: "
            f"change_bps={data['change_bps']} expected={calculated_change_bps}."
        )

    if data["change_bps"] > 0 and data["direction"] != "rate_hike":
        raise KeyRateDecisionImportError("Positive change_bps requires rate_hike.")

    if data["change_bps"] < 0 and data["direction"] != "rate_cut":
        raise KeyRateDecisionImportError("Negative change_bps requires rate_cut.")

    if data["change_bps"] == 0 and data["direction"] != "rate_hold":
        raise KeyRateDecisionImportError("Zero change_bps requires rate_hold.")

    if data["is_official"] is True and not data["source_url"]:
        raise KeyRateDecisionImportError("source_url is required for official rows.")

    return data


def _require_text(value, field_name: str) -> str:
    normalized_value = normalize_empty(value)

    if normalized_value is None:
        raise KeyRateDecisionImportError(f"{field_name} is required.")

    return normalized_value


def _parse_change_bps(value) -> int:
    normalized_value = normalize_empty(value)

    if normalized_value is None:
        raise KeyRateDecisionImportError("change_bps value is required.")

    try:
        return int(normalized_value)
    except ValueError as error:
        raise KeyRateDecisionImportError(
            f"Invalid change_bps value: {value!r}"
        ) from error


def _validate_csv_header(fieldnames) -> None:
    if not fieldnames:
        raise KeyRateDecisionImportError("CSV header is required.")

    missing_columns = [
        column for column in EXPECTED_COLUMNS if column not in fieldnames
    ]

    if missing_columns:
        raise KeyRateDecisionImportError(
            "CSV header is missing required columns: "
            + ", ".join(missing_columns)
        )


def _with_row_number(message: str, row_number: int | None) -> str:
    if row_number is None:
        return message

    return f"Row {row_number}: {message}"
