from app.core.database import Base
from app.modules.reference.models import (
    Benchmark,
    DataSource,
    Instrument,
    Issuer,
    IssuerSectorHistory,
    Sector,
)


def test_reference_models_are_registered_in_metadata():
    expected_tables = {
        "issuers",
        "instruments",
        "sectors",
        "issuer_sector_history",
        "benchmarks",
        "data_sources",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_reference_model_table_names():
    assert Issuer.__tablename__ == "issuers"
    assert Instrument.__tablename__ == "instruments"
    assert Sector.__tablename__ == "sectors"
    assert IssuerSectorHistory.__tablename__ == "issuer_sector_history"
    assert Benchmark.__tablename__ == "benchmarks"
    assert DataSource.__tablename__ == "data_sources"


def test_reference_constraints_and_indexes_are_registered():
    instruments_table = Base.metadata.tables["instruments"]
    history_table = Base.metadata.tables["issuer_sector_history"]

    instrument_constraints = {constraint.name for constraint in instruments_table.constraints}
    history_constraints = {constraint.name for constraint in history_table.constraints}
    history_indexes = {index.name for index in history_table.indexes}

    assert "uq_instruments_engine_market_board_secid" in instrument_constraints
    assert "uq_issuer_sector_history_issuer_sector_valid_from" in history_constraints
    assert "ix_issuer_sector_history_issuer_valid_from" in history_indexes
