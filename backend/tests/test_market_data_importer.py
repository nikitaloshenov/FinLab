from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.modules.market_data.models import IngestionRun, PriceCandle
from app.modules.market_data.repository import create_ingestion_run, upsert_price_candles
from app.modules.market_data.service import (
    MarketDataInstrumentNotFoundError,
    MarketDataUnsupportedIntervalError,
    import_daily_candles,
)
from app.modules.reference.models import DataSource, Instrument


class FakeMoexClient:
    def __init__(self, candles=None, error=None):
        self.candles = candles or []
        self.error = error

    def fetch_candles(self, secid, interval, from_date, till_date):
        if self.error is not None:
            raise self.error

        return self.candles


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


def test_upsert_price_candles_does_not_create_duplicates(db_session):
    instrument = _seed_instrument(db_session)
    source = _seed_moex_source(db_session)
    ingestion_run = create_ingestion_run(
        db_session,
        source_id=source.id,
        ingestion_type="moex_daily_candles",
        params_json={},
    )
    candle = {
        "interval": "1d",
        "begin_at": datetime(2024, 1, 3, tzinfo=UTC),
        "trading_date": date(2024, 1, 3),
        "open": Decimal("100"),
        "high": Decimal("110"),
        "low": Decimal("95"),
        "close": Decimal("105"),
        "volume": Decimal("1000"),
        "value": Decimal("105000"),
    }

    first_count = upsert_price_candles(
        db_session,
        instrument_id=instrument.id,
        source_id=source.id,
        ingestion_run_id=ingestion_run.id,
        candles=[candle],
    )
    candle["close"] = Decimal("106")
    second_count = upsert_price_candles(
        db_session,
        instrument_id=instrument.id,
        source_id=source.id,
        ingestion_run_id=ingestion_run.id,
        candles=[candle],
    )

    saved_candles = db_session.scalars(select(PriceCandle)).all()

    assert first_count == 1
    assert second_count == 1
    assert len(saved_candles) == 1
    assert saved_candles[0].close == Decimal("106.000000")


def test_import_daily_candles_with_fake_moex_client_succeeds(db_session):
    _seed_moex_source(db_session)
    _seed_instrument(db_session)
    fake_client = FakeMoexClient(
        candles=[
            {
                "begin": "2024-01-03T00:00:00",
                "open": Decimal("100"),
                "high": Decimal("110"),
                "low": Decimal("95"),
                "close": Decimal("105"),
                "volume": Decimal("1000"),
                "value": Decimal("105000"),
            },
        ],
    )

    result = import_daily_candles(
        db_session,
        secid="sber",
        date_from=date(2024, 1, 1),
        date_to=date(2024, 1, 10),
        moex_client=fake_client,
    )

    ingestion_run = db_session.get(IngestionRun, result.ingestion_run_id)
    saved_candle = db_session.scalar(select(PriceCandle).where(PriceCandle.interval == "1d"))

    assert result.rows_loaded == 1
    assert result.status == "success"
    assert ingestion_run.status == "success"
    assert ingestion_run.rows_loaded == 1
    assert saved_candle.trading_date == date(2024, 1, 3)
    assert saved_candle.close == Decimal("105.000000")


def test_import_daily_candles_unknown_secid_fails(db_session):
    with pytest.raises(MarketDataInstrumentNotFoundError):
        import_daily_candles(
            db_session,
            secid="UNKNOWN",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 10),
            moex_client=FakeMoexClient(),
        )


def test_import_daily_candles_unsupported_interval_fails(db_session):
    _seed_instrument(db_session)

    with pytest.raises(MarketDataUnsupportedIntervalError):
        import_daily_candles(
            db_session,
            secid="SBER",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 10),
            interval="1h",
            moex_client=FakeMoexClient(),
        )


def test_import_daily_candles_marks_ingestion_run_failed_on_client_error(db_session):
    _seed_moex_source(db_session)
    _seed_instrument(db_session)

    with pytest.raises(RuntimeError):
        import_daily_candles(
            db_session,
            secid="SBER",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 10),
            moex_client=FakeMoexClient(error=RuntimeError("MOEX unavailable")),
        )

    ingestion_run = db_session.scalar(select(IngestionRun))

    assert ingestion_run.status == "failed"
    assert ingestion_run.rows_failed == 1
    assert "MOEX unavailable" in ingestion_run.error_message


def _seed_moex_source(db_session):
    source = DataSource(
        code="moex",
        name="Moscow Exchange",
        source_type="moex",
        url="https://iss.moex.com/iss",
    )
    db_session.add(source)
    db_session.commit()
    return source


def _seed_instrument(db_session):
    instrument = Instrument(
        secid="SBER",
        name="Sberbank",
        short_name="Sberbank",
        asset_type="share",
        board="TQBR",
        market="shares",
        engine="stock",
        currency="RUB",
    )
    db_session.add(instrument)
    db_session.commit()
    return instrument
