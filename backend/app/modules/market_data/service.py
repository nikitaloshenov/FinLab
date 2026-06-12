from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.modules.market.moex_client import MoexClient, MoexClientError
from app.modules.market_data.repository import (
    create_ingestion_run,
    finish_ingestion_run,
    get_data_source_by_code,
    get_preferred_instrument_by_secid,
    upsert_price_candles,
)


SUPPORTED_IMPORT_INTERVALS = {"1d"}


class MarketDataImportError(Exception):
    pass


class MarketDataInstrumentNotFoundError(MarketDataImportError):
    pass


class MarketDataUnsupportedIntervalError(MarketDataImportError):
    pass


@dataclass
class CandleImportResult:
    secid: str
    interval: str
    date_from: date
    date_to: date
    rows_loaded: int
    ingestion_run_id: int
    status: str


def import_daily_candles(
    db: Session,
    *,
    secid: str,
    date_from: date,
    date_to: date,
    interval: str = "1d",
    moex_client: MoexClient | None = None,
) -> CandleImportResult:
    normalized_interval = interval.strip().lower()

    if normalized_interval not in SUPPORTED_IMPORT_INTERVALS:
        raise MarketDataUnsupportedIntervalError(
            f"Unsupported candle interval for importer: {interval}. Only 1d is supported.",
        )

    if date_from > date_to:
        raise MarketDataImportError("date_from must be less than or equal to date_to.")

    instrument = get_preferred_instrument_by_secid(db, secid)
    if instrument is None:
        raise MarketDataInstrumentNotFoundError(
            f"Reference instrument {secid.strip().upper()} was not found.",
        )

    source = get_data_source_by_code(db, "moex")
    ingestion_run = create_ingestion_run(
        db,
        source_id=source.id if source is not None else None,
        ingestion_type="moex_daily_candles",
        params_json={
            "secid": instrument.secid,
            "interval": normalized_interval,
            "from": date_from.isoformat(),
            "to": date_to.isoformat(),
        },
    )
    db.commit()

    client = moex_client or MoexClient(
        engine=instrument.engine,
        market=instrument.market,
        board=instrument.board,
    )

    try:
        raw_candles = client.fetch_candles(
            secid=instrument.secid,
            interval=normalized_interval,
            from_date=date_from.isoformat(),
            till_date=date_to.isoformat(),
        )
        normalized_candles = [
            _normalize_candle(candle, interval=normalized_interval)
            for candle in raw_candles
        ]
        rows_loaded = upsert_price_candles(
            db,
            instrument_id=instrument.id,
            source_id=source.id if source is not None else None,
            ingestion_run_id=ingestion_run.id,
            candles=normalized_candles,
        )
        finish_ingestion_run(
            db,
            ingestion_run,
            status="success",
            rows_loaded=rows_loaded,
            rows_failed=0,
        )
        db.commit()
    except Exception as error:
        db.rollback()
        ingestion_run = db.merge(ingestion_run)
        finish_ingestion_run(
            db,
            ingestion_run,
            status="failed",
            rows_loaded=0,
            rows_failed=1,
            error_message=str(error),
        )
        db.commit()
        raise

    return CandleImportResult(
        secid=instrument.secid,
        interval=normalized_interval,
        date_from=date_from,
        date_to=date_to,
        rows_loaded=rows_loaded,
        ingestion_run_id=ingestion_run.id,
        status=ingestion_run.status,
    )


def _normalize_candle(candle: dict[str, Any], *, interval: str) -> dict[str, Any]:
    begin_at = _parse_begin_at(candle["begin"])

    return {
        "interval": interval,
        "begin_at": begin_at,
        "trading_date": begin_at.date(),
        "open": _to_decimal_or_none(candle.get("open")),
        "high": _to_decimal_or_none(candle.get("high")),
        "low": _to_decimal_or_none(candle.get("low")),
        "close": _to_decimal_or_none(candle.get("close")),
        "volume": _to_decimal_or_none(candle.get("volume")),
        "value": _to_decimal_or_none(candle.get("value")),
    }


def _parse_begin_at(value: str) -> datetime:
    normalized_value = value.replace(" ", "T")
    parsed = datetime.fromisoformat(normalized_value)

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed


def _to_decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))
