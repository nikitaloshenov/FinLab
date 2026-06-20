from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.hypotheses.blueprints import UnsupportedHypothesisBlueprintError
from app.modules.hypotheses.key_rate_decisions_service import list_decisions
from app.modules.hypotheses.key_rate_events import list_key_rate_events
from app.modules.hypotheses.key_rate_impact_service import (
    KeyRateImpactMainTickerCandlesError,
    analyze_key_rate_impact,
)
from app.modules.hypotheses.key_rate_v2_service import (
    KeyRateV2DataNotPreparedError,
    KeyRateV2PreparationError,
    KeyRateV2UnknownInstrumentError,
    analyze_key_rate_impact_v2,
)
from app.modules.hypotheses.schemas import (
    HypothesisAnalyzeRequest,
    KeyRateDecisionListResponse,
    KeyRateEventsListResponse,
    KeyRateImpactAnalyzeRequest,
    KeyRateImpactV2AnalyzeRequest,
    KeyRateImpactV2AnalyzeResponse,
)
from app.modules.hypotheses.service import analyze_hypothesis
from app.shared.errors import raise_api_error


router = APIRouter(
    prefix="/hypotheses",
    tags=["Hypotheses"],
)


@router.get("/key-rate-events", response_model=KeyRateEventsListResponse)
def list_key_rate_events_endpoint(
    direction: Literal["rate_cut", "rate_hike", "rate_hold"] | None = Query(
        default=None,
    ),
    only_official: bool | None = Query(default=None),
):
    return {
        "items": jsonable_encoder(
            list_key_rate_events(
                direction=direction,
                only_official=only_official,
            )
        ),
    }


@router.get("/key-rate-decisions", response_model=KeyRateDecisionListResponse)
def list_key_rate_decisions_endpoint(
    direction: Literal["rate_cut", "rate_hike", "rate_hold"] | None = Query(
        default=None,
    ),
    only_official: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return list_decisions(
        db,
        direction=direction,
        only_official=only_official,
        limit=limit,
        offset=offset,
    )


@router.post("/analyze")
def analyze_hypothesis_endpoint(request: HypothesisAnalyzeRequest):
    try:
        return jsonable_encoder(analyze_hypothesis(request))
    except UnsupportedHypothesisBlueprintError as error:
        raise_api_error(
            status_code=400,
            code="unsupported_hypothesis_blueprint",
            message=str(error),
        )


@router.post("/key-rate-impact/analyze")
def analyze_key_rate_impact_endpoint(
    request: KeyRateImpactAnalyzeRequest,
    db: Session = Depends(get_db),
):
    try:
        return jsonable_encoder(analyze_key_rate_impact(db, request))
    except KeyRateImpactMainTickerCandlesError as error:
        raise_api_error(
            status_code=502,
            code="key_rate_impact_market_data_unavailable",
            message=str(error),
        )


@router.post("/key-rate-impact/v2", response_model=KeyRateImpactV2AnalyzeResponse)
def analyze_key_rate_impact_v2_endpoint(
    request: KeyRateImpactV2AnalyzeRequest,
    db: Session = Depends(get_db),
):
    try:
        return jsonable_encoder(
            analyze_key_rate_impact_v2(
                db,
                secid=request.secid,
                date_from=request.date_from,
                date_to=request.date_to,
                horizons=request.horizons,
                auto_prepare_data=request.auto_prepare_data,
                refresh_candles=request.refresh_candles,
                include_sector_comparison=request.include_sector_comparison,
                sector_peer_limit=request.sector_peer_limit,
                auto_prepare_sector_data=request.auto_prepare_sector_data,
            )
        )
    except KeyRateV2UnknownInstrumentError as error:
        raise_api_error(
            status_code=404,
            code="key_rate_v2_unknown_instrument",
            message=str(error),
        )
    except KeyRateV2DataNotPreparedError as error:
        raise_api_error(
            status_code=409,
            code="key_rate_v2_data_not_prepared",
            message=str(error),
        )
    except KeyRateV2PreparationError as error:
        raise_api_error(
            status_code=502,
            code="key_rate_v2_data_preparation_failed",
            message=str(error),
        )
