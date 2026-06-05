from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.modules.hypotheses.key_rate_decisions import (
    calculate_change_bps,
    calculate_key_rate_direction,
)
from app.modules.hypotheses.key_rate_decisions_repository import (
    create_key_rate_decision,
    get_key_rate_decision_by_date,
    list_key_rate_decisions,
    upsert_key_rate_decision_by_date,
)
from app.modules.hypotheses.models import KeyRateDecision


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


def test_create_and_get_key_rate_decision_by_date(db_session):
    create_key_rate_decision(
        db_session,
        _decision_data(
            decision_date=date(2026, 5, 15),
            direction="rate_cut",
        ),
    )
    db_session.commit()

    decision = get_key_rate_decision_by_date(db_session, date(2026, 5, 15))

    assert decision is not None
    assert decision.decision_date == date(2026, 5, 15)
    assert decision.direction == "rate_cut"
    assert decision.title == "Key rate decision"
    assert decision.meeting_date is None
    assert decision.effective_date is None
    assert decision.publication_datetime_msk is None
    assert decision.source_title is None
    assert decision.notes is None


def test_upsert_key_rate_decision_by_date_updates_existing_row(db_session):
    create_key_rate_decision(
        db_session,
        _decision_data(
            decision_date=date(2026, 5, 15),
            direction="rate_cut",
            title="Initial title",
        ),
    )
    db_session.commit()

    updated_decision = upsert_key_rate_decision_by_date(
        db_session,
        _decision_data(
            decision_date=date(2026, 5, 15),
            direction="rate_hike",
            title="Updated title",
        ),
    )
    db_session.commit()

    rows = db_session.query(KeyRateDecision).all()

    assert len(rows) == 1
    assert updated_decision.id == rows[0].id
    assert rows[0].direction == "rate_hike"
    assert rows[0].title == "Updated title"


def test_create_and_list_key_rate_decision_with_dataset_fields(db_session):
    publication_datetime = datetime(2026, 5, 15, 13, 30, tzinfo=UTC)

    create_key_rate_decision(
        db_session,
        _decision_data(
            decision_date=date(2026, 5, 15),
            direction="rate_cut",
            meeting_date=date(2026, 5, 15),
            effective_date=date(2026, 5, 19),
            publication_datetime_msk=publication_datetime,
            source_title="Bank of Russia key rate decision",
            notes="Curated official row.",
        ),
    )
    db_session.commit()

    decisions = list_key_rate_decisions(db_session)

    assert len(decisions) == 1
    assert decisions[0].meeting_date == date(2026, 5, 15)
    assert decisions[0].effective_date == date(2026, 5, 19)
    assert decisions[0].publication_datetime_msk == publication_datetime.replace(
        tzinfo=None
    )
    assert decisions[0].source_title == "Bank of Russia key rate decision"
    assert decisions[0].notes == "Curated official row."


def test_upsert_key_rate_decision_by_date_updates_dataset_fields(db_session):
    create_key_rate_decision(
        db_session,
        _decision_data(
            decision_date=date(2026, 5, 15),
            direction="rate_cut",
            source_title="Initial source title",
        ),
    )
    db_session.commit()

    updated_decision = upsert_key_rate_decision_by_date(
        db_session,
        _decision_data(
            decision_date=date(2026, 5, 15),
            direction="rate_cut",
            meeting_date=date(2026, 5, 15),
            effective_date=date(2026, 5, 19),
            publication_datetime_msk=datetime(2026, 5, 15, 13, 30, tzinfo=UTC),
            source_title="Updated source title",
            notes="Updated notes.",
        ),
    )
    db_session.commit()

    assert updated_decision.meeting_date == date(2026, 5, 15)
    assert updated_decision.effective_date == date(2026, 5, 19)
    assert updated_decision.publication_datetime_msk == datetime(
        2026,
        5,
        15,
        13,
        30,
    )
    assert updated_decision.source_title == "Updated source title"
    assert updated_decision.notes == "Updated notes."


def test_list_key_rate_decisions_sorted_desc_and_filtered(db_session):
    create_key_rate_decision(
        db_session,
        _decision_data(
            decision_date=date(2026, 1, 16),
            direction="rate_hold",
            is_official=False,
        ),
    )
    create_key_rate_decision(
        db_session,
        _decision_data(
            decision_date=date(2026, 5, 15),
            direction="rate_cut",
            is_official=True,
        ),
    )
    create_key_rate_decision(
        db_session,
        _decision_data(
            decision_date=date(2026, 2, 14),
            direction="rate_hike",
            is_official=True,
        ),
    )
    db_session.commit()

    all_decisions = list_key_rate_decisions(db_session)
    cut_decisions = list_key_rate_decisions(db_session, direction="rate_cut")
    official_decisions = list_key_rate_decisions(db_session, only_official=True)

    assert [decision.decision_date for decision in all_decisions] == [
        date(2026, 5, 15),
        date(2026, 2, 14),
        date(2026, 1, 16),
    ]
    assert len(cut_decisions) == 1
    assert cut_decisions[0].direction == "rate_cut"
    assert len(official_decisions) == 2
    assert all(decision.is_official is True for decision in official_decisions)


def test_key_rate_direction_and_change_bps_helpers():
    assert (
        calculate_key_rate_direction(Decimal("16.00"), Decimal("15.50"))
        == "rate_cut"
    )
    assert calculate_change_bps(Decimal("16.00"), Decimal("15.50")) == -50

    assert (
        calculate_key_rate_direction(Decimal("15.50"), Decimal("16.00"))
        == "rate_hike"
    )
    assert calculate_change_bps(Decimal("15.50"), Decimal("16.00")) == 50

    assert (
        calculate_key_rate_direction(Decimal("16.00"), Decimal("16.00"))
        == "rate_hold"
    )
    assert calculate_change_bps(Decimal("16.00"), Decimal("16.00")) == 0


def _decision_data(
    decision_date,
    direction,
    title="Key rate decision",
    is_official=True,
    meeting_date=None,
    effective_date=None,
    publication_datetime_msk=None,
    source_title=None,
    notes=None,
):
    return {
        "decision_date": decision_date,
        "meeting_date": meeting_date,
        "effective_date": effective_date,
        "publication_datetime_msk": publication_datetime_msk,
        "rate_before": Decimal("16.00"),
        "rate_after": Decimal("15.50"),
        "change_bps": -50,
        "direction": direction,
        "title": title,
        "description": "Official imported decision.",
        "is_scheduled": True,
        "is_official": is_official,
        "source_url": "https://www.cbr.ru/",
        "source_title": source_title,
        "source_type": "manual_official_import",
        "source_note": "Test row for repository tests.",
        "notes": notes,
    }
