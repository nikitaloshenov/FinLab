from decimal import Decimal

from app.modules.alerts.service import build_alert_message, is_alert_triggered


def test_is_alert_triggered_above():
    assert is_alert_triggered(
        "above",
        current_price=Decimal("110"),
        target_price=Decimal("100"),
    )

    assert not is_alert_triggered(
        "above",
        current_price=Decimal("90"),
        target_price=Decimal("100"),
    )


def test_is_alert_triggered_below():
    assert is_alert_triggered(
        "below",
        current_price=Decimal("90"),
        target_price=Decimal("100"),
    )

    assert not is_alert_triggered(
        "below",
        current_price=Decimal("110"),
        target_price=Decimal("100"),
    )


def test_is_alert_triggered_unknown_condition():
    assert not is_alert_triggered(
        "unknown",
        current_price=Decimal("100"),
        target_price=Decimal("100"),
    )


def test_build_alert_message_above():
    message = build_alert_message(
        secid="SBER",
        condition="above",
        current_price=Decimal("110"),
        target_price=Decimal("100"),
    )

    assert "SBER" in message
    assert "110" in message
    assert "100" in message
    assert "above or equal" in message


def test_build_alert_message_below():
    message = build_alert_message(
        secid="SBER",
        condition="below",
        current_price=Decimal("90"),
        target_price=Decimal("100"),
    )

    assert "SBER" in message
    assert "90" in message
    assert "100" in message
    assert "below or equal" in message
