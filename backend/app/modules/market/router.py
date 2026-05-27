from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.market.moex_client import (
    MoexClientError,
    MoexTickerNotFoundError,
)
from app.modules.market.schemas import (
    MoexTickerData,
    TickerCandleResponse,
    TickerListItem,
    TickerPriceHistoryItem,
    TickerPriceRead,
    TickerRefreshResult,
)
from app.modules.market.service import (
    MarketLatestPriceNotFoundError,
    MarketPriceUnavailableError,
    MarketTickerNotFoundError,
    get_saved_ticker_price,
    get_ticker_candles,
    get_ticker_from_moex,
    get_ticker_price_history,
    list_tickers,
    refresh_ticker_price,
)
from app.shared.errors import raise_api_error


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
        raise_api_error(
            status_code=404,
            code="ticker_not_found",
            message=str(error),
        )
    except MoexClientError as error:
        raise_api_error(
            status_code=502,
            code="moex_client_error",
            message=str(error),
        )


@router.post("/tickers/{secid}/refresh", response_model=TickerRefreshResult)
def refresh_market_ticker_price(
    secid: str,
    db: Session = Depends(get_db),
):
    try:
        return refresh_ticker_price(db, secid)
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


@router.get("/tickers/{secid}/price", response_model=TickerPriceRead)
def get_market_ticker_price(
    secid: str,
    db: Session = Depends(get_db),
):
    try:
        return get_saved_ticker_price(db, secid)
    except MarketLatestPriceNotFoundError as error:
        raise_api_error(
            status_code=404,
            code="market_latest_price_not_found",
            message=str(error),
        )


@router.get("/tickers/{secid}/prices", response_model=list[TickerPriceHistoryItem])
def get_market_ticker_price_history(
    secid: str,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    try:
        return get_ticker_price_history(
            db=db,
            secid=secid,
            limit=limit,
        )
    except MarketTickerNotFoundError as error:
        raise_api_error(
            status_code=404,
            code="ticker_not_found",
            message=str(error),
        )


@router.get("/tickers/{secid}/candles", response_model=list[TickerCandleResponse])
def get_market_ticker_candles(
    secid: str,
    interval: Literal["10m", "1h", "1d"] = "1d",
    limit: int = Query(default=100, ge=1, le=500),
):
    try:
        return get_ticker_candles(
            secid=secid,
            interval=interval,
            limit=limit,
        )
    except MoexTickerNotFoundError as error:
        raise_api_error(
            status_code=404,
            code="ticker_not_found",
            message=str(error),
        )
    except MoexClientError as error:
        raise_api_error(
            status_code=502,
            code="moex_client_error",
            message=str(error),
        )
