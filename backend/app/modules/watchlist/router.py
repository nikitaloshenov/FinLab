from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.market.moex_client import (
    MoexClientError,
    MoexTickerNotFoundError,
)
from app.modules.market.service import MarketPriceUnavailableError
from app.modules.watchlist.schemas import (
    WatchlistDeleteResult,
    WatchlistItemCreate,
    WatchlistItemRead,
    WatchlistRefreshResult,
)
from app.modules.watchlist.service import (
    WatchlistItemNotFoundError,
    WatchlistTickerCreateError,
    add_ticker_to_watchlist,
    list_watchlist_items,
    refresh_watchlist_prices,
    remove_ticker_from_watchlist,
)
from app.shared.errors import raise_api_error


router = APIRouter(
    prefix="/watchlist",
    tags=["Watchlist"],
)


@router.get("", response_model=list[WatchlistItemRead])
def get_watchlist(db: Session = Depends(get_db)):
    return list_watchlist_items(db)


@router.post("/items", response_model=WatchlistItemRead)
def add_watchlist_item(
    item_data: WatchlistItemCreate,
    db: Session = Depends(get_db),
):
    try:
        return add_ticker_to_watchlist(
            db=db,
            secid=item_data.secid,
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
    except WatchlistTickerCreateError as error:
        raise_api_error(
            status_code=500,
            code="watchlist_ticker_create_error",
            message=str(error),
        )


@router.post("/refresh-prices", response_model=WatchlistRefreshResult)
def refresh_watchlist_item_prices(db: Session = Depends(get_db)):
    return refresh_watchlist_prices(db)


@router.delete("/items/{secid}", response_model=WatchlistDeleteResult)
def delete_watchlist_item_by_secid(
    secid: str,
    db: Session = Depends(get_db),
):
    try:
        return remove_ticker_from_watchlist(
            db=db,
            secid=secid,
        )
    except WatchlistItemNotFoundError as error:
        raise_api_error(
            status_code=404,
            code="watchlist_item_not_found",
            message=str(error),
        )
