from __future__ import annotations

import argparse
import sys
from datetime import date

from app.core.database import SessionLocal
from app.modules.market_data.service import (
    MarketDataImportError,
    import_daily_candles,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import daily MOEX candles into price_candles.")
    parser.add_argument("--secid", required=True, help="MOEX security id, for example SBER.")
    parser.add_argument("--from", dest="date_from", required=True, help="Start date YYYY-MM-DD.")
    parser.add_argument("--to", dest="date_to", required=True, help="End date YYYY-MM-DD.")
    parser.add_argument("--interval", default="1d", help="Candle interval. Only 1d is supported.")

    args = parser.parse_args()

    try:
        date_from = date.fromisoformat(args.date_from)
        date_to = date.fromisoformat(args.date_to)
    except ValueError as error:
        print(f"Invalid date: {error}", file=sys.stderr)
        return 2

    db = SessionLocal()
    try:
        result = import_daily_candles(
            db,
            secid=args.secid,
            date_from=date_from,
            date_to=date_to,
            interval=args.interval,
        )
    except MarketDataImportError as error:
        print(f"Import candles failed: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Unexpected import candles error: {error}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print("Import candles completed")
    print(f"secid: {result.secid}")
    print(f"interval: {result.interval}")
    print(f"from: {result.date_from.isoformat()}")
    print(f"to: {result.date_to.isoformat()}")
    print(f"rows_loaded: {result.rows_loaded}")
    print(f"ingestion_run_id: {result.ingestion_run_id}")
    print(f"status: {result.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
