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
from app.models.service_category import ServiceCategory
from app.models.user import User


@pytest.fixture
def customer_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    customer = User(
        email="customer@example.test",
        password_hash="unused",
        role="customer",
        is_active=True,
    )
    provider = User(
        email="provider@example.test",
        password_hash="unused",
        role="provider",
        is_active=True,
    )
    other_customer = User(
        email="other@example.test",
        password_hash="unused",
        role="customer",
        is_active=True,
    )
    with factory() as db:
        db.add_all([customer, provider, other_customer])
        db.flush()
        db.add_all(
            [
                CustomerProfile(user_id=customer.id, display_name="Customer One"),
                CustomerProfile(user_id=other_customer.id, display_name="Customer Two"),
                ProviderProfile(user_id=provider.id, display_name="Provider One"),
            ]
        )
        category = ServiceCategory(slug="plumbing", name="Plumbing", is_active=True)
        db.add(category)
        db.commit()
        db.refresh(customer)
        db.refresh(provider)
        db.refresh(other_customer)
        customer_id, provider_id, other_id, category_id = (
            customer.id,
            provider.id,
            other_customer.id,
            category.id,
        )

    def override_session():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[current_user] = lambda: customer
    with TestClient(app) as client:
        yield client, (customer_id, provider_id, other_id, category_id), factory
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def _job(factory, customer_id, category_id, status="AWAITING_BIDS"):
    with factory() as db:
        job = Job(
            customer_id=customer_id,
            category_id=category_id,
            title="Repair kitchen tap",
            description="The kitchen tap is leaking badly.",
            urgency="NORMAL",
            preferred_date=date(2026, 12, 1),
            preferred_time=time(10, 0),
            service_location="Rumuola, Port Harcourt",
            budget_kobo=2500000,
            status=status,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job.id


def test_customer_profile_can_be_read_and_updated(customer_client):
    client, _, _ = customer_client
    assert client.get("/api/v1/customer/me").json()["data"]["displayName"] == "Customer One"
    response = client.patch(
        "/api/v1/customer/me",
        json={"displayName": "Updated Name", "defaultCity": "Port Harcourt"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["displayName"] == "Updated Name"
    assert response.json()["data"]["defaultCity"] == "Port Harcourt"


def test_customer_can_create_list_edit_and_cancel_own_job(customer_client):
    client, (_, _, _, category_id), _ = customer_client
    response = client.post(
        "/api/v1/customer/me/jobs",
        json={
            "title": "Repair kitchen tap",
            "category": str(category_id),
            "description": "The kitchen tap is leaking badly.",
            "urgency": "urgent",
            "date": "2026-12-01",
            "time": "10:00:00",
            "location": "Rumuola, Port Harcourt",
            "budget": 25000,
        },
    )
    assert response.status_code == 201
    job = response.json()["data"]
    assert job["status"] == "AWAITING_BIDS"
    assert job["budgetKobo"] == 2500000
    assert job["budget"] == "25000.00"
    job_id = job["id"]
    assert client.get("/api/v1/customer/me/jobs").json()["data"]["items"][0]["id"] == job_id

    update = client.patch(
        f"/api/v1/customer/me/jobs/{job_id}",
        json={"title": "Repair leaking kitchen tap"},
    )
    assert update.status_code == 200
    assert update.json()["data"]["title"] == "Repair leaking kitchen tap"

    cancelled = client.post(f"/api/v1/customer/me/jobs/{job_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["status"] == "CANCELLED"


def test_customer_cannot_read_or_mutate_another_customers_job(customer_client):
    client, (_, _, other_id, category_id), factory = customer_client
    job_id = _job(factory, other_id, category_id)
    assert client.get(f"/api/v1/customer/me/jobs/{job_id}").status_code == 404
    assert client.patch(
        f"/api/v1/customer/me/jobs/{job_id}", json={"title": "Changed title"}
    ).status_code == 404
    assert client.post(f"/api/v1/customer/me/jobs/{job_id}/cancel").status_code == 404


def test_customer_cannot_edit_or_cancel_job_after_state_transition(customer_client):
    client, (customer_id, _, _, category_id), factory = customer_client
    job_id = _job(factory, customer_id, category_id, status="IN_PROGRESS")
    assert client.patch(
        f"/api/v1/customer/me/jobs/{job_id}", json={"title": "Changed title"}
    ).status_code == 409
    assert client.post(f"/api/v1/customer/me/jobs/{job_id}/cancel").status_code == 409


def test_customer_can_view_and_accept_bid_atomically(customer_client):
    client, (customer_id, provider_id, _, category_id), factory = customer_client
    job_id = _job(factory, customer_id, category_id)
    with factory() as db:
        first = Bid(
            job_id=job_id,
            provider_id=provider_id,
            amount_kobo=1800000,
            message="I can repair this tap.",
            estimated_days=1,
        )
        second_provider = User(
            email="provider2@example.test",
            password_hash="unused",
            role="provider",
            is_active=True,
        )
        db.add(second_provider)
        db.flush()
        db.add(
            Bid(
                job_id=job_id,
                provider_id=second_provider.id,
                amount_kobo=2000000,
                message="I can do the repair.",
                estimated_days=2,
            )
        )
        db.add(first)
        db.commit()
        bid_id = first.id
    bids = client.get(f"/api/v1/customer/me/jobs/{job_id}/bids")
    assert bids.status_code == 200
    assert len(bids.json()["data"]["items"]) == 2
    accepted = client.post(
        f"/api/v1/customer/me/jobs/{job_id}/bids/{bid_id}/accept"
    )
    assert accepted.status_code == 200
    assert accepted.json()["data"]["status"] == "IN_PROGRESS"
    with factory() as db:
        assert db.get(Bid, bid_id).status == "ACCEPTED"
        assert db.query(Bid).filter(Bid.job_id == job_id, Bid.status == "DECLINED").count() == 1


def test_accepting_a_bid_for_another_job_is_rejected(customer_client):
    client, (customer_id, provider_id, _, category_id), factory = customer_client
    job_id = _job(factory, customer_id, category_id)
    other_job_id = _job(factory, customer_id, category_id)
    with factory() as db:
        bid = Bid(
            job_id=other_job_id,
            provider_id=provider_id,
            amount_kobo=1800000,
            message="Offer",
            estimated_days=1,
        )
        db.add(bid)
        db.commit()
        bid_id = bid.id
    assert client.post(
        f"/api/v1/customer/me/jobs/{job_id}/bids/{bid_id}/accept"
    ).status_code == 404


def test_favorites_are_idempotent_and_customer_scoped(customer_client):
    client, (_, provider_id, _, _), _ = customer_client
    url = f"/api/v1/customer/me/favorites/{provider_id}"
    assert client.put(url).status_code == 200
    assert client.put(url).status_code == 200
    favorites = client.get("/api/v1/customer/me/favorites")
    assert len(favorites.json()["data"]["items"]) == 1
    assert client.delete(url).json()["data"]["favorited"] is False
    assert client.get("/api/v1/customer/me/favorites").json()["data"]["items"] == []


def test_customer_routes_reject_non_customer_roles(customer_client):
    client, _, _ = customer_client
    app.dependency_overrides[current_user] = lambda: User(
        id=uuid.uuid4(),
        email="provider-role@example.test",
        password_hash="unused",
        role="provider",
        is_active=True,
    )
    assert client.get("/api/v1/customer/me").status_code == 403
