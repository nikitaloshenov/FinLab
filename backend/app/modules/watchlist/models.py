from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    __table_args__ = (
        UniqueConstraint(
            "user_key",
            "ticker_id",
            name="uq_watchlist_user_ticker",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    user_key: Mapped[str] = mapped_column(
        String(64),
        default="default",
        index=True,
        nullable=False,
    )

    ticker_id: Mapped[int] = mapped_column(
        ForeignKey("tickers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    ticker = relationship("Ticker")