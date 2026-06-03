from datetime import date
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
):
    return {
        "decision_date": decision_date,
        "rate_before": Decimal("16.00"),
        "rate_after": Decimal("15.50"),
        "change_bps": -50,
        "direction": direction,
        "title": title,
        "description": "Official imported decision.",
        "is_scheduled": True,
        "is_official": is_official,
        "source_url": "https://www.cbr.ru/",
        "source_type": "manual_official_import",
        "source_note": "Test row for repository tests.",
    }
