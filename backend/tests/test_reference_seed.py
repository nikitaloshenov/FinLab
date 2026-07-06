from datetime import date

from sqlalchemy import create_engine, func, select
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
        curated_secids = _curated_secids()

        assert first_summary.data_sources.created == 3
        assert first_summary.sectors.created == len(SECTOR_SEEDS)
        assert first_summary.instruments.created == len(curated_secids) + 1
        assert first_summary.issuers.created == len(CURATED_ISSUER_MAPPINGS)
        assert first_summary.issuer_sector_history.created == len(CURATED_ISSUER_MAPPINGS)
        assert first_summary.benchmarks.created == len(BENCHMARK_SEEDS)

        assert second_summary.data_sources.skipped == 3
        assert second_summary.sectors.skipped == len(SECTOR_SEEDS)
        assert second_summary.instruments.skipped == len(curated_secids) + 3
        assert second_summary.issuers.skipped == len(CURATED_ISSUER_MAPPINGS)
        assert second_summary.issuer_sector_history.skipped == len(CURATED_ISSUER_MAPPINGS)
        assert second_summary.benchmarks.skipped == len(BENCHMARK_SEEDS)

        assert session.scalar(select(DataSource).where(DataSource.code == "manual_seed")) is not None
        assert session.scalar(select(Sector).where(Sector.code == "finance")) is not None
        assert session.scalar(select(Instrument).where(Instrument.secid == "SBER")) is not None
        assert session.scalar(select(Issuer).where(Issuer.name == "Sberbank")) is not None
        assert session.scalar(select(IssuerSectorHistory)) is not None
        assert session.scalar(select(Benchmark).where(Benchmark.code == "russian_market")) is not None
    finally:
        session.close()


def test_reference_seed_on_empty_db_creates_curated_instruments_and_shared_history_once():
    session = _build_session()
    try:
        first_summary = seed_reference_layer(session)
        second_summary = seed_reference_layer(session)

        sber = session.scalar(select(Instrument).where(Instrument.secid == "SBER"))
        sberp = session.scalar(select(Instrument).where(Instrument.secid == "SBERP"))
        flot = session.scalar(select(Instrument).where(Instrument.secid == "FLOT"))

        assert sber is not None
        assert sberp is not None
        assert flot is not None
        assert sber.issuer_id == sberp.issuer_id
        assert _sector_code_for_secid(session, "SBER") == "finance"
        assert _sector_code_for_secid(session, "SBERP") == "finance"
        assert _sector_code_for_secid(session, "FLOT") == "transport"

        assert _current_history_count_for_issuer(session, sber.issuer_id) == 1
        assert first_summary.issuer_sector_history.created == len(CURATED_ISSUER_MAPPINGS)
        assert second_summary.issuer_sector_history.created == 0
        assert second_summary.issuer_sector_history.conflicts == 0
        assert (
            session.scalar(select(func.count()).select_from(Instrument))
            == len(_curated_secids())
        )
        assert (
            session.scalar(select(func.count()).select_from(IssuerSectorHistory))
            == len(CURATED_ISSUER_MAPPINGS)
        )
    finally:
        session.close()


def test_reference_seed_assigns_curated_sectors_and_is_idempotent():
    session = _build_session()
    try:
        _add_tickers(
            session,
            "SBER",
            "SBERP",
            "CBOM",
            "MOEX",
            "GAZP",
            "LKOH",
            "ROSN",
            "NVTK",
            "FLOT",
            "YDEX",
            "IRAO",
        )
        session.commit()

        first_summary = seed_reference_layer(session)
        second_summary = seed_reference_layer(session)

        assert first_summary.issuer_sector_history.created == len(CURATED_ISSUER_MAPPINGS)
        assert second_summary.issuer_sector_history.created == 0
        assert second_summary.issuer_sector_history.conflicts == 0
        assert (
            session.scalar(select(func.count()).select_from(IssuerSectorHistory))
            == len(CURATED_ISSUER_MAPPINGS)
        )

        assert _sector_code_for_secid(session, "SBER") == "finance"
        assert _sector_code_for_secid(session, "SBERP") == "finance"
        assert _sector_code_for_secid(session, "CBOM") == "finance"
        assert _sector_code_for_secid(session, "MOEX") == "financial_infrastructure"
        assert _sector_code_for_secid(session, "GAZP") == "oil_gas"
        assert _sector_code_for_secid(session, "LKOH") == "oil_gas"
        assert _sector_code_for_secid(session, "ROSN") == "oil_gas"
        assert _sector_code_for_secid(session, "NVTK") == "oil_gas"
        assert _sector_code_for_secid(session, "FLOT") == "transport"
        assert _sector_code_for_secid(session, "YDEX") == "it"
        assert _sector_code_for_secid(session, "IRAO") == "utilities"
    finally:
        session.close()


def test_reference_seed_reuses_existing_matching_history():
    session = _build_session()
    try:
        sector = Sector(code="finance", name="Finance")
        issuer = Issuer(name="Sberbank", short_name="Sberbank", country="RU")
        sber = Instrument(
            issuer=issuer,
            secid="SBER",
            name="Sberbank",
            short_name="SBER",
            asset_type="share",
            board="TQBR",
            market="shares",
            engine="stock",
            currency="RUB",
        )
        history = IssuerSectorHistory(
            issuer=issuer,
            sector=sector,
            valid_from=date(1900, 1, 1),
        )
        session.add_all([sector, issuer, sber, history])
        session.commit()

        seed_reference_layer(session)

        sberp = session.scalar(select(Instrument).where(Instrument.secid == "SBERP"))

        assert sberp is not None
        assert sberp.issuer_id == sber.issuer_id
        assert _current_history_count_for_issuer(session, sber.issuer_id) == 1
        assert _sector_code_for_secid(session, "SBERP") == "finance"
    finally:
        session.close()


def test_reference_seed_does_not_overwrite_conflicting_sector_history():
    session = _build_session()
    try:
        _add_tickers(session, "FLOT")
        seed_reference_layer(session)

        instrument = session.scalar(select(Instrument).where(Instrument.secid == "FLOT"))
        transport_history = session.scalar(
            select(IssuerSectorHistory).where(IssuerSectorHistory.issuer_id == instrument.issuer_id),
        )
        other_sector = session.scalar(select(Sector).where(Sector.code == "finance"))
        transport_history.sector = other_sector
        session.commit()

        summary = seed_reference_layer(session)

        assert summary.issuer_sector_history.conflicts == 1
        assert _sector_code_for_secid(session, "FLOT") == "finance"
        assert (
            session.scalar(
                select(func.count())
                .select_from(IssuerSectorHistory)
                .where(IssuerSectorHistory.issuer_id == instrument.issuer_id),
            )
            == 1
        )
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


def _add_tickers(session, *secids: str) -> None:
    for secid in secids:
        session.add(
            Ticker(
                secid=secid,
                short_name=secid,
                name=f"{secid} issuer",
                board="TQBR",
                market="shares",
                engine="stock",
                currency="RUB",
            ),
        )


def _sector_code_for_secid(session, secid: str) -> str | None:
    return session.scalar(
        select(Sector.code)
        .join(IssuerSectorHistory, IssuerSectorHistory.sector_id == Sector.id)
        .join(Issuer, Issuer.id == IssuerSectorHistory.issuer_id)
        .join(Instrument, Instrument.issuer_id == Issuer.id)
        .where(Instrument.secid == secid),
    )


def _current_history_count_for_issuer(session, issuer_id: int) -> int:
    return session.scalar(
        select(func.count())
        .select_from(IssuerSectorHistory)
        .where(IssuerSectorHistory.issuer_id == issuer_id)
        .where(IssuerSectorHistory.valid_to.is_(None)),
    )


def _curated_secids() -> set[str]:
    return {
        secid
        for mapping in CURATED_ISSUER_MAPPINGS
        for secid in mapping["secids"]
    }


def _assert_unique(values):
    assert len(values) == len(set(values))
