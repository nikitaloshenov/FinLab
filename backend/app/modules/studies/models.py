from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


json_type = JSON().with_variant(JSONB, "postgresql")


class StudyRun(Base):
    __tablename__ = "study_runs"

    __table_args__ = (
        Index("ix_study_runs_study_type_created_at", "study_type", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    study_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("event_types.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    target_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_instrument_id: Mapped[int | None] = mapped_column(
        ForeignKey("instruments.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    target_issuer_id: Mapped[int | None] = mapped_column(
        ForeignKey("issuers.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_sector_id: Mapped[int | None] = mapped_column(
        ForeignKey("sectors.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    market_benchmark_id: Mapped[int | None] = mapped_column(
        ForeignKey("benchmarks.id", ondelete="SET NULL"),
        nullable=True,
    )
    sector_benchmark_id: Mapped[int | None] = mapped_column(
        ForeignKey("benchmarks.id", ondelete="SET NULL"),
        nullable=True,
    )

    params_json: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(64), nullable=False)
    data_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    data_cutoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    run_events: Mapped[list["StudyRunEvent"]] = relationship(back_populates="study_run")
    event_results: Mapped[list["StudyEventResult"]] = relationship(back_populates="study_run")
    benchmark_results: Mapped[list["StudyBenchmarkResult"]] = relationship(back_populates="study_run")
    comparisons: Mapped[list["StudyComparison"]] = relationship(back_populates="study_run")
    horizon_summaries: Mapped[list["StudyHorizonSummary"]] = relationship(back_populates="study_run")
    skipped_events: Mapped[list["StudySkippedEvent"]] = relationship(back_populates="study_run")


class StudyRunEvent(Base):
    __tablename__ = "study_run_events"

    __table_args__ = (
        UniqueConstraint("study_run_id", "event_id", name="uq_study_run_events_study_run_event"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    study_run_id: Mapped[int] = mapped_column(
        ForeignKey("study_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    skipped_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    study_run: Mapped["StudyRun"] = relationship(back_populates="run_events")


class StudyEventResult(Base):
    __tablename__ = "study_event_results"

    __table_args__ = (
        UniqueConstraint(
            "study_run_id",
            "event_id",
            "instrument_id",
            "horizon_trading_days",
            name="uq_study_event_results_run_event_instrument_horizon",
        ),
        Index("ix_study_event_results_run_horizon", "study_run_id", "horizon_trading_days"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    study_run_id: Mapped[int] = mapped_column(
        ForeignKey("study_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    horizon_trading_days: Mapped[int] = mapped_column(Integer, nullable=False)
    event_candle_id: Mapped[int | None] = mapped_column(
        ForeignKey("price_candles.id", ondelete="SET NULL"),
        nullable=True,
    )
    horizon_candle_id: Mapped[int | None] = mapped_column(
        ForeignKey("price_candles.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    horizon_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    return_percent: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    skipped_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    study_run: Mapped["StudyRun"] = relationship(back_populates="event_results")


class StudyBenchmarkResult(Base):
    __tablename__ = "study_benchmark_results"

    __table_args__ = (
        UniqueConstraint(
            "study_run_id",
            "event_id",
            "benchmark_id",
            "horizon_trading_days",
            name="uq_study_benchmark_results_run_event_benchmark_horizon",
        ),
        Index("ix_study_benchmark_results_run_horizon", "study_run_id", "horizon_trading_days"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    study_run_id: Mapped[int] = mapped_column(
        ForeignKey("study_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    benchmark_id: Mapped[int] = mapped_column(
        ForeignKey("benchmarks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    horizon_trading_days: Mapped[int] = mapped_column(Integer, nullable=False)
    benchmark_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    horizon_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    return_percent: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    skipped_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    study_run: Mapped["StudyRun"] = relationship(back_populates="benchmark_results")


class StudyComparison(Base):
    __tablename__ = "study_comparisons"

    __table_args__ = (
        UniqueConstraint(
            "study_run_id",
            "event_id",
            "instrument_id",
            "comparison_type",
            "horizon_trading_days",
            name="uq_study_comparisons_run_event_instrument_type_horizon",
        ),
        Index("ix_study_comparisons_run_horizon", "study_run_id", "horizon_trading_days"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    study_run_id: Mapped[int] = mapped_column(
        ForeignKey("study_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    benchmark_id: Mapped[int | None] = mapped_column(
        ForeignKey("benchmarks.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    comparison_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    horizon_trading_days: Mapped[int] = mapped_column(Integer, nullable=False)
    instrument_return_percent: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    benchmark_return_percent: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    relative_return_percent: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    skipped_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    study_run: Mapped["StudyRun"] = relationship(back_populates="comparisons")


class StudyHorizonSummary(Base):
    __tablename__ = "study_horizon_summary"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    study_run_id: Mapped[int] = mapped_column(
        ForeignKey("study_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    subject_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    instrument_id: Mapped[int | None] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    sector_id: Mapped[int | None] = mapped_column(
        ForeignKey("sectors.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    benchmark_id: Mapped[int | None] = mapped_column(
        ForeignKey("benchmarks.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    horizon_trading_days: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    positive_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    negative_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    neutral_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_return_percent: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    median_return_percent: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    hit_rate_percent: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    average_relative_return_percent: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    median_relative_return_percent: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    best_horizon_flag: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    study_run: Mapped["StudyRun"] = relationship(back_populates="horizon_summaries")


class StudySkippedEvent(Base):
    __tablename__ = "study_skipped_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    study_run_id: Mapped[int] = mapped_column(
        ForeignKey("study_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event_id: Mapped[int | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    reason_code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    reason_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_json: Mapped[dict[str, Any] | None] = mapped_column(json_type, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    study_run: Mapped["StudyRun"] = relationship(back_populates="skipped_events")
