import logging
from typing import Any

from sqlalchemy.orm import Session

from app.modules.market.moex_client import MoexClientError, MoexTickerNotFoundError
from app.modules.market.repository import get_ticker_by_secid
from app.modules.market.service import MarketPriceUnavailableError, refresh_ticker_price
from app.modules.watchlist.repository import (
    create_watchlist_item,
    delete_watchlist_item,
    get_watchlist_item_by_secid,
    get_watchlist_item_by_ticker_id,
    get_watchlist_items,
    watchlist_item_to_dict,
)


logger = logging.getLogger(__name__)


class WatchlistItemNotFoundError(Exception):
    pass


class WatchlistTickerCreateError(Exception):
    pass


def list_watchlist_items(db: Session) -> list[dict[str, Any]]:
    return get_watchlist_items(db)


def add_ticker_to_watchlist(db: Session, secid: str) -> dict[str, Any]:
    normalized_secid = secid.upper().strip()

    ticker = get_ticker_by_secid(db, normalized_secid)

    if ticker is None:
        refresh_ticker_price(db, normalized_secid)
        ticker = get_ticker_by_secid(db, normalized_secid)

    if ticker is None:
        raise WatchlistTickerCreateError(
            f"Ticker {normalized_secid} was not created"
        )

    existing_item = get_watchlist_item_by_ticker_id(
        db=db,
        ticker_id=ticker.id,
    )

    if existing_item is not None:
        return watchlist_item_to_dict(existing_item)

    create_watchlist_item(
        db=db,
        ticker=ticker,
    )

    db.commit()

    created_item = get_watchlist_item_by_secid(
        db=db,
        secid=normalized_secid,
    )

    if created_item is None:
        raise WatchlistTickerCreateError(
            f"Watchlist item for {normalized_secid} was not created"
        )

    return watchlist_item_to_dict(created_item)


def remove_ticker_from_watchlist(db: Session, secid: str) -> dict[str, Any]:
    normalized_secid = secid.upper().strip()

    item = get_watchlist_item_by_secid(
        db=db,
        secid=normalized_secid,
    )

    if item is None:
        raise WatchlistItemNotFoundError(
            f"Ticker {normalized_secid} not found in watchlist"
        )

    delete_watchlist_item(
        db=db,
        item=item,
    )

    db.commit()

    return {
        "secid": normalized_secid,
        "deleted": True,
    }


def refresh_watchlist_prices(db: Session) -> dict[str, Any]:
    watchlist_items = get_watchlist_items(db)

    logger.info("Refreshing watchlist prices: total=%s", len(watchlist_items))

    results = []
    updated_count = 0
    failed_count = 0

    for item in watchlist_items:
        secid = item["secid"]

        try:
            refresh_result = refresh_ticker_price(
                db=db,
                secid=secid,
            )

            updated_count += 1

            logger.info(
                "Watchlist ticker refreshed: secid=%s price=%s",
                secid,
                refresh_result["price"],
            )

            results.append(
                {
                    "secid": secid,
                    "success": True,
                    "price": refresh_result["price"],
                    "error": None,
                }
            )

        except (
            MoexTickerNotFoundError,
            MarketPriceUnavailableError,
            MoexClientError,
        ) as error:
            db.rollback()
            failed_count += 1

            logger.warning(
                "Watchlist ticker refresh failed: secid=%s error=%s",
                secid,
                error,
            )

            results.append(
                {
                    "secid": secid,
                    "success": False,
                    "price": None,
                    "error": str(error),
                }
            )

        except Exception as error:
            db.rollback()
            failed_count += 1

            logger.warning(
                "Watchlist ticker refresh failed: secid=%s error=%s",
                secid,
                error,
            )

            results.append(
                {
                    "secid": secid,
                    "success": False,
                    "price": None,
                    "error": f"Unexpected error: {error}",
                }
            )

    logger.info(
        "Watchlist refresh completed: total=%s updated=%s failed=%s",
        len(watchlist_items),
        updated_count,
        failed_count,
    )

    return {
        "total": len(watchlist_items),
        "updated": updated_count,
        "failed": failed_count,
        "items": results,
    }
