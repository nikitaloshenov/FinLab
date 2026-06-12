from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.events.repository import (
    get_or_create_event_type,
    get_or_create_market_event_target,
    get_preferred_key_rate_source,
    list_key_rate_decisions,
    upsert_event,
    upsert_event_value,
)
from app.modules.hypotheses.models import KeyRateDecision


KEY_RATE_EVENT_TYPE_CODE = "key_rate_decision"


@dataclass
class KeyRateEventsImportResult:
    legacy_decisions_total: int
    events_created: int
    events_updated: int
    event_values_upserted: int
    event_targets_created: int
    event_targets_skipped: int
    skipped: int
    event_type_id: int
    status: str


def import_key_rate_decisions_to_events(
    db: Session,
    *,
    dry_run: bool = False,
) -> KeyRateEventsImportResult:
    source = get_preferred_key_rate_source(db)
    event_type, _ = get_or_create_event_type(
        db,
        code=KEY_RATE_EVENT_TYPE_CODE,
        name="Key rate decision",
        description="Bank of Russia key rate decision event.",
        default_source_id=source.id if source is not None else None,
    )
    decisions = list_key_rate_decisions(db)

    events_created = 0
    events_updated = 0
    event_values_upserted = 0
    event_targets_created = 0
    event_targets_skipped = 0
    skipped = 0

    for decision in decisions:
        if decision.decision_date is None:
            skipped += 1
            continue

        event, created = upsert_event(
            db,
            event_type_id=event_type.id,
            source_event_id=_build_source_event_id(decision),
            event_date=decision.decision_date,
            event_datetime=decision.publication_datetime_msk,
            title=_build_event_title(decision),
            direction=_normalize_direction(decision),
            importance="high",
            source_id=source.id if source is not None else None,
        )
        if created:
            events_created += 1
        else:
            events_updated += 1

        for value in _build_event_values(decision):
            upsert_event_value(db, event_id=event.id, **value)
            event_values_upserted += 1

        _, target_created = get_or_create_market_event_target(db, event_id=event.id)
        if target_created:
            event_targets_created += 1
        else:
            event_targets_skipped += 1

    result = KeyRateEventsImportResult(
        legacy_decisions_total=len(decisions),
        events_created=events_created,
        events_updated=events_updated,
        event_values_upserted=event_values_upserted,
        event_targets_created=event_targets_created,
        event_targets_skipped=event_targets_skipped,
        skipped=skipped,
        event_type_id=event_type.id,
        status="dry_run" if dry_run else "success",
    )

    if dry_run:
        db.rollback()
    else:
        db.commit()

    return result


def _build_source_event_id(decision: KeyRateDecision) -> str:
    return f"key_rate_decision:{decision.decision_date.isoformat()}"


def _build_event_title(decision: KeyRateDecision) -> str:
    if decision.rate_after is None:
        return f"CBR key rate decision: {decision.decision_date.isoformat()}"

    return f"CBR key rate decision: {_format_decimal(decision.rate_after)}%"


def _normalize_direction(decision: KeyRateDecision) -> str:
    if decision.rate_before is not None and decision.rate_after is not None:
        if decision.rate_after > decision.rate_before:
            return "hike"
        if decision.rate_after < decision.rate_before:
            return "cut"
        return "hold"

    return {
        "rate_hike": "hike",
        "rate_cut": "cut",
        "rate_hold": "hold",
    }.get(decision.direction, "unknown")


def _build_event_values(decision: KeyRateDecision) -> list[dict[str, object]]:
    values: list[dict[str, object]] = []

    if decision.rate_after is not None:
        values.append(
            {
                "key": "key_rate",
                "numeric_value": decision.rate_after,
                "unit": "percent",
            },
        )

    if decision.rate_before is not None:
        values.append(
            {
                "key": "previous_key_rate",
                "numeric_value": decision.rate_before,
                "unit": "percent",
            },
        )

    change_bps = _get_change_bps(decision)
    if change_bps is not None:
        values.append(
            {
                "key": "change_bps",
                "numeric_value": Decimal(change_bps),
                "unit": "bps",
            },
        )

    return values


def _get_change_bps(decision: KeyRateDecision) -> int | None:
    if decision.change_bps is not None:
        return decision.change_bps

    if decision.rate_before is None or decision.rate_after is None:
        return None

    return int((decision.rate_after - decision.rate_before) * Decimal("100"))


def _format_decimal(value: Decimal) -> str:
    return format(value.normalize(), "f")
