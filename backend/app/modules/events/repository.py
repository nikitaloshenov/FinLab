from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.events.models import Event, EventTarget, EventType, EventValue
from app.modules.hypotheses.models import KeyRateDecision
from app.modules.reference.models import DataSource


def get_data_source_by_code(db: Session, code: str) -> DataSource | None:
    return db.scalar(select(DataSource).where(DataSource.code == code))


def get_preferred_key_rate_source(db: Session) -> DataSource | None:
    return get_data_source_by_code(db, "cbr") or get_data_source_by_code(db, "manual_seed")


def get_or_create_event_type(
    db: Session,
    *,
    code: str,
    name: str,
    description: str | None,
    default_source_id: int | None,
) -> tuple[EventType, bool]:
    event_type = db.scalar(select(EventType).where(EventType.code == code))

    if event_type is None:
        event_type = EventType(
            code=code,
            name=name,
            description=description,
            default_source_id=default_source_id,
            is_active=True,
        )
        db.add(event_type)
        db.flush()
        return event_type, True

    event_type.name = name
    event_type.description = description
    event_type.default_source_id = default_source_id
    event_type.is_active = True
    db.flush()
    return event_type, False


def list_key_rate_decisions(db: Session) -> list[KeyRateDecision]:
    return list(db.scalars(select(KeyRateDecision).order_by(KeyRateDecision.decision_date)).all())


def get_event_by_source_event_id(
    db: Session,
    *,
    event_type_id: int,
    source_event_id: str,
) -> Event | None:
    return db.scalar(
        select(Event).where(
            Event.event_type_id == event_type_id,
            Event.source_event_id == source_event_id,
        ),
    )


def get_event_by_type_and_date(
    db: Session,
    *,
    event_type_id: int,
    event_date,
) -> Event | None:
    return db.scalar(
        select(Event)
        .where(
            Event.event_type_id == event_type_id,
            Event.event_date == event_date,
        )
        .order_by(Event.id),
    )


def upsert_event(
    db: Session,
    *,
    event_type_id: int,
    source_event_id: str,
    event_date,
    event_datetime,
    title: str,
    direction: str,
    importance: str,
    source_id: int | None,
) -> tuple[Event, bool]:
    event = get_event_by_source_event_id(
        db,
        event_type_id=event_type_id,
        source_event_id=source_event_id,
    ) or get_event_by_type_and_date(
        db,
        event_type_id=event_type_id,
        event_date=event_date,
    )

    if event is None:
        event = Event(
            event_type_id=event_type_id,
            source_event_id=source_event_id,
            event_date=event_date,
            event_datetime=event_datetime,
            title=title,
            direction=direction,
            importance=importance,
            source_id=source_id,
        )
        db.add(event)
        db.flush()
        return event, True

    event.source_event_id = source_event_id
    event.event_datetime = event_datetime
    event.title = title
    event.direction = direction
    event.importance = importance
    event.source_id = source_id
    db.flush()
    return event, False


def upsert_event_value(
    db: Session,
    *,
    event_id: int,
    key: str,
    numeric_value: Decimal | None = None,
    text_value: str | None = None,
    unit: str | None = None,
) -> EventValue:
    event_value = db.scalar(
        select(EventValue).where(
            EventValue.event_id == event_id,
            EventValue.key == key,
        ),
    )

    if event_value is None:
        event_value = EventValue(
            event_id=event_id,
            key=key,
            numeric_value=numeric_value,
            text_value=text_value,
            unit=unit,
        )
        db.add(event_value)
    else:
        event_value.numeric_value = numeric_value
        event_value.text_value = text_value
        event_value.unit = unit

    db.flush()
    return event_value


def get_or_create_market_event_target(db: Session, *, event_id: int) -> tuple[EventTarget, bool]:
    target = db.scalar(
        select(EventTarget).where(
            EventTarget.event_id == event_id,
            EventTarget.target_type == "market",
            EventTarget.instrument_id.is_(None),
            EventTarget.issuer_id.is_(None),
            EventTarget.sector_id.is_(None),
            EventTarget.benchmark_id.is_(None),
        ),
    )

    if target is not None:
        return target, False

    target = EventTarget(event_id=event_id, target_type="market")
    db.add(target)
    db.flush()
    return target, True
