import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.models.profile import ProviderProfile
from app.models.service import ProviderService, Service
from app.models.service_category import ServiceCategory
from app.models.user import User


def test_public_service_discovery_and_provider_service_filter():
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
    try:
        with factory() as session:
            category = ServiceCategory(
                slug="electrical", name="Electrical", is_active=True
            )
            session.add(category)
            session.flush()
            service = Service(
                category_id=category.id,
                slug="socket-repair",
                name="Socket repair",
                description="Repair faulty sockets.",
                is_active=True,
            )
            inactive = Service(
                category_id=category.id,
                slug="hidden-service",
                name="Hidden service",
                is_active=False,
            )
            second_service = Service(
                category_id=category.id,
                slug="wiring-repair",
                name="Wiring repair",
                is_active=True,
            )
            user = User(
                email=f"{uuid.uuid4()}@example.test",
                password_hash="not-used",
                role="provider",
                is_active=True,
            )
            session.add_all([service, inactive, second_service, user])
            session.flush()
            profile = ProviderProfile(
                user_id=user.id,
                display_name="Ada Electrician",
                primary_category_id=category.id,
            )
            session.add(profile)
            session.flush()
            session.add(
                ProviderService(
                    provider_id=user.id,
                    service_id=service.id,
                    description="Socket inspection and repair.",
                    pricing_mode="from",
                    price_kobo=250000,
                    is_active=True,
                )
            )
            session.commit()
            category_id = category.id
            service_id = service.id
            provider_id = user.id

        with TestClient(app) as client:
            catalogue = client.get(
                "/api/v1/public/services",
                params={"q": "socket", "categoryId": str(category_id)},
            )
            assert catalogue.status_code == 200
            items = catalogue.json()["data"]["items"]
            assert len(items) == 1
            assert items[0]["name"] == "Socket repair"
            assert items[0]["category"]["name"] == "Electrical"

            hidden = client.get("/api/v1/public/services")
            assert [item["name"] for item in hidden.json()["data"]["items"]] == [
                "Socket repair",
                "Wiring repair",
            ]

            first_page = client.get(
                "/api/v1/public/services", params={"limit": 1}
            )
            assert first_page.status_code == 200
            first_data = first_page.json()["data"]
            assert len(first_data["items"]) == 1
            assert first_data["nextCursor"]
            second_page = client.get(
                "/api/v1/public/services",
                params={"limit": 1, "cursor": first_data["nextCursor"]},
            )
            assert second_page.status_code == 200
            second_data = second_page.json()["data"]
            assert len(second_data["items"]) == 1
            assert first_data["items"][0]["id"] != second_data["items"][0]["id"]

            providers = client.get(
                "/api/v1/public/providers", params={"serviceId": str(service_id)}
            )
            assert providers.status_code == 200
            provider = providers.json()["data"]["items"][0]
            assert provider["id"] == str(provider_id)
            assert provider["services"][0]["price"] == {
                "amount": 2500,
                "currency": "NGN",
            }

            profile_response = client.get(f"/api/v1/public/providers/{provider_id}")
            assert profile_response.status_code == 200
            assert profile_response.json()["data"]["services"][0]["id"] == str(
                service_id
            )

            invalid_cursor = client.get(
                "/api/v1/public/services", params={"cursor": "invalid"}
            )
            assert invalid_cursor.status_code == 422
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
