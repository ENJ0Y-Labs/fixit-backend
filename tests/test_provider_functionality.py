import uuid
from datetime import date, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.auth import current_user
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.models.customer import Bid, Job
from app.models.profile import CustomerProfile, ProviderProfile
from app.models.provider import ProviderAvailability, ProviderAvailabilityDay
from app.models.service import ProviderService, Service
from app.models.service_category import ServiceCategory
from app.models.user import User


@pytest.fixture
def provider_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    provider = User(
        email="provider@example.test",
        phone="08011111111",
        password_hash="unused",
        role="provider",
        is_active=True,
    )
    other_provider = User(
        email="other-provider@example.test",
        phone="08022222222",
        password_hash="unused",
        role="provider",
        is_active=True,
    )
    customer = User(
        email="customer@example.test",
        phone="08033333333",
        password_hash="unused",
        role="customer",
        is_active=True,
    )
    with factory() as db:
        db.add_all([provider, other_provider, customer])
        db.flush()
        db.add_all(
            [
                ProviderProfile(
                    user_id=provider.id,
                    display_name="Provider One",
                    service_area_city="Port Harcourt",
                    service_area_state="Rivers",
                ),
                ProviderProfile(
                    user_id=other_provider.id, display_name="Other Provider"
                ),
                CustomerProfile(
                    user_id=customer.id,
                    display_name="Customer One",
                    default_city="Port Harcourt",
                    default_state="Rivers",
                ),
            ]
        )
        category = ServiceCategory(
            slug="plumbing", name="Plumbing", is_active=True
        )
        db.add(category)
        db.flush()
        service = Service(
            category_id=category.id,
            slug="tap-repair",
            name="Tap repair",
            is_active=True,
        )
        second_service = Service(
            category_id=category.id,
            slug="pipe-repair",
            name="Pipe repair",
            is_active=True,
        )
        db.add_all([service, second_service])
        db.flush()
        listing = ProviderService(
            provider_id=provider.id,
            service_id=service.id,
            description="Household tap repairs and replacements.",
            pricing_mode="from",
            price_kobo=1500000,
        )
        db.add(listing)
        db.commit()
        ids = {
            "provider": provider.id,
            "other_provider": other_provider.id,
            "customer": customer.id,
            "category": category.id,
            "service": service.id,
            "second_service": second_service.id,
            "listing": listing.id,
        }

    def override_session():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[current_user] = lambda: provider
    with TestClient(app) as client:
        yield client, ids, factory
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def _job(factory, ids, *, status="AWAITING_BIDS"):
    with factory() as db:
        job = Job(
            customer_id=ids["customer"],
            category_id=ids["category"],
            title="Repair leaking kitchen tap",
            description="The kitchen tap leaks around the base and needs repair.",
            urgency="NORMAL",
            preferred_date=date(2026, 12, 2),
            preferred_time=time(10, 0),
            service_location="42 Private Street, Rumuola, Port Harcourt",
            budget_kobo=2500000,
            status=status,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job.id


def test_provider_can_read_and_update_own_profile(provider_client):
    client, _, _ = provider_client
    current = client.get("/api/v1/provider/me")
    assert current.status_code == 200
    assert current.json()["data"]["displayName"] == "Provider One"
    updated = client.patch(
        "/api/v1/provider/me",
        json={
            "displayName": "Provider Updated",
            "bio": "Experienced home plumbing specialist in Port Harcourt.",
            "serviceAreaCity": "Port Harcourt",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["displayName"] == "Provider Updated"
    assert updated.json()["data"]["bio"].startswith("Experienced")


def test_provider_can_manage_only_own_service_listings(provider_client):
    client, ids, _ = provider_client
    current = client.get("/api/v1/provider/me/services").json()["data"]
    assert current["items"][0]["name"] == "Tap repair"
    assert any(item["name"] == "Pipe repair" for item in current["catalogue"])

    created = client.post(
        "/api/v1/provider/me/services",
        json={
            "serviceId": str(ids["second_service"]),
            "description": "Repair and replace damaged household pipes.",
            "pricingMode": "quote",
        },
    )
    assert created.status_code == 201
    listing_id = created.json()["data"]["id"]
    updated = client.patch(
        f"/api/v1/provider/me/services/{listing_id}",
        json={"description": "Pipe repairs and replacements for homes."},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["description"].startswith("Pipe repairs")
    removed = client.delete(f"/api/v1/provider/me/services/{listing_id}")
    assert removed.json()["data"]["removed"]


def test_provider_availability_is_persisted_and_validated(provider_client):
    client, ids, factory = provider_client
    response = client.put(
        "/api/v1/provider/me/availability",
        json={
            "isAvailable": True,
            "timezone": "Africa/Lagos",
            "schedule": [
                {"weekday": 0, "enabled": True, "start": "09:00", "end": "17:00"},
                {"weekday": 1, "enabled": False},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["schedule"][0]["day"] == "Monday"
    assert data["schedule"][0]["enabled"] is True
    assert data["schedule"][1]["enabled"] is False
    with factory() as db:
        assert db.get(ProviderAvailability, ids["provider"]).timezone == "Africa/Lagos"
        day_count = db.query(ProviderAvailabilityDay).filter_by(
            provider_id=ids["provider"]
        ).count()
        assert day_count == 2

    invalid = client.put(
        "/api/v1/provider/me/availability",
        json={
            "isAvailable": True,
            "timezone": "Africa/Lagos",
            "schedule": [
                {"weekday": 0, "enabled": True, "start": "17:00", "end": "09:00"}
            ],
        },
    )
    assert invalid.status_code == 422


def test_provider_discovers_only_matching_jobs_without_private_address(provider_client):
    client, ids, factory = provider_client
    job_id = _job(factory, ids)
    response = client.get("/api/v1/provider/jobs", params={"location": "Port Harcourt"})
    assert response.status_code == 200
    item = response.json()["data"]["items"][0]
    assert item["id"] == str(job_id)
    assert item["location"] == "Port Harcourt, Rivers"
    assert "Private Street" not in str(item)
    assert "08033333333" not in str(item)
    no_matches = client.get(
        "/api/v1/provider/jobs", params={"search": "not-a-real-job"}
    )
    assert no_matches.json()["data"]["items"] == []


def test_provider_can_submit_bid_and_complete_accepted_job(provider_client):
    client, ids, factory = provider_client
    job_id = _job(factory, ids)
    submitted = client.post(
        f"/api/v1/provider/jobs/{job_id}/bids",
        json={
            "price": 24500,
            "currency": "NGN",
            "message": "I will inspect the joint and repair the leak.",
            "proposedSchedule": "2026-12-02T10:30",
        },
    )
    assert submitted.status_code == 201
    bid = submitted.json()["data"]["bid"]
    assert bid["price"] == "24500.00"
    assert bid["status"] == "PENDING"
    assert client.post(
        f"/api/v1/provider/jobs/{job_id}/bids",
        json={"price": 24500, "message": "Duplicate quote"},
    ).status_code == 409
    with factory() as db:
        db.query(Job).filter(Job.id == job_id).update(
            {
                "status": "IN_PROGRESS",
                "accepted_provider_id": ids["provider"],
                "agreed_price_kobo": 2450000,
            }
        )
        db.query(Bid).filter(Bid.id == uuid.UUID(bid["id"])).update(
            {"status": "ACCEPTED"}
        )
        db.commit()

    jobs = client.get("/api/v1/provider/me/jobs").json()["data"]["items"]
    assert jobs[0]["id"] == str(job_id)
    assert jobs[0]["allowedTransitions"] == ["COMPLETE"]
    completed = client.patch(
        f"/api/v1/provider/me/jobs/{job_id}/progress",
        json={"transition": "COMPLETE", "expectedUpdatedAt": jobs[0]["updatedAt"]},
    )
    assert completed.status_code == 200
    assert completed.json()["data"]["job"]["status"] == "COMPLETED"


def test_provider_earnings_separate_estimates_from_agreed_amounts(provider_client):
    client, ids, factory = provider_client
    pending_job = _job(factory, ids)
    accepted_job = _job(factory, ids)
    with factory() as db:
        db.add_all(
            [
                Bid(
                    job_id=pending_job,
                    provider_id=ids["provider"],
                    amount_kobo=2000000,
                    message="Pending quote",
                    estimated_days=None,
                    status="PENDING",
                ),
                Bid(
                    job_id=accepted_job,
                    provider_id=ids["provider"],
                    amount_kobo=2500000,
                    message="Accepted quote",
                    estimated_days=None,
                    status="ACCEPTED",
                ),
            ]
        )
        db.query(Job).filter(Job.id == accepted_job).update(
            {
                "status": "IN_PROGRESS",
                "accepted_provider_id": ids["provider"],
                "agreed_price_kobo": 2500000,
            }
        )
        db.commit()
    response = client.get("/api/v1/provider/me/earnings")
    assert response.status_code == 200
    data = response.json()["data"]
    assert {item["amountType"] for item in data["items"]} == {"estimated", "agreed"}
    assert data["payoutStatus"] == "UNAVAILABLE"
    assert data["paidRecordsAvailable"] is False


def test_provider_cannot_access_another_providers_listing(provider_client):
    client, ids, factory = provider_client
    with factory() as db:
        other_listing = ProviderService(
            provider_id=ids["other_provider"],
            service_id=ids["service"],
            description="Other provider listing",
            pricing_mode="quote",
        )
        db.add(other_listing)
        db.commit()
        listing_id = other_listing.id
    assert client.patch(
        f"/api/v1/provider/me/services/{listing_id}",
        json={"description": "Attempted takeover"},
    ).status_code == 404
