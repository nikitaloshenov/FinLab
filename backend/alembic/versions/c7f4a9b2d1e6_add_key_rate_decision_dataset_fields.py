"""add key rate decision dataset fields

Revision ID: c7f4a9b2d1e6
Revises: b4d2c9a1e7f3
Create Date: 2026-06-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7f4a9b2d1e6"
down_revision: Union[str, Sequence[str], None] = "b4d2c9a1e7f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "key_rate_decisions",
        sa.Column("meeting_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "key_rate_decisions",
        sa.Column("effective_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "key_rate_decisions",
        sa.Column("publication_datetime_msk", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "key_rate_decisions",
        sa.Column("source_title", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "key_rate_decisions",
        sa.Column("notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("key_rate_decisions", "notes")
    op.drop_column("key_rate_decisions", "source_title")
    op.drop_column("key_rate_decisions", "publication_datetime_msk")
    op.drop_column("key_rate_decisions", "effective_date")
    op.drop_column("key_rate_decisions", "meeting_date")
