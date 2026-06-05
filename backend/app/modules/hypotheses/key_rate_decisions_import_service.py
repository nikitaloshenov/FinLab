from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.modules.hypotheses.key_rate_decisions_importer import (
    KeyRateDecisionImportError,
    load_key_rate_decisions_csv,
)
from app.modules.hypotheses.key_rate_decisions_repository import (
    get_key_rate_decision_by_date,
    upsert_key_rate_decision_by_date,
)


def import_key_rate_decisions_from_csv(
    db: Session,
    path,
    dry_run: bool = False,
) -> dict:
    rows = load_key_rate_decisions_csv(Path(path))
    _validate_no_duplicate_decision_dates(rows)

    created = 0
    updated = 0

    for row in rows:
        existing_decision = get_key_rate_decision_by_date(
            db,
            row["decision_date"],
        )

        if existing_decision is None:
            created += 1
        else:
            updated += 1

    summary = {
        "processed": len(rows),
        "created": created,
        "updated": updated,
        "skipped": 0,
        "errors": [],
        "dry_run": dry_run,
    }

    if dry_run:
        return summary

    try:
        for row in rows:
            upsert_key_rate_decision_by_date(db, row)

        db.commit()
    except Exception:
        db.rollback()
        raise

    return summary


def _validate_no_duplicate_decision_dates(rows: list[dict]) -> None:
    seen_dates = set()

    for row in rows:
        decision_date = row["decision_date"]

        if decision_date in seen_dates:
            raise KeyRateDecisionImportError(
                f"Duplicate decision_date in CSV: {decision_date.isoformat()}"
            )

        seen_dates.add(decision_date)
