"""Add catalogue services and provider service listings."""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261127_04"
down_revision: str | None = "20261127_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_categories.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(140), nullable=False),
        sa.Column("name", sa.String(140), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("slug", name="uq_services_slug"),
    )
    op.create_index("ix_services_category_id", "services", ["category_id"])
    op.create_index("ix_services_is_active", "services", ["is_active"])

    op.create_table(
        "provider_services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("provider_profiles.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "service_id",
        sa.Column(
            "pricing_mode",
            sa.String(12),
        sa.Column(
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
            server_default="quote",
        ),
            sa.ForeignKey("services.id", ondelete="RESTRICT"),
            nullable=False,
        sa.UniqueConstraint(
            "provider_id", "service_id", name="uq_provider_services_pair"
    op.create_index(
    op.create_index(
    op.create_index(
        "ix_provider_services_is_active", "provider_services", ["is_active"]
    )
    )
    )
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("pricing_mode", sa.String(12), nullable=False, server_default="quote"),
        sa.Column("price_kobo", sa.BigInteger()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "pricing_mode IN ('from', 'fixed', 'quote')",
            name="ck_provider_services_pricing_mode",
        ),
        sa.CheckConstraint(
            "price_kobo IS NULL OR price_kobo > 0",
            name="ck_provider_services_price_positive",
        ),
        sa.UniqueConstraint("provider_id", "service_id", name="uq_provider_services_pair"),
    )
    op.create_index("ix_provider_services_provider_id", "provider_services", ["provider_id"])
    op.create_index("ix_provider_services_service_id", "provider_services", ["service_id"])
    op.create_index("ix_provider_services_is_active", "provider_services", ["is_active"])

    service_table = sa.table(
        "services",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("category_id", postgresql.UUID(as_uuid=True)),
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("is_active", sa.Boolean),
        sa.column("sort_order", sa.Integer),
    )
    # fmt: off
    catalog = [
        ("00000000-0000-4000-8000-000000000101", "00000000-0000-4000-8000-000000000001", "tap-repair", "Tap repair", "Repair or replace leaking and faulty taps.", 1),  # noqa: E501
        ("00000000-0000-4000-8000-000000000102", "00000000-0000-4000-8000-000000000001", "leak-detection", "Leak detection", "Locate and assess household water leaks.", 2),  # noqa: E501
        ("00000000-0000-4000-8000-000000000103", "00000000-0000-4000-8000-000000000001", "pipe-installation", "Pipe installation", "Install or replace domestic water pipes.", 3),  # noqa: E501
        ("00000000-0000-4000-8000-000000000201", "00000000-0000-4000-8000-000000000002", "socket-repair", "Socket repair", "Inspect and repair faulty electrical sockets.", 1),  # noqa: E501
        ("00000000-0000-4000-8000-000000000202", "00000000-0000-4000-8000-000000000002", "wiring-installation", "Wiring installation", "Install or replace residential electrical wiring.", 2),  # noqa: E501
        ("00000000-0000-4000-8000-000000000203", "00000000-0000-4000-8000-000000000002", "fan-installation", "Fan installation", "Install and connect ceiling or wall fans.", 3),  # noqa: E501
        ("00000000-0000-4000-8000-000000000301", "00000000-0000-4000-8000-000000000003", "deep-cleaning", "Deep cleaning", "Detailed cleaning of rooms, kitchens and bathrooms.", 1),  # noqa: E501
        ("00000000-0000-4000-8000-000000000302", "00000000-0000-4000-8000-000000000003", "move-in-cleaning", "Move-in cleaning", "Prepare a property for a new occupant.", 2),  # noqa: E501
        ("00000000-0000-4000-8000-000000000401", "00000000-0000-4000-8000-000000000004", "furniture-repair", "Furniture repair", "Repair damaged household furniture.", 1),  # noqa: E501
        ("00000000-0000-4000-8000-000000000402", "00000000-0000-4000-8000-000000000004", "cabinet-installation", "Cabinet installation", "Install or fit kitchen and storage cabinets.", 2),  # noqa: E501
        ("00000000-0000-4000-8000-000000000501", "00000000-0000-4000-8000-000000000005", "interior-painting", "Interior painting", "Paint interior walls and ceilings.", 1),  # noqa: E501
        ("00000000-0000-4000-8000-000000000502", "00000000-0000-4000-8000-000000000005", "exterior-painting", "Exterior painting", "Paint exterior walls and surfaces.", 2),  # noqa: E501
    ]
    # fmt: on
    op.bulk_insert(
        service_table,
        [
            {
                "id": UUID(service_id),
                "category_id": UUID(category_id),
                "slug": slug,
                "name": name,
                "description": description,
                "is_active": True,
                "sort_order": order,
            }
            for service_id, category_id, slug, name, description, order in catalog
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_provider_services_is_active", table_name="provider_services")
    op.drop_index("ix_provider_services_service_id", table_name="provider_services")
    op.drop_index("ix_provider_services_provider_id", table_name="provider_services")
    op.drop_table("provider_services")
    op.drop_index("ix_services_is_active", table_name="services")
    op.drop_index("ix_services_category_id", table_name="services")
    op.drop_table("services")
