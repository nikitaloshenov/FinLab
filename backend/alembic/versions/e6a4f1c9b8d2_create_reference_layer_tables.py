"""create reference layer tables

Revision ID: e6a4f1c9b8d2
Revises: d9f1b8c3a4e2
Create Date: 2026-06-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6a4f1c9b8d2"
down_revision: Union[str, Sequence[str], None] = "d9f1b8c3a4e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "data_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=True),
        sa.Column("license_note", sa.Text(), nullable=True),
        sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_data_sources_code"), "data_sources", ["code"], unique=False)
    op.create_index(op.f("ix_data_sources_id"), "data_sources", ["id"], unique=False)
    op.create_index(
        op.f("ix_data_sources_source_type"),
        "data_sources",
        ["source_type"],
        unique=False,
    )

    op.create_table(
        "issuers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("short_name", sa.String(length=255), nullable=True),
        sa.Column("country", sa.String(length=16), nullable=True),
        sa.Column("website", sa.String(length=1024), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_issuers_id"), "issuers", ["id"], unique=False)
    op.create_index(op.f("ix_issuers_is_active"), "issuers", ["is_active"], unique=False)
    op.create_index(op.f("ix_issuers_name"), "issuers", ["name"], unique=False)

    op.create_table(
        "sectors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_sectors_code"), "sectors", ["code"], unique=False)
    op.create_index(op.f("ix_sectors_id"), "sectors", ["id"], unique=False)
    op.create_index(op.f("ix_sectors_is_active"), "sectors", ["is_active"], unique=False)

    op.create_table(
        "instruments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("issuer_id", sa.Integer(), nullable=True),
        sa.Column("secid", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("short_name", sa.String(length=255), nullable=True),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("board", sa.String(length=32), nullable=False),
        sa.Column("market", sa.String(length=64), nullable=False),
        sa.Column("engine", sa.String(length=64), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=True),
        sa.Column("lot_size", sa.Integer(), nullable=True),
        sa.Column("isin", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["issuer_id"], ["issuers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "engine",
            "market",
            "board",
            "secid",
            name="uq_instruments_engine_market_board_secid",
        ),
    )
    op.create_index(op.f("ix_instruments_asset_type"), "instruments", ["asset_type"], unique=False)
    op.create_index(op.f("ix_instruments_id"), "instruments", ["id"], unique=False)
    op.create_index(op.f("ix_instruments_is_active"), "instruments", ["is_active"], unique=False)
    op.create_index(op.f("ix_instruments_isin"), "instruments", ["isin"], unique=False)
    op.create_index(op.f("ix_instruments_issuer_id"), "instruments", ["issuer_id"], unique=False)
    op.create_index(op.f("ix_instruments_secid"), "instruments", ["secid"], unique=False)

    op.create_table(
        "issuer_sector_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("issuer_id", sa.Integer(), nullable=False),
        sa.Column("sector_id", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["issuer_id"], ["issuers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sector_id"], ["sectors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "issuer_id",
            "sector_id",
            "valid_from",
            name="uq_issuer_sector_history_issuer_sector_valid_from",
        ),
    )
    op.create_index(op.f("ix_issuer_sector_history_id"), "issuer_sector_history", ["id"], unique=False)
    op.create_index(
        "ix_issuer_sector_history_issuer_valid_from",
        "issuer_sector_history",
        ["issuer_id", "valid_from"],
        unique=False,
    )
    op.create_index(
        op.f("ix_issuer_sector_history_sector_id"),
        "issuer_sector_history",
        ["sector_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_issuer_sector_history_valid_from"),
        "issuer_sector_history",
        ["valid_from"],
        unique=False,
    )

    op.create_table(
        "benchmarks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("benchmark_type", sa.String(length=64), nullable=False),
        sa.Column("instrument_id", sa.Integer(), nullable=True),
        sa.Column("sector_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sector_id"], ["sectors.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_benchmarks_benchmark_type"), "benchmarks", ["benchmark_type"], unique=False)
    op.create_index(op.f("ix_benchmarks_id"), "benchmarks", ["id"], unique=False)
    op.create_index(op.f("ix_benchmarks_instrument_id"), "benchmarks", ["instrument_id"], unique=False)
    op.create_index(op.f("ix_benchmarks_is_active"), "benchmarks", ["is_active"], unique=False)
    op.create_index(op.f("ix_benchmarks_sector_id"), "benchmarks", ["sector_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_benchmarks_sector_id"), table_name="benchmarks")
    op.drop_index(op.f("ix_benchmarks_is_active"), table_name="benchmarks")
    op.drop_index(op.f("ix_benchmarks_instrument_id"), table_name="benchmarks")
    op.drop_index(op.f("ix_benchmarks_id"), table_name="benchmarks")
    op.drop_index(op.f("ix_benchmarks_benchmark_type"), table_name="benchmarks")
    op.drop_table("benchmarks")

    op.drop_index(op.f("ix_issuer_sector_history_valid_from"), table_name="issuer_sector_history")
    op.drop_index(op.f("ix_issuer_sector_history_sector_id"), table_name="issuer_sector_history")
    op.drop_index("ix_issuer_sector_history_issuer_valid_from", table_name="issuer_sector_history")
    op.drop_index(op.f("ix_issuer_sector_history_id"), table_name="issuer_sector_history")
    op.drop_table("issuer_sector_history")

    op.drop_index(op.f("ix_instruments_secid"), table_name="instruments")
    op.drop_index(op.f("ix_instruments_issuer_id"), table_name="instruments")
    op.drop_index(op.f("ix_instruments_isin"), table_name="instruments")
    op.drop_index(op.f("ix_instruments_is_active"), table_name="instruments")
    op.drop_index(op.f("ix_instruments_id"), table_name="instruments")
    op.drop_index(op.f("ix_instruments_asset_type"), table_name="instruments")
    op.drop_table("instruments")

    op.drop_index(op.f("ix_sectors_is_active"), table_name="sectors")
    op.drop_index(op.f("ix_sectors_id"), table_name="sectors")
    op.drop_index(op.f("ix_sectors_code"), table_name="sectors")
    op.drop_table("sectors")

    op.drop_index(op.f("ix_issuers_name"), table_name="issuers")
    op.drop_index(op.f("ix_issuers_is_active"), table_name="issuers")
    op.drop_index(op.f("ix_issuers_id"), table_name="issuers")
    op.drop_table("issuers")

    op.drop_index(op.f("ix_data_sources_source_type"), table_name="data_sources")
    op.drop_index(op.f("ix_data_sources_id"), table_name="data_sources")
    op.drop_index(op.f("ix_data_sources_code"), table_name="data_sources")
    op.drop_table("data_sources")
