from typing import Any

from sqlalchemy.orm import Session

from app.modules.market.moex_client import MoexClient
from app.modules.market.repository import (
    create_price,
    create_ticker,
    get_latest_price_by_secid,
    get_ticker_by_secid,
    get_tickers,
    update_ticker_from_moex_data,
    upsert_latest_price,
)


class MarketPriceUnavailableError(Exception):
    pass


class MarketLatestPriceNotFoundError(Exception):
    pass


def list_tickers(db: Session) -> list[dict[str, Any]]:
    return get_tickers(db)


def get_ticker_from_moex(secid: str) -> dict[str, Any]:
    moex_client = MoexClient()
    return moex_client.fetch_ticker(secid)


def refresh_ticker_price(db: Session, secid: str) -> dict[str, Any]:
    moex_data = get_ticker_from_moex(secid)

    price = moex_data.get("price")

    if price is None:
        raise MarketPriceUnavailableError(
            f"MOEX did not return price for ticker {secid.upper()}"
        )

    ticker = get_ticker_by_secid(db, moex_data["secid"])

    if ticker is None:
        ticker = create_ticker(db, moex_data)
    else:
        ticker = update_ticker_from_moex_data(ticker, moex_data)

    create_price(
        db=db,
        ticker=ticker,
        price=price,
        source="moex",
    )

    latest_price = upsert_latest_price(
        db=db,
        ticker=ticker,
        price=price,
        source="moex",
    )

    db.commit()
    db.refresh(ticker)
    db.refresh(latest_price)

    return {
        "secid": ticker.secid,
        "short_name": ticker.short_name,
        "price": latest_price.price,
        "previous_price": latest_price.previous_price,
        "source": latest_price.source,
        "received_at": latest_price.received_at,
        "market_time": latest_price.market_time,
        "saved": True,
    }


def get_saved_ticker_price(db: Session, secid: str) -> dict[str, Any]:
    latest_price = get_latest_price_by_secid(db, secid)

    if latest_price is None:
        raise MarketLatestPriceNotFoundError(
            f"Saved price for ticker {secid.upper()} not found"
        )

    return latest_price