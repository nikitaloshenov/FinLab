"""create key rate decisions table

Revision ID: b4d2c9a1e7f3
Revises: 8e91a7d2c6b4
Create Date: 2026-06-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b4d2c9a1e7f3"
down_revision: Union[str, Sequence[str], None] = "8e91a7d2c6b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "key_rate_decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("decision_date", sa.Date(), nullable=False),
        sa.Column("rate_before", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("rate_after", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("change_bps", sa.Integer(), nullable=True),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_scheduled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "is_official",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("source_url", sa.String(length=1024), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("source_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "direction IN ('rate_cut', 'rate_hike', 'rate_hold')",
            name="ck_key_rate_decision_direction",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_key_rate_decisions_decision_date",
        "key_rate_decisions",
        ["decision_date"],
        unique=True,
    )
    op.create_index(
        "ix_key_rate_decisions_direction",
        "key_rate_decisions",
        ["direction"],
        unique=False,
    )
    op.create_index(
        "ix_key_rate_decisions_is_official",
        "key_rate_decisions",
        ["is_official"],
        unique=False,
    )
    op.create_index(
        "ix_key_rate_decisions_direction_decision_date",
        "key_rate_decisions",
        ["direction", "decision_date"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_key_rate_decisions_direction_decision_date",
        table_name="key_rate_decisions",
    )
    op.drop_index(
        "ix_key_rate_decisions_is_official",
        table_name="key_rate_decisions",
    )
    op.drop_index(
        "ix_key_rate_decisions_direction",
        table_name="key_rate_decisions",
    )
    op.drop_index(
        "ix_key_rate_decisions_decision_date",
        table_name="key_rate_decisions",
    )
    op.drop_table("key_rate_decisions")
