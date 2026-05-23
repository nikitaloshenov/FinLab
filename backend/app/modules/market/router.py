from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.market.moex_client import (
    MoexClientError,
    MoexTickerNotFoundError,
)
from app.modules.market.schemas import MoexTickerData, TickerListItem
from app.modules.market.service import get_ticker_from_moex, list_tickers


router = APIRouter(
    prefix="/market",
    tags=["Market"],
)


@router.get("/tickers", response_model=list[TickerListItem])
def get_market_tickers(db: Session = Depends(get_db)):
    return list_tickers(db)


@router.get("/tickers/{secid}/moex", response_model=MoexTickerData)
def get_market_ticker_from_moex(secid: str):
    try:
        return get_ticker_from_moex(secid)
    except MoexTickerNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except MoexClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error