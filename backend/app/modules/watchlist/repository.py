from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.modules.market.models import Ticker
from app.modules.watchlist.models import WatchlistItem


def watchlist_item_to_dict(item: WatchlistItem) -> dict[str, Any]:
    ticker = item.ticker

    latest_price = None

    if ticker.latest_price is not None:
        latest_price = ticker.latest_price.price

    return {
        "id": item.id,
        "secid": ticker.secid,
        "short_name": ticker.short_name,
        "latest_price": latest_price,
        "created_at": item.created_at,
    }


def get_watchlist_items(
    db: Session,
    session_id: str,
) -> list[dict[str, Any]]:
    items = (
        db.query(WatchlistItem)
        .options(
            joinedload(WatchlistItem.ticker).joinedload(Ticker.latest_price)
        )
        .filter(WatchlistItem.session_id == session_id)
        .order_by(WatchlistItem.created_at.desc())
        .all()
    )

    return [watchlist_item_to_dict(item) for item in items]


def get_watchlist_item_by_ticker_id(
    db: Session,
    ticker_id: int,
    session_id: str,
) -> WatchlistItem | None:
    return (
        db.query(WatchlistItem)
        .options(
            joinedload(WatchlistItem.ticker).joinedload(Ticker.latest_price)
        )
        .filter(
            WatchlistItem.session_id == session_id,
            WatchlistItem.ticker_id == ticker_id,
        )
        .first()
    )


def get_watchlist_item_by_secid(
    db: Session,
    secid: str,
    session_id: str,
) -> WatchlistItem | None:
    normalized_secid = secid.upper().strip()

    return (
        db.query(WatchlistItem)
        .join(Ticker, WatchlistItem.ticker_id == Ticker.id)
        .options(
            joinedload(WatchlistItem.ticker).joinedload(Ticker.latest_price)
        )
        .filter(
            WatchlistItem.session_id == session_id,
            Ticker.secid == normalized_secid,
        )
        .first()
    )


def create_watchlist_item(
    db: Session,
    ticker: Ticker,
    session_id: str,
) -> WatchlistItem:
    item = WatchlistItem(
        user_key=session_id,
        session_id=session_id,
        ticker_id=ticker.id,
    )

    db.add(item)
    db.flush()

    return item


def delete_watchlist_item(
    db: Session,
    item: WatchlistItem,
) -> None:
    db.delete(item)
    db.flush()
