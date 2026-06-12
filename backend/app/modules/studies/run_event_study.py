from __future__ import annotations

import argparse
import sys
from datetime import date

from app.core.database import SessionLocal
from app.modules.studies.service import (
    EventStudyError,
    EventStudyUnknownEventTypeError,
    EventStudyUnknownInstrumentError,
    run_event_study,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run v2 event-study over persisted events/candles.")
    parser.add_argument("--secid", required=True, help="MOEX security id, for example SBER.")
    parser.add_argument("--event-type", required=True, help="Event type code, for example key_rate_decision.")
    parser.add_argument(
        "--horizons",
        default="1,5,10,20",
        help="Comma-separated trading-day horizons, for example 1,5,10,20.",
    )
    parser.add_argument("--from", dest="date_from", help="Optional start event date YYYY-MM-DD.")
    parser.add_argument("--to", dest="date_to", help="Optional end event date YYYY-MM-DD.")
    parser.add_argument("--dry-run", action="store_true", help="Calculate and rollback DB writes.")

    args = parser.parse_args()

    try:
        horizons = _parse_horizons(args.horizons)
        date_from = date.fromisoformat(args.date_from) if args.date_from else None
        date_to = date.fromisoformat(args.date_to) if args.date_to else None
    except ValueError as error:
        print(f"Invalid argument: {error}", file=sys.stderr)
        return 2

    db = SessionLocal()
    try:
        result = run_event_study(
            db,
            secid=args.secid,
            event_type_code=args.event_type,
            horizons=horizons,
            date_from=date_from,
            date_to=date_to,
            dry_run=args.dry_run,
        )
    except (EventStudyUnknownInstrumentError, EventStudyUnknownEventTypeError, EventStudyError) as error:
        db.rollback()
        print(f"Event study failed: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        db.rollback()
        print(f"Unexpected event study error: {error}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print("Event study completed")
    print(f"study_run_id: {result.study_run_id}")
    print(f"secid: {result.secid}")
    print(f"event_type: {result.event_type}")
    print(f"events_total: {result.events_total}")
    print(f"events_processed: {result.events_processed}")
    print(f"events_skipped: {result.events_skipped}")
    print(f"horizons: {','.join(str(horizon) for horizon in result.horizons)}")
    print(f"results_created: {result.results_created}")
    print(f"summary_rows_created: {result.summary_rows_created}")
    print(f"status: {result.status}")

    for summary in result.summary:
        print(
            "summary "
            f"horizon={summary.horizon_trading_days} "
            f"sample={summary.sample_size} "
            f"skipped={summary.skipped_count} "
            f"avg={summary.average_return_percent} "
            f"median={summary.median_return_percent} "
            f"hit_rate={summary.hit_rate_percent} "
            f"best={summary.best_horizon_flag}",
        )

    return 0


def _parse_horizons(value: str) -> list[int]:
    horizons = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not horizons:
        raise ValueError("At least one horizon is required.")

    if any(horizon <= 0 for horizon in horizons):
        raise ValueError("Horizons must be positive integers.")

    return horizons


if __name__ == "__main__":
    raise SystemExit(main())
