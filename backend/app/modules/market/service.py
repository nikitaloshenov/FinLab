import logging
from typing import Any

from sqlalchemy.orm import Session

from app.modules.market.moex_client import (
    MoexClient,
    MoexClientError,
    MoexTickerNotFoundError,
)
from app.modules.market.repository import (
    create_price,
    create_ticker,
    get_latest_price_by_secid,
    get_price_history_by_secid,
    get_ticker_by_secid,
    get_tickers,
    update_ticker_from_moex_data,
    upsert_latest_price,
)


logger = logging.getLogger(__name__)


class MarketPriceUnavailableError(Exception):
    pass


class MarketLatestPriceNotFoundError(Exception):
    pass


class MarketTickerNotFoundError(Exception):
    pass


def list_tickers(db: Session) -> list[dict[str, Any]]:
    return get_tickers(db)


def get_ticker_from_moex(secid: str) -> dict[str, Any]:
    moex_client = MoexClient()
    return moex_client.fetch_ticker(secid)


def refresh_ticker_price(db: Session, secid: str) -> dict[str, Any]:
    normalized_secid = secid.upper().strip()

    logger.info("Refreshing ticker price: secid=%s", normalized_secid)

    try:
        moex_data = get_ticker_from_moex(secid)
    except MoexTickerNotFoundError:
        logger.warning(
            "Ticker refresh failed, ticker not found: secid=%s",
            normalized_secid,
        )
        raise
    except MoexClientError as error:
        logger.error(
            "Ticker refresh failed, MOEX client error: secid=%s error=%s",
            normalized_secid,
            error,
        )
        raise

    price = moex_data.get("price")

    if price is None:
        logger.warning(
            "Ticker refresh failed, price unavailable: secid=%s",
            normalized_secid,
        )
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

    logger.info(
        "Ticker price refreshed: secid=%s price=%s saved=%s",
        ticker.secid,
        latest_price.price,
        True,
    )

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


def get_ticker_price_history(
    db: Session,
    secid: str,
    limit: int,
) -> list[dict[str, Any]]:
    history = get_price_history_by_secid(
        db=db,
        secid=secid,
        limit=limit,
    )

    if history is None:
        raise MarketTickerNotFoundError(
            f"Ticker {secid.upper()} not found"
        )

    return history
