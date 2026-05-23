from typing import Any

from sqlalchemy.orm import Session

from app.modules.market.models import Ticker
from app.modules.market.moex_client import MoexClient
from app.modules.market.repository import get_tickers


def list_tickers(db: Session) -> list[Ticker]:
    return get_tickers(db)


def get_ticker_from_moex(secid: str) -> dict[str, Any]:
    moex_client = MoexClient()
    return moex_client.fetch_ticker(secid)