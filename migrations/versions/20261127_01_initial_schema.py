"""Create initial marketplace database schema."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261127_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone", sa.String(32)),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
            "role IN ('customer', 'provider', 'admin')", name="ck_users_role"
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("phone", name="uq_users_phone"),
    )
    op.create_table(
        "service_categories",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True)),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
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
        sa.ForeignKeyConstraint(
            ["parent_id"], ["service_categories.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("slug", name="uq_service_categories_slug"),
    )

    profile_columns = {
        "customer_profiles": [
            sa.Column("display_name", sa.String(120), nullable=False),
            sa.Column("default_city", sa.String(100)),
            sa.Column("default_state", sa.String(100)),
        ],
        "provider_profiles": [
            sa.Column("display_name", sa.String(120), nullable=False),
            sa.Column("headline", sa.String(160)),
            sa.Column("bio", sa.Text()),
            sa.Column("avatar_url", sa.String(2048)),
            sa.Column("service_area_city", sa.String(100)),
            sa.Column("service_area_state", sa.String(100)),
            sa.Column("hourly_rate_kobo", sa.BigInteger()),
            sa.Column("primary_category_id", postgresql.UUID(as_uuid=True)),
        ],
        "admin_profiles": [
            sa.Column("display_name", sa.String(120), nullable=False),
            sa.Column("department", sa.String(100)),
        ],
    }
    for table_name, fields in profile_columns.items():
        columns = [
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                nullable=False,
            ),
            *fields,
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
        ]
        constraints = [
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE")
        ]
        if table_name == "provider_profiles":
            constraints.append(
                sa.ForeignKeyConstraint(
                    ["primary_category_id"],
                    ["service_categories.id"],
                    ondelete="SET NULL",
                )
            )
        op.create_table(table_name, *columns, *constraints)


def downgrade() -> None:
    op.drop_table("admin_profiles")
    op.drop_table("provider_profiles")
    op.drop_table("customer_profiles")
    op.drop_table("service_categories")
    op.drop_table("users")
