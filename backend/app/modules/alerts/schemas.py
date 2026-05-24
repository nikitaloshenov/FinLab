from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class AlertCreate(BaseModel):
    secid: str = Field(min_length=1, max_length=32)
    condition: Literal["above", "below"]
    target_price: Decimal = Field(gt=0)


class AlertRead(BaseModel):
    id: int
    secid: str
    short_name: str | None = None
    condition: Literal["above", "below"]
    target_price: Decimal
    is_active: bool
    triggered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AlertDeleteResult(BaseModel):
    id: int
    deleted: bool = True


class AlertDisableResult(BaseModel):
    id: int
    is_active: bool = False


class AlertCheckResult(BaseModel):
    alert_id: int
    secid: str
    condition: Literal["above", "below"]
    target_price: Decimal
    current_price: Decimal
    triggered: bool
    is_active: bool
    message: str | None = None


class AlertEventRead(BaseModel):
    id: int
    alert_id: int
    secid: str
    price: Decimal
    target_price: Decimal
    condition: str
    message: str | None = None
    created_at: datetime