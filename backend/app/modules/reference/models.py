from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    license_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    loaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)

    issuer_sector_history: Mapped[list["IssuerSectorHistory"]] = relationship(
        back_populates="source",
    )


class Issuer(Base):
    __tablename__ = "issuers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(16), default="RU", nullable=True)
    website: Mapped[str | None] = mapped_column(String(1024), nullable=True)

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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    instruments: Mapped[list["Instrument"]] = relationship(back_populates="issuer")
    sector_history: Mapped[list["IssuerSectorHistory"]] = relationship(
        back_populates="issuer",
    )


class Instrument(Base):
    __tablename__ = "instruments"

    __table_args__ = (
        UniqueConstraint(
            "engine",
            "market",
            "board",
            "secid",
            name="uq_instruments_engine_market_board_secid",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    issuer_id: Mapped[int | None] = mapped_column(
        ForeignKey("issuers.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    secid: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    short_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    asset_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    board: Mapped[str] = mapped_column(String(32), nullable=False)
    market: Mapped[str] = mapped_column(String(64), nullable=False)
    engine: Mapped[str] = mapped_column(String(64), nullable=False)

    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    lot_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    isin: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)

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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    issuer: Mapped["Issuer | None"] = relationship(back_populates="instruments")
    benchmarks: Mapped[list["Benchmark"]] = relationship(back_populates="instrument")


class Sector(Base):
    __tablename__ = "sectors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        index=True,
        nullable=False,
    )

    issuer_history: Mapped[list["IssuerSectorHistory"]] = relationship(
        back_populates="sector",
    )
    benchmarks: Mapped[list["Benchmark"]] = relationship(back_populates="sector")


class IssuerSectorHistory(Base):
    __tablename__ = "issuer_sector_history"

    __table_args__ = (
        UniqueConstraint(
            "issuer_id",
            "sector_id",
            "valid_from",
            name="uq_issuer_sector_history_issuer_sector_valid_from",
        ),
        Index("ix_issuer_sector_history_issuer_valid_from", "issuer_id", "valid_from"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    issuer_id: Mapped[int] = mapped_column(
        ForeignKey("issuers.id", ondelete="CASCADE"),
        nullable=False,
    )
    sector_id: Mapped[int] = mapped_column(
        ForeignKey("sectors.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    valid_from: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )

    issuer: Mapped["Issuer"] = relationship(back_populates="sector_history")
    sector: Mapped["Sector"] = relationship(back_populates="issuer_history")
    source: Mapped["DataSource | None"] = relationship(
        back_populates="issuer_sector_history",
    )


class Benchmark(Base):
    __tablename__ = "benchmarks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    benchmark_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    instrument_id: Mapped[int | None] = mapped_column(
        ForeignKey("instruments.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    sector_id: Mapped[int | None] = mapped_column(
        ForeignKey("sectors.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        index=True,
        nullable=False,
    )

    instrument: Mapped["Instrument | None"] = relationship(back_populates="benchmarks")
    sector: Mapped["Sector | None"] = relationship(back_populates="benchmarks")
