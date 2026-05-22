from sqlalchemy.orm import Session

from app.modules.market.models import Ticker
from app.modules.market.repository import get_tickers


def list_tickers(db: Session) -> list[Ticker]:
    return get_tickers(db)