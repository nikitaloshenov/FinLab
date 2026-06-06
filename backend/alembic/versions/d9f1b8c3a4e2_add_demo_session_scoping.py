"""add demo session scoping

Revision ID: d9f1b8c3a4e2
Revises: c7f4a9b2d1e6
Create Date: 2026-06-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d9f1b8c3a4e2"
down_revision: Union[str, None] = "c7f4a9b2d1e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LEGACY_SESSION_ID = "legacy-demo-session"


def upgrade() -> None:
    op.add_column(
        "watchlist_items",
        sa.Column(
            "session_id",
            sa.String(length=64),
            server_default=LEGACY_SESSION_ID,
            nullable=False,
        ),
    )
    op.add_column(
        "alerts",
        sa.Column(
            "session_id",
            sa.String(length=64),
            server_default=LEGACY_SESSION_ID,
            nullable=False,
        ),
    )
    op.add_column(
        "alert_events",
        sa.Column(
            "session_id",
            sa.String(length=64),
            server_default=LEGACY_SESSION_ID,
            nullable=False,
        ),
    )

    op.alter_column("watchlist_items", "session_id", server_default=None)
    op.alter_column("alerts", "session_id", server_default=None)
    op.alter_column("alert_events", "session_id", server_default=None)

    op.create_index(
        "ix_watchlist_items_session_id",
        "watchlist_items",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_alerts_session_id",
        "alerts",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_alert_events_session_id",
        "alert_events",
        ["session_id"],
        unique=False,
    )

    op.drop_constraint(
        "uq_watchlist_user_ticker",
        "watchlist_items",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_watchlist_session_ticker",
        "watchlist_items",
        ["session_id", "ticker_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_watchlist_session_ticker",
        "watchlist_items",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_watchlist_user_ticker",
        "watchlist_items",
        ["user_key", "ticker_id"],
    )

    op.drop_index("ix_alert_events_session_id", table_name="alert_events")
    op.drop_index("ix_alerts_session_id", table_name="alerts")
    op.drop_index("ix_watchlist_items_session_id", table_name="watchlist_items")

    op.drop_column("alert_events", "session_id")
    op.drop_column("alerts", "session_id")
    op.drop_column("watchlist_items", "session_id")
