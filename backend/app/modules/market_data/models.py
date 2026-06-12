from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


json_type = JSON().with_variant(JSONB, "postgresql")


class TradingCalendar(Base):
    __tablename__ = "trading_calendar"

    __table_args__ = (
        UniqueConstraint(
            "market_code",
            "trading_date",
            name="uq_trading_calendar_market_code_trading_date",
        ),
        Index("ix_trading_calendar_market_date", "market_code", "trading_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    market_code: Mapped[str] = mapped_column(String(32), default="moex", nullable=False)
    trading_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    is_trading_day: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        index=True,
        nullable=False,
    )
    session_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    __table_args__ = (
        Index("ix_ingestion_runs_source_started_at", "source_id", "started_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    ingestion_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    params_json: Mapped[dict[str, Any] | None] = mapped_column(json_type, nullable=True)
    rows_loaded: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    rows_failed: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    candles: Mapped[list["PriceCandle"]] = relationship(back_populates="ingestion_run")


class PriceCandle(Base):
    __tablename__ = "price_candles"

    __table_args__ = (
        UniqueConstraint(
            "instrument_id",
            "interval",
            "begin_at",
            name="uq_price_candles_instrument_interval_begin_at",
        ),
        Index("ix_price_candles_instrument_interval_begin_at", "instrument_id", "interval", "begin_at"),
        Index(
            "ix_price_candles_instrument_interval_trading_date",
            "instrument_id",
            "interval",
            "trading_date",
        ),
        Index("ix_price_candles_interval_trading_date", "interval", "trading_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"),
        nullable=False,
    )
    interval: Mapped[str] = mapped_column(String(16), nullable=False)
    begin_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    trading_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)

    open: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    high: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    low: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    close: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    volume: Mapped[Decimal | None] = mapped_column(Numeric(24, 6), nullable=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric(24, 6), nullable=True)

    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    ingestion_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingestion_runs.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    ingestion_run: Mapped["IngestionRun | None"] = relationship(back_populates="candles")
