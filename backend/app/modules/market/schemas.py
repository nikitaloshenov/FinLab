from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class TickerRead(BaseModel):
    id: int
    secid: str
    short_name: str | None = None
    name: str | None = None
    board: str
    market: str
    engine: str
    currency: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TickerListItem(BaseModel):
    id: int
    secid: str
    short_name: str | None = None
    latest_price: Decimal | None = None

    model_config = ConfigDict(from_attributes=True)


class MoexTickerData(BaseModel):
    secid: str
    short_name: str | None = None
    name: str | None = None

    board: str
    market: str
    engine: str

    currency: str | None = None
    price: Decimal | None = None

    model_config = ConfigDict(from_attributes=True)


class TickerPriceRead(BaseModel):
    secid: str
    short_name: str | None = None
    price: Decimal
    previous_price: Decimal | None = None
    source: str
    received_at: datetime
    market_time: datetime | None = None


class TickerRefreshResult(TickerPriceRead):
    saved: bool = True