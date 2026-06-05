from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.modules.hypotheses.key_rate_decisions_import_service import (
    import_key_rate_decisions_from_csv,
)
from app.modules.hypotheses.key_rate_decisions_importer import (
    KeyRateDecisionImportError,
)
from app.modules.hypotheses.key_rate_decisions_repository import (
    get_key_rate_decision_by_date,
    list_key_rate_decisions,
)


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


def test_import_key_rate_decisions_dry_run_does_not_write(db_session, tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            _csv_row(decision_date="2026-05-15"),
        ],
    )

    summary = import_key_rate_decisions_from_csv(
        db_session,
        csv_path,
        dry_run=True,
    )

    assert summary == {
        "processed": 1,
        "created": 1,
        "updated": 0,
        "skipped": 0,
        "errors": [],
        "dry_run": True,
    }
    assert list_key_rate_decisions(db_session) == []


def test_import_key_rate_decisions_creates_rows(db_session, tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            _csv_row(decision_date="2026-05-15"),
        ],
    )

    summary = import_key_rate_decisions_from_csv(db_session, csv_path)
    decisions = list_key_rate_decisions(db_session)

    assert summary["processed"] == 1
    assert summary["created"] == 1
    assert summary["updated"] == 0
    assert len(decisions) == 1
    assert decisions[0].decision_date == date(2026, 5, 15)


def test_import_key_rate_decisions_updates_existing_row(db_session, tmp_path):
    first_csv_path = _write_csv(
        tmp_path,
        [
            _csv_row(
                decision_date="2026-05-15",
                title="Initial title",
                notes="Initial notes",
            ),
        ],
        name="first.csv",
    )
    second_csv_path = _write_csv(
        tmp_path,
        [
            _csv_row(
                decision_date="2026-05-15",
                title="Updated title",
                notes="Updated notes",
            ),
        ],
        name="second.csv",
    )

    import_key_rate_decisions_from_csv(db_session, first_csv_path)
    summary = import_key_rate_decisions_from_csv(db_session, second_csv_path)

    decisions = list_key_rate_decisions(db_session)

    assert summary["created"] == 0
    assert summary["updated"] == 1
    assert len(decisions) == 1
    assert decisions[0].title == "Updated title"
    assert decisions[0].notes == "Updated notes"


def test_import_key_rate_decisions_supports_nullable_dataset_fields(
    db_session,
    tmp_path,
):
    csv_path = _write_csv(
        tmp_path,
        [
            _csv_row(
                decision_date="2026-05-15",
                meeting_date="2026-05-15",
                effective_date="2026-05-19",
                publication_datetime_msk="2026-05-15T13:30:00",
                source_title="Bank of Russia decision",
                notes="Curated official row.",
            ),
        ],
    )

    import_key_rate_decisions_from_csv(db_session, csv_path)

    decision = get_key_rate_decision_by_date(db_session, date(2026, 5, 15))

    assert decision is not None
    assert decision.meeting_date == date(2026, 5, 15)
    assert decision.effective_date == date(2026, 5, 19)
    assert decision.publication_datetime_msk is not None
    assert decision.source_title == "Bank of Russia decision"
    assert decision.notes == "Curated official row."


def test_import_key_rate_decisions_invalid_csv_fails_before_writing(
    db_session,
    tmp_path,
):
    csv_path = _write_csv(
        tmp_path,
        [
            _csv_row(decision_date="2026-05-15"),
            _csv_row(decision_date="2026-02-14", source_url=""),
        ],
    )

    with pytest.raises(KeyRateDecisionImportError):
        import_key_rate_decisions_from_csv(db_session, csv_path)

    assert list_key_rate_decisions(db_session) == []


def test_import_key_rate_decisions_rejects_duplicate_decision_date(
    db_session,
    tmp_path,
):
    csv_path = _write_csv(
        tmp_path,
        [
            _csv_row(decision_date="2026-05-15"),
            _csv_row(decision_date="2026-05-15", title="Duplicate"),
        ],
    )

    with pytest.raises(KeyRateDecisionImportError, match="Duplicate decision_date"):
        import_key_rate_decisions_from_csv(db_session, csv_path)

    assert list_key_rate_decisions(db_session) == []


def _write_csv(tmp_path, rows, name="decisions.csv"):
    csv_path = tmp_path / name
    csv_path.write_text(
        "\n".join([_csv_header(), *rows]),
        encoding="utf-8",
    )

    return csv_path


def _csv_header():
    return (
        "decision_date,meeting_date,effective_date,publication_datetime_msk,"
        "rate_before,rate_after,change_bps,direction,title,description,"
        "is_scheduled,is_official,source_url,source_type,source_title,"
        "source_note,notes"
    )


def _csv_row(
    decision_date,
    meeting_date="",
    effective_date="",
    publication_datetime_msk="",
    rate_before="16.00",
    rate_after="15.50",
    change_bps="-50",
    direction="rate_cut",
    title="Key rate decision",
    description="Official imported decision.",
    is_scheduled="true",
    is_official="true",
    source_url="https://www.cbr.ru/",
    source_type="official_curated",
    source_title="",
    source_note="Synthetic test row.",
    notes="",
):
    return (
        f"{decision_date},{meeting_date},{effective_date},"
        f"{publication_datetime_msk},{rate_before},{rate_after},"
        f"{change_bps},{direction},{title},{description},{is_scheduled},"
        f"{is_official},{source_url},{source_type},{source_title},"
        f"{source_note},{notes}"
    )
