"""Add customer jobs, bids and favorites."""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261127_03"
down_revision: str | None = "20261127_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_categories.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("urgency", sa.String(16), nullable=False, server_default="NORMAL"),
        sa.Column("preferred_date", sa.Date()),
        sa.Column("preferred_time", sa.Time()),
        sa.Column("service_location", sa.String(240), nullable=False),
        sa.Column("budget_kobo", sa.BigInteger()),
        sa.Column(
            "status",
            sa.String(24),
            nullable=False,
            server_default="AWAITING_BIDS",
        ),
        sa.Column(
            "accepted_provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("agreed_price_kobo", sa.BigInteger()),
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
        sa.CheckConstraint(
            "urgency IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')",
            name="ck_jobs_urgency",
        ),
        sa.CheckConstraint(
            "status IN ('AWAITING_BIDS', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')",
            name="ck_jobs_status",
        ),
        sa.CheckConstraint(
            "budget_kobo IS NULL OR budget_kobo >= 0",
            name="ck_jobs_budget",
        ),
        sa.CheckConstraint(
            "agreed_price_kobo IS NULL OR agreed_price_kobo >= 0",
            name="ck_jobs_agreed_price",
        ),
    )
    op.create_index("ix_jobs_customer_id", "jobs", ["customer_id"])
    op.create_index("ix_jobs_category_id", "jobs", ["category_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])

    op.create_table(
        "bids",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("amount_kobo", sa.BigInteger(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("estimated_days", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(16), nullable=False, server_default="PENDING"
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
        sa.CheckConstraint(
            "amount_kobo > 0", name="ck_bids_amount_positive"
        ),
        sa.CheckConstraint(
            "estimated_days > 0", name="ck_bids_estimated_days_positive"
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'ACCEPTED', 'DECLINED')",
            name="ck_bids_status",
        ),
        sa.UniqueConstraint(
            "job_id", "provider_id", name="uq_bids_job_provider"
        ),
    )
    op.create_index("ix_bids_job_id", "bids", ["job_id"])
    op.create_index("ix_bids_provider_id", "bids", ["provider_id"])
    op.create_index("ix_bids_status", "bids", ["status"])

    op.create_table(
        "customer_favorites",
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
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
        sa.UniqueConstraint(
            "customer_id", "provider_id", name="uq_customer_favorites_pair"
        ),
    )

    category_table = sa.table(
        "service_categories",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("is_active", sa.Boolean),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(
        category_table,
        [
            {
                "id": UUID("00000000-0000-4000-8000-000000000001"),
                "slug": "plumbing",
                "name": "Plumbing",
                "description": "Plumbing installation and repairs",
                "is_active": True,
                "sort_order": 1,
            },
            {
                "id": UUID("00000000-0000-4000-8000-000000000002"),
                "slug": "electrical",
                "name": "Electrical",
                "description": "Electrical installation and repairs",
                "is_active": True,
                "sort_order": 2,
            },
            {
                "id": UUID("00000000-0000-4000-8000-000000000003"),
                "slug": "cleaning",
                "name": "Cleaning",
                "description": "Residential and commercial cleaning",
                "is_active": True,
                "sort_order": 3,
            },
            {
                "id": UUID("00000000-0000-4000-8000-000000000004"),
                "slug": "carpentry",
                "name": "Carpentry",
                "description": "Woodwork, furniture and carpentry",
                "is_active": True,
                "sort_order": 4,
            },
            {
                "id": UUID("00000000-0000-4000-8000-000000000005"),
                "slug": "painting",
                "name": "Painting",
                "description": "Interior and exterior painting",
                "is_active": True,
                "sort_order": 5,
            },
            {
                "id": UUID("00000000-0000-4000-8000-000000000006"),
                "slug": "other",
                "name": "Other",
                "description": "Other home services",
                "is_active": True,
                "sort_order": 6,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("customer_favorites")
    op.drop_index("ix_bids_status", table_name="bids")
    op.drop_index("ix_bids_provider_id", table_name="bids")
    op.drop_index("ix_bids_job_id", table_name="bids")
    op.drop_table("bids")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_category_id", table_name="jobs")
    op.drop_index("ix_jobs_customer_id", table_name="jobs")
    op.drop_table("jobs")
    op.execute(
        "DELETE FROM service_categories WHERE slug IN "
        "('plumbing', 'electrical', 'cleaning', 'carpentry', 'painting', 'other')"
    )
