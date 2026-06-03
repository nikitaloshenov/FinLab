from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KeyRateDecision(Base):
    __tablename__ = "key_rate_decisions"

    __table_args__ = (
        CheckConstraint(
            "direction IN ('rate_cut', 'rate_hike', 'rate_hold')",
            name="ck_key_rate_decision_direction",
        ),
        Index("ix_key_rate_decisions_direction_decision_date", "direction", "decision_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    decision_date: Mapped[date] = mapped_column(
        Date,
        unique=True,
        index=True,
        nullable=False,
    )

    rate_before: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    rate_after: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    change_bps: Mapped[int | None] = mapped_column(Integer, nullable=True)

    direction: Mapped[str] = mapped_column(String(16), index=True, nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_scheduled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )
    is_official: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        index=True,
        nullable=False,
    )

    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_note: Mapped[str | None] = mapped_column(Text, nullable=True)

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
