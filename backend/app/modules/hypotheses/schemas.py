from datetime import date, datetime
from decimal import Decimal
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


class KeyRateImpactAnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    main_ticker: str = Field(min_length=1, max_length=32)
    direction: Literal["rate_cut", "rate_hike", "rate_hold"]
    benchmark_ticker: str | None = None
    horizons: list[int] = Field(default_factory=lambda: [1, 3, 10, 30])
    only_official: bool = True
    include_events: bool = True
    max_events: int | None = Field(default=None, ge=1, le=200)

    @field_validator("main_ticker")
    @classmethod
    def validate_main_ticker(cls, ticker: str) -> str:
        normalized_ticker = ticker.strip().upper()

        if not normalized_ticker:
            raise ValueError("main_ticker cannot be empty")

        return normalized_ticker

    @field_validator("benchmark_ticker")
    @classmethod
    def validate_impact_benchmark_ticker(cls, ticker: str | None) -> str | None:
        if ticker is None:
            return None

        normalized_ticker = ticker.strip().upper()

        return normalized_ticker or None

    @field_validator("horizons")
    @classmethod
    def validate_horizons(cls, horizons: list[int]) -> list[int]:
        allowed_horizons = {1, 3, 10, 30}
        normalized_horizons = []

        for horizon in horizons:
            if horizon not in allowed_horizons:
                raise ValueError("horizons can contain only 1, 3, 10, 30")

            if horizon not in normalized_horizons:
                normalized_horizons.append(horizon)

        if not normalized_horizons:
            raise ValueError("horizons cannot be empty")

        return normalized_horizons


class KeyRateImpactV2AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    secid: str = Field(min_length=1, max_length=32)
    date_from: date | None = None
    date_to: date | None = None
    horizons: list[int] = Field(default_factory=lambda: [1, 5, 10, 20])
    auto_prepare_data: bool = True
    refresh_candles: bool = False

    @field_validator("secid")
    @classmethod
    def validate_secid(cls, secid: str) -> str:
        normalized_secid = secid.strip().upper()

        if not normalized_secid:
            raise ValueError("secid cannot be empty")

        return normalized_secid

    @field_validator("horizons")
    @classmethod
    def validate_v2_horizons(cls, horizons: list[int]) -> list[int]:
        normalized_horizons = []

        for horizon in horizons:
            if horizon <= 0:
                raise ValueError("horizons must contain only positive integers")
            if horizon > 60:
                raise ValueError("horizons must be less than or equal to 60")
            if horizon not in normalized_horizons:
                normalized_horizons.append(horizon)

        if not normalized_horizons:
            raise ValueError("horizons cannot be empty")

        return normalized_horizons

    @model_validator(mode="after")
    def validate_v2_dates(self):
        if self.date_from is not None and self.date_to is not None:
            if self.date_from > self.date_to:
                raise ValueError("date_from must be less than or equal to date_to")

        return self


class KeyRateImpactV2InstrumentResponse(BaseModel):
    secid: str
    name: str | None
    asset_type: str
    sector: str | None = None


class KeyRateImpactV2SummaryResponse(BaseModel):
    horizon_trading_days: int
    sample_size: int
    skipped_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    average_return_percent: Decimal | None
    median_return_percent: Decimal | None
    hit_rate_percent: Decimal | None
    best_horizon_flag: bool


class KeyRateImpactV2DataPreparationResponse(BaseModel):
    key_rate_events_ready: bool
    key_rate_events_importer_ran: bool
    candles_ready: bool
    candles_importer_ran: bool
    candles_rows_loaded: int
    required_from: date | None
    required_to: date | None


class KeyRateImpactV2SampleResultResponse(BaseModel):
    event_id: int
    horizon_trading_days: int
    event_price: Decimal | None
    horizon_price: Decimal | None
    return_percent: Decimal | None
    status: str
    skipped_reason: str | None


class KeyRateImpactV2AnalyzeResponse(BaseModel):
    study_run_id: int | None
    secid: str
    instrument: KeyRateImpactV2InstrumentResponse
    event_type: str
    events_total: int
    events_processed: int
    events_skipped: int
    horizons: list[int]
    summary: list[KeyRateImpactV2SummaryResponse]
    data_preparation: KeyRateImpactV2DataPreparationResponse
    status: str
    sample_results: list[KeyRateImpactV2SampleResultResponse] = Field(default_factory=list)


class KeyRateEventResponse(BaseModel):
    event_id: str
    event_date: date
    event_type: Literal["key_rate"]
    event_direction: Literal["rate_cut", "rate_hike", "rate_hold"]
    rate_before: Decimal | None
    rate_after: Decimal | None
    change_bps: int | None
    title: str
    description: str
    is_official: bool
    source_note: str


class KeyRateEventsListResponse(BaseModel):
    items: list[KeyRateEventResponse]


class KeyRateDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    decision_date: date
    meeting_date: date | None
    effective_date: date | None
    publication_datetime_msk: datetime | None
    rate_before: Decimal | None
    rate_after: Decimal | None
    change_bps: int | None
    direction: Literal["rate_cut", "rate_hike", "rate_hold"]
    title: str
    description: str | None
    is_scheduled: bool
    is_official: bool
    source_url: str | None
    source_title: str | None
    source_type: str | None
    source_note: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class KeyRateDecisionListResponse(BaseModel):
    items: list[KeyRateDecisionRead]
    total: int
    limit: int
    offset: int
