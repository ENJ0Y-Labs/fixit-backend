from sqlalchemy import inspect

from app.core.config import get_settings
from app.db.session import get_engine


def test_initial_migration_creates_expected_tables() -> None:
    table_names = set(inspect(get_engine()).get_table_names())
    assert {
        "alembic_version",
        "users",
        "customer_profiles",
        "provider_profiles",
        "admin_profiles",
        "service_categories",
        "services",
        "provider_services",
        "provider_availability",
        "provider_availability_days",
        "jobs",
        "bids",
        "customer_favorites",
    }.issubset(table_names)


def test_profile_tables_use_user_id_as_primary_key() -> None:
    inspector = inspect(get_engine())
    for table_name in ("customer_profiles", "provider_profiles", "admin_profiles"):
        assert inspector.get_pk_constraint(table_name)["constrained_columns"] == [
            "user_id"
        ]


def test_database_url_uses_postgresql_driver() -> None:
    assert get_settings().database_url.startswith("postgresql+psycopg://")
