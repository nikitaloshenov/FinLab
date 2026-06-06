from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    __table_args__ = (
        CheckConstraint(
            "condition IN ('above', 'below')",
            name="ck_alert_condition",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    session_id: Mapped[str] = mapped_column(
        String(64),
        default="legacy-demo-session",
        index=True,
        nullable=False,
    )

    ticker_id: Mapped[int] = mapped_column(
        ForeignKey("tickers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    condition: Mapped[str] = mapped_column(String(16), nullable=False)

    target_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    ticker = relationship("Ticker")
    events: Mapped[list["AlertEvent"]] = relationship(
        back_populates="alert",
        cascade="all, delete-orphan",
    )


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    session_id: Mapped[str] = mapped_column(
        String(64),
        default="legacy-demo-session",
        index=True,
        nullable=False,
    )

    alert_id: Mapped[int] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    ticker_id: Mapped[int] = mapped_column(
        ForeignKey("tickers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    target_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)

    condition: Mapped[str] = mapped_column(String(16), nullable=False)

    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    alert: Mapped["Alert"] = relationship(back_populates="events")
    ticker = relationship("Ticker")
