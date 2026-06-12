from __future__ import annotations

import argparse
import sys

from app.core.database import SessionLocal
from app.modules.events.service import import_key_rate_decisions_to_events


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import legacy key_rate_decisions into generic v2 events.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and summarize the import without writing changes.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = import_key_rate_decisions_to_events(db, dry_run=args.dry_run)
    except Exception as error:
        db.rollback()
        print(f"Import key rate events failed: {error}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print("Import key rate events completed")
    print("event_type: key_rate_decision")
    print(f"legacy_decisions_total: {result.legacy_decisions_total}")
    print(f"events_created: {result.events_created}")
    print(f"events_updated: {result.events_updated}")
    print(f"event_values_upserted: {result.event_values_upserted}")
    print(f"event_targets_created: {result.event_targets_created}")
    print(f"event_targets_skipped: {result.event_targets_skipped}")
    print(f"skipped: {result.skipped}")
    print(f"event_type_id: {result.event_type_id}")
    print(f"status: {result.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
