from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.hypotheses.key_rate_decisions_repository import (
    count_key_rate_decisions,
    get_key_rate_decision_by_id,
    key_rate_decision_to_dict,
    list_key_rate_decisions,
    upsert_key_rate_decision_by_date,
)


class KeyRateDecisionNotFoundError(Exception):
    pass


def list_decisions(
    db: Session,
    direction: str | None = None,
    only_official: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    decisions = list_key_rate_decisions(
        db,
        direction=direction,
        only_official=only_official,
        limit=limit,
        offset=offset,
    )
    total = count_key_rate_decisions(
        db,
        direction=direction,
        only_official=only_official,
    )

    return {
        "items": [key_rate_decision_to_dict(decision) for decision in decisions],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_decision(
    db: Session,
    decision_id: int,
) -> dict[str, Any]:
    decision = get_key_rate_decision_by_id(db, decision_id)

    if decision is None:
        raise KeyRateDecisionNotFoundError(
            f"Key rate decision not found: id={decision_id}"
        )

    return key_rate_decision_to_dict(decision)


def upsert_decision(
    db: Session,
    data: dict[str, Any],
) -> dict[str, Any]:
    decision = upsert_key_rate_decision_by_date(db, data)

    return key_rate_decision_to_dict(decision)
