from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.modules.market.router import router as market_router


app = FastAPI(
    title=settings.app_name,
)


@app.get(f"{settings.api_v1_prefix}/health")
def health_check():
    return {"status": "ok"}


@app.get(f"{settings.api_v1_prefix}/health/db")
def database_health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


app.include_router(
    market_router,
    prefix=settings.api_v1_prefix,
)