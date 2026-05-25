from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class WatchlistItemCreate(BaseModel):
    secid: str = Field(min_length=1, max_length=32)


class WatchlistItemRead(BaseModel):
    id: int
    secid: str
    short_name: str | None = None
    latest_price: Decimal | None = None
    created_at: datetime


class WatchlistDeleteResult(BaseModel):
    secid: str
    deleted: bool = True


class WatchlistRefreshItemResult(BaseModel):
    secid: str
    success: bool
    price: Decimal | None = None
    error: str | None = None


class WatchlistRefreshResult(BaseModel):
    total: int
    updated: int
    failed: int
    items: list[WatchlistRefreshItemResult]