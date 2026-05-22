from sqlalchemy.orm import Session

from app.modules.market.models import Ticker


def get_tickers(db: Session) -> list[Ticker]:
    return db.query(Ticker).order_by(Ticker.secid).all()