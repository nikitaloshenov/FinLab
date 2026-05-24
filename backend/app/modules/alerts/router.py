from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.alerts.schemas import (
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
        raise HTTPException(status_code=404, detail=str(error)) from error
    except MarketPriceUnavailableError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except MoexClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except AlertTickerCreateError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get("/events", response_model=list[AlertEventRead])
def get_alert_events_list(db: Session = Depends(get_db)):
    return list_alert_events(db)


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
        raise HTTPException(status_code=404, detail=str(error)) from error
    except AlertLatestPriceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


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
        raise HTTPException(status_code=404, detail=str(error)) from error


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
        raise HTTPException(status_code=404, detail=str(error)) from error