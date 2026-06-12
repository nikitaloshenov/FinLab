from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.market_data.models import IngestionRun, PriceCandle
from app.modules.reference.models import DataSource, Instrument


def get_preferred_instrument_by_secid(db: Session, secid: str) -> Instrument | None:
    normalized_secid = secid.strip().upper()
    instruments = db.scalars(
        select(Instrument).where(func.upper(Instrument.secid) == normalized_secid),
    ).all()

    if not instruments:
        return None

    return sorted(
        instruments,
        key=lambda instrument: (
            not instrument.is_active,
            instrument.board != "TQBR",
            instrument.id,
        ),
    )[0]


def get_data_source_by_code(db: Session, code: str) -> DataSource | None:
    return db.scalar(select(DataSource).where(DataSource.code == code))


def create_ingestion_run(
    db: Session,
    *,
    source_id: int | None,
    ingestion_type: str,
    params_json: dict[str, Any],
) -> IngestionRun:
    ingestion_run = IngestionRun(
        source_id=source_id,
        ingestion_type=ingestion_type,
        status="running",
        started_at=datetime.now(UTC),
        params_json=params_json,
        rows_loaded=0,
        rows_failed=0,
    )
    db.add(ingestion_run)
    db.flush()
    return ingestion_run


def finish_ingestion_run(
    db: Session,
    ingestion_run: IngestionRun,
    *,
    status: str,
    rows_loaded: int = 0,
    rows_failed: int = 0,
    error_message: str | None = None,
) -> IngestionRun:
    ingestion_run.status = status
    ingestion_run.finished_at = datetime.now(UTC)
    ingestion_run.rows_loaded = rows_loaded
    ingestion_run.rows_failed = rows_failed
    ingestion_run.error_message = error_message
    db.flush()
    return ingestion_run


def upsert_price_candles(
    db: Session,
    *,
    instrument_id: int,
    source_id: int | None,
    ingestion_run_id: int,
    candles: list[dict[str, Any]],
) -> int:
    rows_loaded = 0

    for candle in candles:
        existing = db.scalar(
            select(PriceCandle).where(
                PriceCandle.instrument_id == instrument_id,
                PriceCandle.interval == candle["interval"],
                PriceCandle.begin_at == candle["begin_at"],
            ),
        )

        values = {
            "trading_date": candle["trading_date"],
            "open": _to_decimal_or_none(candle.get("open")),
            "high": _to_decimal_or_none(candle.get("high")),
            "low": _to_decimal_or_none(candle.get("low")),
            "close": _to_decimal_or_none(candle.get("close")),
            "volume": _to_decimal_or_none(candle.get("volume")),
            "value": _to_decimal_or_none(candle.get("value")),
            "source_id": source_id,
            "ingestion_run_id": ingestion_run_id,
        }

        if existing is None:
            db.add(
                PriceCandle(
                    instrument_id=instrument_id,
                    interval=candle["interval"],
                    begin_at=candle["begin_at"],
                    **values,
                ),
            )
        else:
            for field_name, value in values.items():
                setattr(existing, field_name, value)

        rows_loaded += 1

    db.flush()
    return rows_loaded


def _to_decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))
