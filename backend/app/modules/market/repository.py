from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.modules.market.models import Price, Ticker, TickerLatestPrice


def get_tickers(db: Session) -> list[dict[str, Any]]:
    tickers = (
        db.query(Ticker)
        .options(joinedload(Ticker.latest_price))
        .order_by(Ticker.secid)
        .all()
    )

    return [
        {
            "id": ticker.id,
            "secid": ticker.secid,
            "short_name": ticker.short_name,
            "latest_price": (
                ticker.latest_price.price
                if ticker.latest_price is not None
                else None
            ),
        }
        for ticker in tickers
    ]


def get_ticker_by_secid(db: Session, secid: str) -> Ticker | None:
    normalized_secid = secid.upper().strip()

    return (
        db.query(Ticker)
        .filter(Ticker.secid == normalized_secid)
        .first()
    )


def create_ticker(db: Session, ticker_data: dict[str, Any]) -> Ticker:
    ticker = Ticker(
        secid=ticker_data["secid"],
        short_name=ticker_data.get("short_name"),
        name=ticker_data.get("name"),
        board=ticker_data.get("board", "TQBR"),
        market=ticker_data.get("market", "shares"),
        engine=ticker_data.get("engine", "stock"),
        currency=ticker_data.get("currency"),
    )

    db.add(ticker)
    db.flush()

    return ticker


def update_ticker_from_moex_data(
    ticker: Ticker,
    ticker_data: dict[str, Any],
) -> Ticker:
    ticker.short_name = ticker_data.get("short_name")
    ticker.name = ticker_data.get("name")
    ticker.board = ticker_data.get("board", ticker.board)
    ticker.market = ticker_data.get("market", ticker.market)
    ticker.engine = ticker_data.get("engine", ticker.engine)
    ticker.currency = ticker_data.get("currency")

    return ticker


def create_price(
    db: Session,
    ticker: Ticker,
    price: Decimal,
    source: str = "moex",
) -> Price:
    price_row = Price(
        ticker_id=ticker.id,
        price=price,
        source=source,
    )

    db.add(price_row)
    db.flush()

    return price_row


def upsert_latest_price(
    db: Session,
    ticker: Ticker,
    price: Decimal,
    source: str = "moex",
) -> TickerLatestPrice:
    latest_price = (
        db.query(TickerLatestPrice)
        .filter(TickerLatestPrice.ticker_id == ticker.id)
        .first()
    )

    now = datetime.now(UTC)

    if latest_price is None:
        latest_price = TickerLatestPrice(
            ticker_id=ticker.id,
            price=price,
            previous_price=None,
            source=source,
            received_at=now,
        )

        db.add(latest_price)
        db.flush()

        return latest_price

    latest_price.previous_price = latest_price.price
    latest_price.price = price
    latest_price.source = source
    latest_price.received_at = now

    db.flush()

    return latest_price


def get_latest_price_by_secid(
    db: Session,
    secid: str,
) -> dict[str, Any] | None:
    ticker = get_ticker_by_secid(db, secid)

    if ticker is None:
        return None

    latest_price = (
        db.query(TickerLatestPrice)
        .filter(TickerLatestPrice.ticker_id == ticker.id)
        .first()
    )

    if latest_price is None:
        return None

    return {
        "secid": ticker.secid,
        "short_name": ticker.short_name,
        "price": latest_price.price,
        "previous_price": latest_price.previous_price,
        "source": latest_price.source,
        "received_at": latest_price.received_at,
        "market_time": latest_price.market_time,
    }