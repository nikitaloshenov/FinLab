from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HypothesisAnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    user_hypothesis_text: str | None = None
    event_type: Literal["key_rate"]
    event_direction: Literal["rate_cut", "rate_hike"]
    sector: Literal["banks", "broad_market"]
    main_ticker: str = Field(min_length=1, max_length=32)
    benchmark_ticker: str | None = "IMOEX"
    event_date: date
    interval: Literal["1d"] = "1d"
    window_before_days: int = Field(default=20, ge=1, le=365)
    window_after_days: int = Field(default=20, ge=1, le=365)
    expected_direction: Literal["positive", "negative", "neutral"] = "positive"

    @field_validator("main_ticker")
    @classmethod
    def validate_main_ticker(cls, ticker: str) -> str:
        normalized_ticker = ticker.strip()

        if not normalized_ticker:
            raise ValueError("main_ticker cannot be empty")

        return normalized_ticker

    @field_validator("benchmark_ticker")
    @classmethod
    def validate_benchmark_ticker(cls, ticker: str | None) -> str | None:
        if ticker is None:
            return None

        normalized_ticker = ticker.strip()

        return normalized_ticker or None

    @model_validator(mode="after")
    def ignore_same_benchmark_as_main(self):
        if self.benchmark_ticker is None:
            return self

        if self.benchmark_ticker.upper() == self.main_ticker.upper():
            self.benchmark_ticker = None

        return self
