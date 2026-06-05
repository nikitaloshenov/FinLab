from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal


EventDirection = Literal["rate_cut", "rate_hike", "rate_hold"]


# TODO: This is an MVP/static sample legacy layer.
# Production key-rate analysis should use the key_rate_decisions table.
class KeyRateEventNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class KeyRateEvent:
    event_id: str
    event_date: date
    event_type: str
    event_direction: EventDirection
    rate_before: Decimal | None
    rate_after: Decimal | None
    change_bps: int | None
    title: str
    description: str
    is_official: bool
    source_note: str


SAMPLE_SOURCE_NOTE = (
    "MVP sample event. Replace with official Central Bank calendar before "
    "production use."
)


KEY_RATE_EVENTS: tuple[KeyRateEvent, ...] = (
    KeyRateEvent(
        event_id="key_rate_sample_2026_05_15",
        event_date=date(2026, 5, 15),
        event_type="key_rate",
        event_direction="rate_cut",
        rate_before=None,
        rate_after=None,
        change_bps=None,
        title="Тестовое событие ключевой ставки",
        description=(
            "Тестовая дата для проверки Hypothesis Lab. Событие не является "
            "официальными данными и должно быть заменено перед production use."
        ),
        is_official=False,
        source_note=SAMPLE_SOURCE_NOTE,
    ),
    KeyRateEvent(
        event_id="key_rate_sample_cut",
        event_date=date(2026, 3, 20),
        event_type="key_rate",
        event_direction="rate_cut",
        rate_before=None,
        rate_after=None,
        change_bps=None,
        title="Sample-сценарий снижения ключевой ставки",
        description=(
            "MVP sample event для проверки сценария rate_cut. Не является "
            "официальными данными."
        ),
        is_official=False,
        source_note=SAMPLE_SOURCE_NOTE,
    ),
    KeyRateEvent(
        event_id="key_rate_sample_hike",
        event_date=date(2026, 2, 14),
        event_type="key_rate",
        event_direction="rate_hike",
        rate_before=None,
        rate_after=None,
        change_bps=None,
        title="Sample-сценарий повышения ключевой ставки",
        description=(
            "MVP sample event для проверки сценария rate_hike. Не является "
            "официальными данными."
        ),
        is_official=False,
        source_note=SAMPLE_SOURCE_NOTE,
    ),
    KeyRateEvent(
        event_id="key_rate_sample_hold",
        event_date=date(2026, 1, 16),
        event_type="key_rate",
        event_direction="rate_hold",
        rate_before=None,
        rate_after=None,
        change_bps=None,
        title="Sample-сценарий сохранения ключевой ставки",
        description=(
            "MVP sample event для проверки сценария rate_hold. Не является "
            "официальными данными."
        ),
        is_official=False,
        source_note=SAMPLE_SOURCE_NOTE,
    ),
)


def list_key_rate_events(
    direction: str | None = None,
    only_official: bool | None = None,
) -> list[dict]:
    normalized_direction = (
        normalize_event_direction(direction)
        if direction is not None
        else None
    )
    events = sorted(KEY_RATE_EVENTS, key=lambda event: event.event_date, reverse=True)

    if normalized_direction is not None:
        events = [
            event
            for event in events
            if event.event_direction == normalized_direction
        ]

    if only_official is not None:
        events = [
            event
            for event in events
            if event.is_official is only_official
        ]

    return [_event_to_dict(event) for event in events]


def get_key_rate_event(event_id: str) -> dict:
    normalized_event_id = event_id.strip()

    for event in KEY_RATE_EVENTS:
        if event.event_id == normalized_event_id:
            return _event_to_dict(event)

    raise KeyRateEventNotFoundError(
        f"Key rate event not found: event_id={event_id}"
    )


def find_key_rate_event_by_date(event_date) -> dict | None:
    normalized_event_date = _normalize_event_date(event_date)

    for event in KEY_RATE_EVENTS:
        if event.event_date == normalized_event_date:
            return _event_to_dict(event)

    return None


def get_default_key_rate_event(direction: str | None = None) -> dict:
    events = list_key_rate_events(direction=direction)

    if not events:
        if direction is None:
            raise KeyRateEventNotFoundError("Default key rate event not found.")

        raise KeyRateEventNotFoundError(
            f"Default key rate event not found: direction={direction}"
        )

    return events[0]


def normalize_event_direction(direction: str) -> EventDirection:
    normalized_direction = direction.strip().lower()

    if normalized_direction not in {"rate_cut", "rate_hike", "rate_hold"}:
        raise ValueError(f"Unsupported key rate event direction: {direction}")

    return normalized_direction  # type: ignore[return-value]


def _normalize_event_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        return date.fromisoformat(value.strip())

    raise TypeError(f"Unsupported event date value: {value!r}")


def _event_to_dict(event: KeyRateEvent) -> dict:
    return asdict(event)


__all__ = [
    "KeyRateEvent",
    "KeyRateEventNotFoundError",
    "find_key_rate_event_by_date",
    "get_default_key_rate_event",
    "get_key_rate_event",
    "list_key_rate_events",
    "normalize_event_direction",
]
