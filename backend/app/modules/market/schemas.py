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