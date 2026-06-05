from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.modules.hypotheses.key_rate_decisions import normalize_key_rate_direction
from app.modules.hypotheses.models import KeyRateDecision


def key_rate_decision_to_dict(decision: KeyRateDecision) -> dict[str, Any]:
    return {
        "id": decision.id,
        "decision_date": decision.decision_date,
        "meeting_date": decision.meeting_date,
        "effective_date": decision.effective_date,
        "publication_datetime_msk": decision.publication_datetime_msk,
        "rate_before": decision.rate_before,
        "rate_after": decision.rate_after,
        "change_bps": decision.change_bps,
        "direction": decision.direction,
        "title": decision.title,
        "description": decision.description,
        "is_scheduled": decision.is_scheduled,
        "is_official": decision.is_official,
        "source_url": decision.source_url,
        "source_title": decision.source_title,
        "source_type": decision.source_type,
        "source_note": decision.source_note,
        "notes": decision.notes,
        "created_at": decision.created_at,
        "updated_at": decision.updated_at,
    }


def create_key_rate_decision(
    db: Session,
    data: dict[str, Any],
) -> KeyRateDecision:
    decision_data = _normalize_decision_data(data)
    decision = KeyRateDecision(**decision_data)

    db.add(decision)
    db.flush()

    return decision


def get_key_rate_decision_by_id(
    db: Session,
    decision_id: int,
) -> KeyRateDecision | None:
    return db.query(KeyRateDecision).filter(KeyRateDecision.id == decision_id).first()


def get_key_rate_decision_by_date(
    db: Session,
    decision_date: date,
) -> KeyRateDecision | None:
    return (
        db.query(KeyRateDecision)
        .filter(KeyRateDecision.decision_date == decision_date)
        .first()
    )


def list_key_rate_decisions(
    db: Session,
    direction: str | None = None,
    only_official: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[KeyRateDecision]:
    query = _apply_key_rate_decision_filters(
        db.query(KeyRateDecision),
        direction=direction,
        only_official=only_official,
    )

    return (
        query.order_by(KeyRateDecision.decision_date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def count_key_rate_decisions(
    db: Session,
    direction: str | None = None,
    only_official: bool | None = None,
) -> int:
    query = _apply_key_rate_decision_filters(
        db.query(KeyRateDecision),
        direction=direction,
        only_official=only_official,
    )

    return query.count()


def upsert_key_rate_decision_by_date(
    db: Session,
    data: dict[str, Any],
) -> KeyRateDecision:
    decision_data = _normalize_decision_data(data)
    decision = get_key_rate_decision_by_date(db, decision_data["decision_date"])

    if decision is None:
        return create_key_rate_decision(db, decision_data)

    for field_name, value in decision_data.items():
        setattr(decision, field_name, value)

    db.flush()

    return decision


def _apply_key_rate_decision_filters(query, direction, only_official):
    if direction is not None:
        query = query.filter(
            KeyRateDecision.direction == normalize_key_rate_direction(direction)
        )

    if only_official is not None:
        query = query.filter(KeyRateDecision.is_official.is_(only_official))

    return query


def _normalize_decision_data(data: dict[str, Any]) -> dict[str, Any]:
    decision_data = dict(data)

    if "direction" in decision_data:
        decision_data["direction"] = normalize_key_rate_direction(
            decision_data["direction"]
        )

    return decision_data
