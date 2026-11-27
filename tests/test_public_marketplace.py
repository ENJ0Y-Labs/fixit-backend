import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.models.profile import ProviderProfile
from app.models.service_category import ServiceCategory
from app.models.user import User


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_session():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def marketplace_records(client):
    with next(app.dependency_overrides[get_db_session]()) as session:
        category = ServiceCategory(
            slug="electrical",
            name="Electrical",
            description="Electrical repairs",
            is_active=True,
            sort_order=1,
        )
        hidden_category = ServiceCategory(
            slug="inactive",
            name="Inactive",
            is_active=False,
        )
        session.add_all([category, hidden_category])
        session.flush()

        providers = []
        for name, city, active, role in [
            ("Ada Electrician", "Port Harcourt", True, "provider"),
            ("Bola Electrician", "Lagos", True, "provider"),
            ("Hidden Provider", "Port Harcourt", False, "provider"),
            ("Customer Account", "Port Harcourt", True, "customer"),
        ]:
            user = User(
                email=f"{uuid.uuid4()}@example.test",
                password_hash="not-used-in-this-test",
                role=role,
                is_active=active,
            )
            profile = ProviderProfile(
                user=user,
                display_name=name,
                headline="Electrical specialist",
                bio="Residential repairs",
                service_area_city=city,
                service_area_state="Rivers" if city == "Port Harcourt" else "Lagos",
                hourly_rate_kobo=650000,
                primary_category=category,
            ) if role == "provider" else None
            session.add(user)
            if profile:
                session.add(profile)
                providers.append(profile)
        session.commit()
        return category, providers


def test_public_categories_exclude_inactive_categories(client, marketplace_records):
    response = client.get("/api/v1/public/categories")

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert [item["slug"] for item in items] == ["electrical"]


def test_provider_directory_filters_active_providers_by_search_and_location(
    client, marketplace_records
):
    response = client.get(
        "/api/v1/public/providers",
        params={"q": "electrician", "city": "Port Harcourt"},
    )

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["displayName"] == "Ada Electrician"


def test_provider_directory_supports_category_slug_and_cursor(
    client, marketplace_records
):
    first_page = client.get(
        "/api/v1/public/providers",
        params={"category": "electrical", "limit": 1},
    )

    assert first_page.status_code == 200
    first_data = first_page.json()["data"]
    assert len(first_data["items"]) == 1
    assert first_data["nextCursor"]

    second_page = client.get(
        "/api/v1/public/providers",
        params={"category": "electrical", "limit": 1, "cursor": first_data["nextCursor"]},
    )

    assert second_page.status_code == 200
    assert len(second_page.json()["data"]["items"]) == 1
    assert (
        first_data["items"][0]["id"]
        != second_page.json()["data"]["items"][0]["id"]
    )


def test_provider_profile_is_public_safe(client, marketplace_records):
    _, providers = marketplace_records
    provider_id = str(providers[0].user_id)

    response = client.get(f"/api/v1/public/providers/{provider_id}")

    assert response.status_code == 200
    provider = response.json()["data"]
    assert provider["displayName"] == "Ada Electrician"
    assert provider["category"]["name"] == "Electrical"
    assert provider["hourlyRate"]["amount"] == 6500
    assert "email" not in provider
    assert "phone" not in provider
    assert "password_hash" not in provider


def test_private_provider_profile_returns_not_found(client, marketplace_records):
    with next(app.dependency_overrides[get_db_session]()) as session:
        private_user = User(
            email="private@example.test",
            password_hash="not-used-in-this-test",
            role="provider",
            is_active=False,
        )
        session.add(private_user)
        session.flush()
        session.add(
            ProviderProfile(user_id=private_user.id, display_name="Private Provider")
        )
        session.commit()
        provider_id = str(private_user.id)

    response = client.get(f"/api/v1/public/providers/{provider_id}")
    assert response.status_code == 404


def test_invalid_provider_cursor_returns_validation_error(client):
    response = client.get("/api/v1/public/providers", params={"cursor": "invalid"})
    assert response.status_code == 422
