from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Ticker(Base):
    __tablename__ = "tickers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    secid: Mapped[str] = mapped_column(
        String(32),
        unique=True,    
        index=True,
        nullable=False,
    )

    short_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(512), nullable=True)

    board: Mapped[str] = mapped_column(String(32), default="TQBR", nullable=False)
    market: Mapped[str] = mapped_column(String(64), default="shares", nullable=False)
    engine: Mapped[str] = mapped_column(String(64), default="stock", nullable=False)

    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)

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

    latest_price: Mapped["TickerLatestPrice | None"] = relationship(
        back_populates="ticker",
        cascade="all, delete-orphan",
        uselist=False,
    )


class TickerLatestPrice(Base):
    __tablename__ = "ticker_latest_prices"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    ticker_id: Mapped[int] = mapped_column(
        ForeignKey("tickers.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    previous_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)

    source: Mapped[str] = mapped_column(String(32), default="moex", nullable=False)

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    market_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ticker: Mapped["Ticker"] = relationship(back_populates="latest_price")
