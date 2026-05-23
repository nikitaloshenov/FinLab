from typing import Any

from sqlalchemy.orm import Session

from app.modules.market.repository import get_ticker_by_secid
from app.modules.market.service import refresh_ticker_price
from app.modules.watchlist.repository import (
    create_watchlist_item,
    delete_watchlist_item,
    get_watchlist_item_by_secid,
    get_watchlist_item_by_ticker_id,
    get_watchlist_items,
    watchlist_item_to_dict,
)


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