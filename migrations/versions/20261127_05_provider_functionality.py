"""Add provider availability and bid schedule support."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261127_05"
down_revision: str | None = "20261127_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_availability",
        sa.Column(
            "provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("provider_profiles.user_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "is_available", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "timezone", sa.String(64), nullable=False, server_default="Africa/Lagos"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_table(
        "provider_availability_days",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("provider_availability.provider_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("start_time", sa.Time()),
        sa.Column("end_time", sa.Time()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_provider_day_weekday"),
        sa.CheckConstraint(
            "NOT is_enabled OR (start_time IS NOT NULL AND end_time IS NOT NULL "
            "AND start_time < end_time)",
            name="ck_provider_day_hours",
        ),
        sa.UniqueConstraint(
            "provider_id", "weekday", name="uq_provider_availability_day"
        ),
    )
    op.create_index(
        "ix_provider_availability_days_provider_id",
        "provider_availability_days",
        ["provider_id"],
    )
    op.alter_column(
        "bids", "estimated_days", existing_type=sa.Integer(), nullable=True
    )
    op.add_column(
        "bids", sa.Column("proposed_schedule_at", sa.DateTime(timezone=True))
    )
    op.drop_constraint("ck_bids_estimated_days_positive", "bids", type_="check")
    op.create_check_constraint(
        "ck_bids_estimated_days_positive",
        "bids",
        "estimated_days IS NULL OR estimated_days > 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_bids_estimated_days_positive", "bids", type_="check")
    op.create_check_constraint(
        "ck_bids_estimated_days_positive", "bids", "estimated_days > 0"
    )
    op.drop_column("bids", "proposed_schedule_at")
    op.alter_column("bids", "estimated_days", existing_type=sa.Integer(), nullable=False)
    op.drop_index(
        "ix_provider_availability_days_provider_id",
        table_name="provider_availability_days",
    )
    op.drop_table("provider_availability_days")
    op.drop_table("provider_availability")
