from __future__ import annotations

from datetime import date, datetime

import pytest

from app.modules.hypotheses.key_rate_events import (
    KeyRateEventNotFoundError,
    find_key_rate_event_by_date,
    get_default_key_rate_event,
    get_key_rate_event,
    list_key_rate_events,
    normalize_event_direction,
)


REQUIRED_EVENT_FIELDS = {
    "event_id",
    "event_date",
    "event_type",
    "event_direction",
    "rate_before",
    "rate_after",
    "change_bps",
    "title",
    "description",
    "is_official",
    "source_note",
}


def test_list_key_rate_events_returns_non_empty_desc_sorted_list():
    events = list_key_rate_events()

    assert events
    assert [event["event_date"] for event in events] == sorted(
        [event["event_date"] for event in events],
        reverse=True,
    )


def test_all_key_rate_events_have_required_fields():
    events = list_key_rate_events()

    for event in events:
        assert set(event) == REQUIRED_EVENT_FIELDS
        assert event["event_type"] == "key_rate"
        assert event["event_direction"] in {"rate_cut", "rate_hike", "rate_hold"}


def test_sample_events_are_marked_as_not_official():
    events = list_key_rate_events()

    assert all(event["is_official"] is False for event in events)


def test_list_key_rate_events_filters_by_direction():
    events = list_key_rate_events(direction="rate_cut")

    assert events
    assert all(event["event_direction"] == "rate_cut" for event in events)


def test_list_key_rate_events_filters_by_only_official():
    official_events = list_key_rate_events(only_official=True)
    sample_events = list_key_rate_events(only_official=False)

    assert official_events == []
    assert sample_events
    assert all(event["is_official"] is False for event in sample_events)


def test_get_key_rate_event_returns_event_by_id():
    expected_event = list_key_rate_events()[0]

    event = get_key_rate_event(expected_event["event_id"])

    assert event == expected_event


def test_get_key_rate_event_raises_for_unknown_id():
    with pytest.raises(KeyRateEventNotFoundError):
        get_key_rate_event("unknown_event")


def test_find_key_rate_event_by_date_works_for_date_and_string():
    event_from_date = find_key_rate_event_by_date(date(2026, 5, 15))
    event_from_datetime = find_key_rate_event_by_date(
        datetime(2026, 5, 15, 12, 30),
    )
    event_from_string = find_key_rate_event_by_date("2026-05-15")

    assert event_from_date is not None
    assert event_from_date == event_from_datetime
    assert event_from_date == event_from_string
    assert event_from_date["event_id"] == "key_rate_sample_2026_05_15"


def test_find_key_rate_event_by_date_returns_none_for_unknown_date():
    assert find_key_rate_event_by_date("2030-01-01") is None


def test_get_default_key_rate_event_returns_an_event():
    event = get_default_key_rate_event()

    assert event["event_id"]
    assert event["event_type"] == "key_rate"


def test_get_default_key_rate_event_with_direction_returns_matching_direction():
    event = get_default_key_rate_event(direction="rate_hike")

    assert event["event_direction"] == "rate_hike"


def test_normalize_event_direction_is_case_insensitive():
    assert normalize_event_direction(" RATE_CUT ") == "rate_cut"
    assert normalize_event_direction("Rate_Hike") == "rate_hike"
    assert normalize_event_direction("rate_hold") == "rate_hold"


def test_normalize_event_direction_rejects_invalid_direction():
    with pytest.raises(ValueError):
        normalize_event_direction("rate_pause")


def test_source_note_warns_sample_events_must_be_replaced_before_production():
    events = list_key_rate_events()

    for event in events:
        assert "MVP sample event" in event["source_note"]
        assert "Replace with official Central Bank calendar" in event["source_note"]
        assert "production use" in event["source_note"]
