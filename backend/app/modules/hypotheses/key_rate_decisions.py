from __future__ import annotations

from decimal import Decimal
from typing import Literal


KeyRateDecisionDirection = Literal["rate_cut", "rate_hike", "rate_hold"]


def normalize_key_rate_direction(direction: str) -> KeyRateDecisionDirection:
    normalized_direction = direction.strip().lower()

    if normalized_direction not in {"rate_cut", "rate_hike", "rate_hold"}:
        raise ValueError(f"Unsupported key rate decision direction: {direction}")

    return normalized_direction  # type: ignore[return-value]


def calculate_key_rate_direction(
    rate_before: Decimal,
    rate_after: Decimal,
) -> KeyRateDecisionDirection:
    normalized_rate_before = Decimal(rate_before)
    normalized_rate_after = Decimal(rate_after)

    if normalized_rate_after < normalized_rate_before:
        return "rate_cut"

    if normalized_rate_after > normalized_rate_before:
        return "rate_hike"

    return "rate_hold"


def calculate_change_bps(
    rate_before: Decimal,
    rate_after: Decimal,
) -> int:
    normalized_rate_before = Decimal(rate_before)
    normalized_rate_after = Decimal(rate_after)

    return int((normalized_rate_after - normalized_rate_before) * Decimal("100"))
