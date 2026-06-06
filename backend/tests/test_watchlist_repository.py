import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.modules.market.models import Ticker
from app.modules.watchlist.repository import (
    create_watchlist_item,
    get_watchlist_item_by_secid,
    get_watchlist_items,
)


SESSION_A = "11111111-1111-4111-8111-111111111111"
SESSION_B = "22222222-2222-4222-8222-222222222222"


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_watchlist_items_are_session_scoped(db_session):
    ticker = Ticker(
        secid="SBER",
        short_name="Sber",
        board="TQBR",
        market="shares",
        engine="stock",
    )
    db_session.add(ticker)
    db_session.flush()

    create_watchlist_item(db_session, ticker=ticker, session_id=SESSION_A)
    create_watchlist_item(db_session, ticker=ticker, session_id=SESSION_B)
    db_session.commit()

    session_a_items = get_watchlist_items(db_session, session_id=SESSION_A)
    session_b_items = get_watchlist_items(db_session, session_id=SESSION_B)

    assert [item["secid"] for item in session_a_items] == ["SBER"]
    assert [item["secid"] for item in session_b_items] == ["SBER"]
    assert session_a_items[0]["id"] != session_b_items[0]["id"]


def test_get_watchlist_item_by_secid_does_not_cross_sessions(db_session):
    ticker = Ticker(
        secid="SBER",
        short_name="Sber",
        board="TQBR",
        market="shares",
        engine="stock",
    )
    db_session.add(ticker)
    db_session.flush()

    create_watchlist_item(db_session, ticker=ticker, session_id=SESSION_A)
    db_session.commit()

    assert get_watchlist_item_by_secid(
        db_session,
        secid="SBER",
        session_id=SESSION_A,
    )
    assert get_watchlist_item_by_secid(
        db_session,
        secid="SBER",
        session_id=SESSION_B,
    ) is None
