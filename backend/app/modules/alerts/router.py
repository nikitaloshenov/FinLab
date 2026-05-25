from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.alerts.schemas import (
    AlertBatchCheckResult,
    AlertCheckResult,
    AlertCreate,
    AlertDeleteResult,
    AlertDisableResult,
    AlertEventRead,
    AlertRead,
)
from app.modules.alerts.service import (
    AlertLatestPriceNotFoundError,
    AlertNotFoundError,
    AlertTickerCreateError,
    check_active_price_alerts,
    check_price_alert,
    create_price_alert,
    disable_price_alert,
    list_alert_events,
    list_alerts,
    remove_price_alert,
)
from app.modules.market.moex_client import (
    MoexClientError,
    MoexTickerNotFoundError,
)
from app.modules.market.service import MarketPriceUnavailableError
from app.shared.errors import raise_api_error


router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"],
)


@router.get("", response_model=list[AlertRead])
def get_alerts_list(db: Session = Depends(get_db)):
    return list_alerts(db)


@router.post("", response_model=AlertRead)
def create_alert(
    alert_data: AlertCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_price_alert(
            db=db,
            secid=alert_data.secid,
            condition=alert_data.condition,
            target_price=alert_data.target_price,
        )
    except MoexTickerNotFoundError as error:
        raise_api_error(
            status_code=404,
            code="ticker_not_found",
            message=str(error),
        )
    except MarketPriceUnavailableError as error:
        raise_api_error(
            status_code=502,
            code="market_price_unavailable",
            message=str(error),
        )
    except MoexClientError as error:
        raise_api_error(
            status_code=502,
            code="moex_client_error",
            message=str(error),
        )
    except AlertTickerCreateError as error:
        raise_api_error(
            status_code=500,
            code="alert_ticker_create_error",
            message=str(error),
        )


@router.get("/events", response_model=list[AlertEventRead])
def get_alert_events_list(db: Session = Depends(get_db)):
    return list_alert_events(db)


@router.post("/check-active", response_model=AlertBatchCheckResult)
def check_active_alerts(db: Session = Depends(get_db)):
    return check_active_price_alerts(db)


@router.post("/{alert_id}/check", response_model=AlertCheckResult)
def check_alert(
    alert_id: int,
    db: Session = Depends(get_db),
):
    try:
        return check_price_alert(
            db=db,
            alert_id=alert_id,
        )
    except AlertNotFoundError as error:
        raise_api_error(
            status_code=404,
            code="alert_not_found",
            message=str(error),
        )
    except AlertLatestPriceNotFoundError as error:
        raise_api_error(
            status_code=404,
            code="alert_latest_price_not_found",
            message=str(error),
        )


@router.patch("/{alert_id}/disable", response_model=AlertDisableResult)
def disable_alert(
    alert_id: int,
    db: Session = Depends(get_db),
):
    try:
        return disable_price_alert(
            db=db,
            alert_id=alert_id,
        )
    except AlertNotFoundError as error:
        raise_api_error(
            status_code=404,
            code="alert_not_found",
            message=str(error),
        )


@router.delete("/{alert_id}", response_model=AlertDeleteResult)
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
):
    try:
        return remove_price_alert(
            db=db,
            alert_id=alert_id,
        )
    except AlertNotFoundError as error:
        raise_api_error(
            status_code=404,
            code="alert_not_found",
            message=str(error),
        )
