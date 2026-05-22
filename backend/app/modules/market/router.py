from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.market.schemas import TickerListItem
from app.modules.market.service import list_tickers


router = APIRouter(
    prefix="/market",
    tags=["Market"],
)


@router.get("/tickers", response_model=list[TickerListItem])
def get_market_tickers(db: Session = Depends(get_db)):
    return list_tickers(db)