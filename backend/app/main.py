from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.modules.alerts.router import router as alerts_router
from app.modules.market.router import router as market_router
from app.modules.watchlist.router import router as watchlist_router


app = FastAPI(
    title=settings.app_name,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

app.include_router(
    watchlist_router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    alerts_router,
    prefix=settings.api_v1_prefix,
)