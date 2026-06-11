from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.modules.market.models import Ticker
from app.modules.reference.constants import (
    BENCHMARK_SEEDS,
    CURATED_ISSUER_MAPPINGS,
    DATA_SOURCE_SEEDS,
    SECTOR_SEEDS,
)
from app.modules.reference.models import Benchmark, DataSource, Instrument, Issuer, IssuerSectorHistory, Sector
from app.modules.reference.seed import seed_reference_layer


def test_reference_seed_constants_are_unique():
    _assert_unique([source["code"] for source in DATA_SOURCE_SEEDS])
    _assert_unique([sector["code"] for sector in SECTOR_SEEDS])
    _assert_unique([benchmark["code"] for benchmark in BENCHMARK_SEEDS])


def test_curated_mapping_uses_known_sector_codes():
    sector_codes = {sector["code"] for sector in SECTOR_SEEDS}

    assert {
        mapping["sector_code"] for mapping in CURATED_ISSUER_MAPPINGS
    }.issubset(sector_codes)


def test_reference_seed_is_idempotent_on_small_db():
    session = _build_session()
    try:
        session.add_all(
            [
                Ticker(
                    secid="SBER",
                    short_name="Sber",
                    name="Sberbank",
                    board="TQBR",
                    market="shares",
                    engine="stock",
                    currency="RUB",
                ),
                Ticker(
                    secid="GAZP",
                    short_name="Gazprom",
                    name="Gazprom",
                    board="TQBR",
                    market="shares",
                    engine="stock",
                    currency="RUB",
                ),
                Ticker(
                    secid="UNKN",
                    short_name="Unknown",
                    name="Unknown issuer",
                    board="TQBR",
                    market="shares",
                    engine="stock",
                    currency="RUB",
                ),
            ],
        )
        session.commit()

        first_summary = seed_reference_layer(session)
        second_summary = seed_reference_layer(session)

        assert first_summary.data_sources.created == 3
        assert first_summary.sectors.created == len(SECTOR_SEEDS)
        assert first_summary.instruments.created == 3
        assert first_summary.issuers.created == 2
        assert first_summary.issuer_sector_history.created == 2
        assert first_summary.benchmarks.created == len(BENCHMARK_SEEDS)

        assert second_summary.data_sources.skipped == 3
        assert second_summary.sectors.skipped == len(SECTOR_SEEDS)
        assert second_summary.instruments.skipped == 3
        assert second_summary.issuers.skipped == 2
        assert second_summary.issuer_sector_history.skipped == 2
        assert second_summary.benchmarks.skipped == len(BENCHMARK_SEEDS)

        assert session.scalar(select(DataSource).where(DataSource.code == "manual_seed")) is not None
        assert session.scalar(select(Sector).where(Sector.code == "finance")) is not None
        assert session.scalar(select(Instrument).where(Instrument.secid == "SBER")) is not None
        assert session.scalar(select(Issuer).where(Issuer.name == "Sberbank")) is not None
        assert session.scalar(select(IssuerSectorHistory)) is not None
        assert session.scalar(select(Benchmark).where(Benchmark.code == "russian_market")) is not None
    finally:
        session.close()


def _build_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine)
    return session_local()


def _assert_unique(values):
    assert len(values) == len(set(values))
