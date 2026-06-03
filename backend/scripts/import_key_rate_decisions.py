from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.core.database import SessionLocal
from app.modules.hypotheses.key_rate_decisions_import_service import (
    import_key_rate_decisions_from_csv,
)
from app.modules.hypotheses.key_rate_decisions_importer import (
    KeyRateDecisionImportError,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import curated key rate decisions from CSV.",
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to CSV file, relative to backend directory or absolute.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and count changes without writing to the database.",
    )

    args = parser.parse_args()

    csv_path = Path(args.file)
    db = SessionLocal()

    try:
        summary = import_key_rate_decisions_from_csv(
            db,
            csv_path,
            dry_run=args.dry_run,
        )
    except KeyRateDecisionImportError as error:
        print(f"Import failed: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Unexpected import error: {error}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print("Key rate decisions import summary")
    print(f"processed: {summary['processed']}")
    print(f"created: {summary['created']}")
    print(f"updated: {summary['updated']}")
    print(f"skipped: {summary['skipped']}")
    print(f"dry_run: {summary['dry_run']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
