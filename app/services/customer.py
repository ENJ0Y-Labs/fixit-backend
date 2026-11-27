import base64
import binascii
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.customer import Bid, Favorite, Job
from app.models.profile import CustomerProfile, ProviderProfile
from app.models.service_category import ServiceCategory
from app.models.user import User


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"code": code, "message": message},
    )


def _category(db: Session, value: str) -> ServiceCategory:
    try:
        category_id = uuid.UUID(value)
    except ValueError:
        category = db.scalar(
            select(ServiceCategory).where(
                or_(
                    ServiceCategory.slug == value.lower(),
                    func.lower(ServiceCategory.name) == value.lower(),
                ),
                ServiceCategory.is_active.is_(True),
            )
        )
    else:
        category = db.scalar(
            select(ServiceCategory).where(
                ServiceCategory.id == category_id,
                ServiceCategory.is_active.is_(True),
            )
        )
    if not category:
        raise _error(422, "CATEGORY_INVALID", "Choose an active service category.")
    return category


def _profile_payload(user: User, profile: CustomerProfile) -> dict:
    return {
        "id": str(user.id),
        "displayName": profile.display_name,
        "email": user.email,
        "phone": user.phone,
        "defaultCity": profile.default_city,
        "defaultState": profile.default_state,
    }


def get_customer_profile(db: Session, user: User) -> dict:
    profile = db.get(CustomerProfile, user.id)
    if not profile:
        raise _error(404, "PROFILE_NOT_FOUND", "Customer profile was not found.")
    return _profile_payload(user, profile)


def update_customer_profile(db: Session, user: User, changes: dict) -> dict:
    profile = db.get(CustomerProfile, user.id)
    if not profile:
        raise _error(404, "PROFILE_NOT_FOUND", "Customer profile was not found.")
    for field, value in changes.items():
        if field == "displayName":
            profile.display_name = value
        elif field == "defaultCity":
            profile.default_city = value
        elif field == "defaultState":
            profile.default_state = value
    db.commit()
    db.refresh(profile)
    return _profile_payload(user, profile)


def _encode_cursor(created_at: datetime, job_id: uuid.UUID) -> str:
    raw = json.dumps(
        {"createdAt": created_at.astimezone(timezone.utc).isoformat(), "id": str(job_id)},
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        payload = json.loads(raw.decode())
        created_at = datetime.fromisoformat(payload["createdAt"])
        job_id = uuid.UUID(payload["id"])
        if created_at.tzinfo is None:
            raise ValueError
        return created_at, job_id
    except (ValueError, TypeError, KeyError, binascii.Error, UnicodeDecodeError) as exc:
        raise _error(422, "CURSOR_INVALID", "The pagination cursor is invalid.") from exc


def list_customer_jobs(
    db: Session, customer_id: uuid.UUID, *, limit: int, cursor: str | None
) -> tuple[list[Job], str | None]:
    statement = (
        select(Job)
        .options(joinedload(Job.category), selectinload(Job.bids))
        .where(Job.customer_id == customer_id)
    )
    if cursor:
        created_at, job_id = _decode_cursor(cursor)
        statement = statement.where(
            or_(
                Job.created_at < created_at,
                and_(Job.created_at == created_at, Job.id < job_id),
            )
        )
    jobs = list(
        db.scalars(
            statement.order_by(Job.created_at.desc(), Job.id.desc()).limit(limit + 1)
        ).unique()
    )
    has_more = len(jobs) > limit
    page = jobs[:limit]
    next_cursor = (
        _encode_cursor(page[-1].created_at, page[-1].id)
        if has_more and page
        else None
    )
    return page, next_cursor


def get_customer_job(db: Session, customer_id: uuid.UUID, job_id: uuid.UUID) -> Job:
    job = db.scalar(
        select(Job)
        .options(joinedload(Job.category), selectinload(Job.bids))
        .where(Job.id == job_id, Job.customer_id == customer_id)
    )
    if not job:
        raise _error(404, "JOB_NOT_FOUND", "Job was not found.")
    return job


def create_customer_job(db: Session, customer_id: uuid.UUID, payload: dict) -> Job:
    category = _category(db, payload["category"])
    job = Job(
        customer_id=customer_id,
        category_id=category.id,
        title=payload["title"],
        description=payload["description"],
        urgency=payload["urgency"],
        preferred_date=payload.get("preferredDate"),
        preferred_time=payload.get("preferredTime"),
        service_location=payload["serviceLocation"],
        budget_kobo=(
            int(payload["budget"] * 100) if payload.get("budget") is not None else None
        ),
        status="AWAITING_BIDS",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    job.category = category
    return job


def update_customer_job(
    db: Session, customer_id: uuid.UUID, job_id: uuid.UUID, changes: dict
) -> Job:
    job = get_customer_job(db, customer_id, job_id)
    if job.status != "AWAITING_BIDS":
        raise _error(409, "JOB_NOT_EDITABLE", "Only jobs awaiting bids can be edited.")
    if "category" in changes and changes["category"] is not None:
        job.category_id = _category(db, changes.pop("category")).id
    mapping = {
        "title": "title",
        "description": "description",
        "urgency": "urgency",
        "preferredDate": "preferred_date",
        "preferredTime": "preferred_time",
        "serviceLocation": "service_location",
        "budget": "budget_kobo",
    }
    for key, field in mapping.items():
        if key in changes:
            value = changes[key]
            if key in {"title", "description", "urgency", "serviceLocation"} and value is None:
                raise _error(422, "FIELD_REQUIRED", f"{key} cannot be null.")
            if key == "budget" and value is not None:
                value = int(value * 100)
            setattr(job, field, value)
    db.commit()
    db.refresh(job)
    job.category = db.get(ServiceCategory, job.category_id)
    return job


def cancel_customer_job(
    db: Session, customer_id: uuid.UUID, job_id: uuid.UUID
) -> Job:
    job = get_customer_job(db, customer_id, job_id)
    if job.status != "AWAITING_BIDS":
        raise _error(409, "JOB_NOT_CANCELLABLE", "This job can no longer be cancelled.")
    job.status = "CANCELLED"
    db.commit()
    db.refresh(job)
    return job


def list_customer_bids(db: Session, customer_id: uuid.UUID, job_id: uuid.UUID) -> list[Bid]:
    get_customer_job(db, customer_id, job_id)
    return list(
        db.scalars(
            select(Bid)
            .join(Bid.job)
            .options(
                joinedload(Bid.job),
                joinedload(Bid.job, Job.category),
                joinedload(Bid.provider).joinedload(User.provider_profile),
            )
            .where(Bid.job_id == job_id)
            .order_by(Bid.created_at.asc(), Bid.id.asc())
        ).unique()
    )


def accept_customer_bid(
    db: Session, customer_id: uuid.UUID, job_id: uuid.UUID, bid_id: uuid.UUID
) -> Job:
    job = db.scalar(
        select(Job)
        .where(Job.id == job_id, Job.customer_id == customer_id)
        .with_for_update()
    )
    if not job:
        raise _error(404, "JOB_NOT_FOUND", "Job was not found.")
    if job.status != "AWAITING_BIDS":
        raise _error(409, "JOB_NOT_ACCEPTING_BIDS", "This job is no longer accepting bids.")
    bid = db.scalar(
        select(Bid).where(
            Bid.id == bid_id, Bid.job_id == job_id, Bid.status == "PENDING"
        )
    )
    if not bid:
        raise _error(404, "BID_NOT_FOUND", "Pending bid was not found for this job.")
    job.status = "IN_PROGRESS"
    job.accepted_provider_id = bid.provider_id
    job.agreed_price_kobo = bid.amount_kobo
    bid.status = "ACCEPTED"
    db.execute(
        update(Bid)
        .where(Bid.job_id == job_id, Bid.id != bid_id, Bid.status == "PENDING")
        .values(status="DECLINED")
    )
    db.commit()
    return get_customer_job(db, customer_id, job_id)


def list_customer_favorites(db: Session, customer_id: uuid.UUID) -> list[ProviderProfile]:
    return list(
        db.scalars(
            select(ProviderProfile)
            .join(ProviderProfile.user)
            .join(
                Favorite,
                Favorite.provider_id == ProviderProfile.user_id,
            )
            .options(
                joinedload(ProviderProfile.primary_category),
                joinedload(ProviderProfile.user),
            )
            .where(
                Favorite.customer_id == customer_id,
                User.role == "provider",
                User.is_active.is_(True),
            )
            .order_by(Favorite.created_at.desc(), Favorite.provider_id)
        ).unique()
    )


def add_customer_favorite(
    db: Session, customer_id: uuid.UUID, provider_id: uuid.UUID
) -> None:
    provider = db.scalar(
        select(User).where(
            User.id == provider_id, User.role == "provider", User.is_active.is_(True)
        )
    )
    if not provider or not db.get(ProviderProfile, provider_id):
        raise _error(404, "PROVIDER_NOT_FOUND", "Active provider was not found.")
    favorite = db.get(Favorite, (customer_id, provider_id))
    if not favorite:
        db.add(Favorite(customer_id=customer_id, provider_id=provider_id))
        db.commit()


def remove_customer_favorite(
    db: Session, customer_id: uuid.UUID, provider_id: uuid.UUID
) -> None:
    favorite = db.get(Favorite, (customer_id, provider_id))
    if favorite:
        db.delete(favorite)
        db.commit()


def serialize_job(job: Job) -> dict:
    actions = ["cancel", "edit"] if job.status == "AWAITING_BIDS" else []
    payload = {
        "id": str(job.id),
        "title": job.title,
        "description": job.description,
        "category": {"id": str(job.category.id), "name": job.category.name},
        "status": job.status,
        "urgency": job.urgency,
        "preferredDate": job.preferred_date.isoformat() if job.preferred_date else None,
        "preferredTime": job.preferred_time.isoformat() if job.preferred_time else None,
        "scheduledAt": None,
        "serviceLocation": job.service_location,
        "budgetKobo": job.budget_kobo,
        "budget": (
            str((Decimal(job.budget_kobo) / 100).quantize(Decimal("0.01")))
            if job.budget_kobo is not None
            else None
        ),
        "agreedPriceKobo": job.agreed_price_kobo,
        "agreedPrice": (
            str((Decimal(job.agreed_price_kobo) / 100).quantize(Decimal("0.01")))
            if job.agreed_price_kobo is not None
            else None
        ),
        "bidCount": len(job.bids),
        "availableActions": actions,
        "createdAt": job.created_at.isoformat(),
        "updatedAt": job.updated_at.isoformat(),
    }
    if job.accepted_provider_id:
        payload["provider"] = {"id": str(job.accepted_provider_id)}
    return {key: value for key, value in payload.items() if value is not None}


def serialize_bid(bid: Bid) -> dict:
    profile = bid.provider.provider_profile
    return {
        "id": str(bid.id),
        "amountKobo": bid.amount_kobo,
        "amount": str((Decimal(bid.amount_kobo) / 100).quantize(Decimal("0.01"))),
        "message": bid.message,
        "estimatedDays": bid.estimated_days,
        "status": bid.status,
        "createdAt": bid.created_at.isoformat(),
        "provider": {
            "id": str(bid.provider_id),
            "name": profile.display_name if profile else "Provider",
            **(
                {"profession": profile.headline, "avatarUrl": profile.avatar_url}
                if profile
                else {}
            ),
        },
    }


def serialize_favorite(profile: ProviderProfile) -> dict:
    payload = {
        "id": str(profile.user_id),
        "displayName": profile.display_name,
        "headline": profile.headline,
        "avatarUrl": profile.avatar_url,
        "serviceAreas": (
            [{"city": profile.service_area_city, "state": profile.service_area_state}]
            if profile.service_area_city or profile.service_area_state
            else []
        ),
    }
    if profile.primary_category and profile.primary_category.is_active:
        payload["category"] = {
            "id": str(profile.primary_category.id),
            "name": profile.primary_category.name,
        }
    return payload
