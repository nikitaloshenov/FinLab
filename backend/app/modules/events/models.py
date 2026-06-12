from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EventType(Base):
    __tablename__ = "event_types"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_source_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    events: Mapped[list["Event"]] = relationship(back_populates="event_type")


class Event(Base):
    __tablename__ = "events"

    __table_args__ = (
        UniqueConstraint(
            "event_type_id",
            "event_date",
            "title",
            name="uq_events_event_type_event_date_title",
        ),
        Index("ix_events_event_type_event_date", "event_type_id", "event_date"),
        Index("ix_events_source_source_event_id", "source_id", "source_event_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    event_type_id: Mapped[int] = mapped_column(
        ForeignKey("event_types.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_event_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    event_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    event_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    direction: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    importance: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    event_type: Mapped["EventType"] = relationship(back_populates="events")
    values: Mapped[list["EventValue"]] = relationship(back_populates="event")
    targets: Mapped[list["EventTarget"]] = relationship(back_populates="event")


class EventValue(Base):
    __tablename__ = "event_values"

    __table_args__ = (
        UniqueConstraint("event_id", "key", name="uq_event_values_event_id_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    numeric_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    text_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    event: Mapped["Event"] = relationship(back_populates="values")


class EventTarget(Base):
    __tablename__ = "event_targets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    target_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    instrument_id: Mapped[int | None] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    issuer_id: Mapped[int | None] = mapped_column(
        ForeignKey("issuers.id", ondelete="CASCADE"),
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    event: Mapped["Event"] = relationship(back_populates="targets")


class BenchmarkConstituent(Base):
    __tablename__ = "benchmark_constituents"

    __table_args__ = (
        UniqueConstraint(
            "benchmark_id",
            "instrument_id",
            "valid_from",
            name="uq_benchmark_constituents_benchmark_instrument_valid_from",
        ),
        Index("ix_benchmark_constituents_benchmark_valid_from", "benchmark_id", "valid_from"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    benchmark_id: Mapped[int] = mapped_column(
        ForeignKey("benchmarks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    weight: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    valid_from: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
