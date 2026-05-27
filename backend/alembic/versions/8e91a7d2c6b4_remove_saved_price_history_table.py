"""remove saved price history table

Revision ID: 8e91a7d2c6b4
Revises: 3b7d9a2f4c1e
Create Date: 2026-05-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8e91a7d2c6b4"
down_revision: Union[str, Sequence[str], None] = "3b7d9a2f4c1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f("ix_prices_ticker_id"), table_name="prices")
    op.drop_index(op.f("ix_prices_id"), table_name="prices")
    op.drop_table("prices")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "prices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker_id", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("market_time", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["ticker_id"], ["tickers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_prices_ticker_id"), "prices", ["ticker_id"], unique=False)
    op.create_index(op.f("ix_prices_id"), "prices", ["id"], unique=False)
