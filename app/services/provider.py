import base64
import binascii
import json
import uuid
from datetime import UTC, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.customer import Bid, Job
from app.models.profile import CustomerProfile, ProviderProfile
from app.models.provider import ProviderAvailability, ProviderAvailabilityDay
from app.models.service import ProviderService, Service
from app.models.service_category import ServiceCategory
from app.models.user import User


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status, detail={"code": code, "message": message}
    )


def _money(kobo: int | None) -> str | None:
    if kobo is None:
        return None
    return str((Decimal(kobo) / 100).quantize(Decimal("0.01")))


def _profile(db: Session, user: User) -> ProviderProfile:
    profile = db.get(ProviderProfile, user.id)
    if not profile:
        raise _error(404, "PROFILE_NOT_FOUND", "Provider profile was not found.")
    return profile


def _service_listing_payload(listing: ProviderService) -> dict:
    service = listing.service
    return {
        "id": str(listing.id),
        "serviceId": str(service.id),
        "name": service.name,
        "category": {"id": str(service.category.id), "name": service.category.name},
        "description": listing.description,
        "pricingMode": listing.pricing_mode,
        "priceKobo": listing.price_kobo,
        "price": _money(listing.price_kobo),
        "isActive": listing.is_active,
        "createdAt": listing.created_at.isoformat(),
        "updatedAt": listing.updated_at.isoformat(),
    }


def get_provider_profile(db: Session, user: User) -> dict:
    profile = _profile(db, user)
    listings = list(
        db.scalars(
            select(ProviderService)
            .options(joinedload(ProviderService.service).joinedload(Service.category))
            .where(
                ProviderService.provider_id == user.id,
                ProviderService.is_active.is_(True),
            )
            .order_by(ProviderService.created_at, ProviderService.id)
        ).unique()
    )
    return {
        "id": str(user.id),
        "displayName": profile.display_name,
        "email": user.email,
        "phone": user.phone,
        "headline": profile.headline,
        "bio": profile.bio,
        "avatarUrl": profile.avatar_url,
        "serviceAreaCity": profile.service_area_city,
        "serviceAreaState": profile.service_area_state,
        "services": [_service_listing_payload(item) for item in listings],
        "updatedAt": profile.updated_at.isoformat(),
    }


def update_provider_profile(db: Session, user: User, changes: dict) -> dict:
    profile = _profile(db, user)
    mapping = {
        "displayName": "display_name",
        "headline": "headline",
        "bio": "bio",
        "serviceAreaCity": "service_area_city",
        "serviceAreaState": "service_area_state",
    }
    for key, field in mapping.items():
        if key in changes:
            value = changes[key]
            if key == "displayName" and not value:
                raise _error(422, "DISPLAY_NAME_REQUIRED", "Display name cannot be blank.")
            setattr(profile, field, value if key == "displayName" else value or None)
    if "phone" in changes:
        phone = changes["phone"] or None
        duplicate = db.scalar(
            select(User).where(User.phone == phone, User.id != user.id)
        ) if phone else None
        if duplicate:
            raise _error(409, "PHONE_EXISTS", "This phone number is already in use.")
        user.phone = phone
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _error(409, "PROFILE_CONFLICT", "The profile could not be updated.") from exc
    db.refresh(profile)
    return get_provider_profile(db, user)


def list_provider_services(db: Session, user_id: uuid.UUID) -> dict:
    catalogue = list(
        db.scalars(
            select(Service)
            .options(joinedload(Service.category))
            .join(Service.category)
            .where(
                Service.is_active.is_(True),
                Service.category.has(ServiceCategory.is_active.is_(True)),
            )
            .order_by(Service.sort_order, Service.name, Service.id)
        ).unique()
    )
    listings = list(
        db.scalars(
            select(ProviderService)
            .options(joinedload(ProviderService.service).joinedload(Service.category))
            .where(ProviderService.provider_id == user_id)
            .order_by(ProviderService.created_at, ProviderService.id)
        ).unique()
    )
    return {
        "catalogue": [
            {
                "id": str(item.id),
                "name": item.name,
                "description": item.description,
                "category": {
                    "id": str(item.category_id),
                    "name": item.category.name,
                },
            }
            for item in catalogue
        ],
        "items": [_service_listing_payload(item) for item in listings],
    }


def create_provider_service(db: Session, user_id: uuid.UUID, payload: dict) -> dict:
    service = db.scalar(
        select(Service)
        .options(joinedload(Service.category))
        .where(
            Service.id == payload["serviceId"],
            Service.is_active.is_(True),
            Service.category.has(ServiceCategory.is_active.is_(True)),
        )
    )
    if not service:
        raise _error(422, "SERVICE_INVALID", "Choose an active catalogue service.")
    existing = db.scalar(
        select(ProviderService).where(
            ProviderService.provider_id == user_id,
            ProviderService.service_id == service.id,
        )
    )
    if existing:
        raise _error(409, "SERVICE_ALREADY_LISTED", "This service is already listed.")
    price = payload.get("price")
    listing = ProviderService(
        provider_id=user_id,
        service_id=service.id,
        description=payload["description"],
        pricing_mode=payload["pricingMode"],
        price_kobo=int(price * 100) if price is not None else None,
        is_active=True,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    listing.service = service
    return _service_listing_payload(listing)


def update_provider_service(
    db: Session, user_id: uuid.UUID, listing_id: uuid.UUID, changes: dict
) -> dict:
    listing = db.scalar(
        select(ProviderService)
        .options(joinedload(ProviderService.service).joinedload(Service.category))
        .where(ProviderService.id == listing_id, ProviderService.provider_id == user_id)
        .with_for_update()
    )
    if not listing:
        raise _error(404, "SERVICE_LISTING_NOT_FOUND", "Service listing was not found.")
    if "description" in changes:
        listing.description = changes["description"]
    if "pricingMode" in changes:
        listing.pricing_mode = changes["pricingMode"]
    if "price" in changes:
        price = changes["price"]
        listing.price_kobo = int(price * 100) if price is not None else None
    if listing.pricing_mode == "quote":
        listing.price_kobo = None
    elif listing.price_kobo is None or listing.price_kobo <= 0:
        raise _error(422, "SERVICE_PRICE_REQUIRED", "A positive price is required.")
    db.commit()
    db.refresh(listing)
    return _service_listing_payload(listing)


def delete_provider_service(db: Session, user_id: uuid.UUID, listing_id: uuid.UUID) -> None:
    listing = db.scalar(
        select(ProviderService).where(
            ProviderService.id == listing_id, ProviderService.provider_id == user_id
        )
    )
    if not listing:
        raise _error(404, "SERVICE_LISTING_NOT_FOUND", "Service listing was not found.")
    db.delete(listing)
    db.commit()


def get_provider_availability(db: Session, user_id: uuid.UUID) -> dict:
    availability = db.get(ProviderAvailability, user_id)
    days = (
        list(
            db.scalars(
                select(ProviderAvailabilityDay)
                .where(ProviderAvailabilityDay.provider_id == user_id)
                .order_by(ProviderAvailabilityDay.weekday)
            )
        )
        if availability
        else []
    )
    by_day = {item.weekday: item for item in days}
    return {
        "isAvailable": availability.is_available if availability else True,
        "timezone": availability.timezone if availability else "Africa/Lagos",
        "schedule": [
            {
                "weekday": weekday,
                "day": ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")[weekday],
                "enabled": by_day[weekday].is_enabled if weekday in by_day else False,
                "start": by_day[weekday].start_time.strftime("%H:%M") if weekday in by_day and by_day[weekday].start_time else None,
                "end": by_day[weekday].end_time.strftime("%H:%M") if weekday in by_day and by_day[weekday].end_time else None,
            }
            for weekday in range(7)
        ],
        "updatedAt": availability.updated_at.isoformat() if availability else None,
    }


def update_provider_availability(db: Session, user_id: uuid.UUID, payload: dict) -> dict:
    availability = db.get(ProviderAvailability, user_id)
    if not availability:
        availability = ProviderAvailability(
            provider_id=user_id,
            is_available=payload["isAvailable"],
            timezone=payload["timezone"],
        )
        db.add(availability)
        db.flush()
    else:
        availability.is_available = payload["isAvailable"]
        availability.timezone = payload["timezone"]
    existing = {
        item.weekday: item
        for item in db.scalars(
            select(ProviderAvailabilityDay).where(
                ProviderAvailabilityDay.provider_id == user_id
            )
        )
    }
    incoming_weekdays = {day["weekday"] for day in payload["schedule"]}
    for weekday, item in existing.items():
        if weekday not in incoming_weekdays:
            db.delete(item)
    for day in payload["schedule"]:
        item = existing.get(day["weekday"])
        if item is None:
            item = ProviderAvailabilityDay(
                provider_id=user_id, weekday=day["weekday"]
            )
            db.add(item)
        item.is_enabled = day["enabled"]
        item.start_time = day["start"] if day["enabled"] else None
        item.end_time = day["end"] if day["enabled"] else None
    db.commit()
    db.refresh(availability)
    return get_provider_availability(db, user_id)


def _encode_cursor(value: dict) -> str:
    return base64.urlsafe_b64encode(
        json.dumps(value, separators=(",", ":")).encode()
    ).decode().rstrip("=")


def _decode_cursor(cursor: str) -> dict:
    try:
        value = json.loads(
            base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        )
        if (
            not isinstance(value, dict)
            or value.get("sort") not in {"newest", "budget-low", "budget-high"}
            or not isinstance(value.get("id"), str)
        ):
            raise ValueError
        uuid.UUID(value["id"])
        if value["sort"] == "newest":
            datetime.fromisoformat(value["createdAt"])
        else:
            int(value["budget"])
        return value
    except (ValueError, TypeError, binascii.Error, UnicodeDecodeError) as exc:
        raise _error(422, "CURSOR_INVALID", "The pagination cursor is invalid.") from exc


def _job_location(customer: CustomerProfile | None) -> str:
    if not customer:
        return "Location shared after acceptance"
    values = [value for value in (customer.default_city, customer.default_state) if value]
    return ", ".join(values) if values else "Location shared after acceptance"


def _job_payload(job: Job, customer: CustomerProfile | None = None) -> dict:
    status_category = {
        "IN_PROGRESS": "in-progress",
        "COMPLETED": "completed",
        "CANCELLED": "cancelled",
    }.get(job.status, "upcoming")
    return {
        "id": str(job.id),
        "title": job.title,
        "description": job.description,
        "category": job.category.name,
        "categoryId": str(job.category_id),
        "location": _job_location(customer),
        "budget": _money(job.budget_kobo),
        "budgetKobo": job.budget_kobo,
        "agreedAmount": _money(job.agreed_price_kobo),
        "urgency": job.urgency,
        "preferredDate": job.preferred_date.isoformat() if job.preferred_date else None,
        "preferredTime": job.preferred_time.isoformat() if job.preferred_time else None,
        "postedAt": job.created_at.isoformat(),
        "updatedAt": job.updated_at.isoformat(),
        "status": job.status,
        "statusCategory": status_category,
        "responseCount": len(job.bids),
        "customerReference": str(job.id)[:8].upper(),
        "allowedTransitions": ["COMPLETE"] if job.status == "IN_PROGRESS" else [],
        "expectedUpdatedAt": job.updated_at.isoformat(),
    }


def _provider_category_ids(db: Session, provider_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        db.scalars(
            select(Service.category_id)
            .join(ProviderService, ProviderService.service_id == Service.id)
            .where(
                ProviderService.provider_id == provider_id,
                ProviderService.is_active.is_(True),
                Service.is_active.is_(True),
                Service.category.has(ServiceCategory.is_active.is_(True)),
            )
            .distinct()
        )
    )


def list_provider_opportunities(
    db: Session,
    provider_id: uuid.UUID,
    *,
    limit: int,
    cursor: str | None,
    search: str | None,
    category: str | None,
    location: str | None,
    min_budget: Decimal | None,
    max_budget: Decimal | None,
    sort: str,
) -> tuple[list[dict], str | None]:
    availability = db.get(ProviderAvailability, provider_id)
    if availability and not availability.is_available:
        return [], None
    category_ids = _provider_category_ids(db, provider_id)
    if not category_ids:
        return [], None

    statement = (
        select(Job, CustomerProfile)
        .join(ServiceCategory, Job.category_id == ServiceCategory.id)
        .outerjoin(CustomerProfile, CustomerProfile.user_id == Job.customer_id)
        .options(joinedload(Job.category), selectinload(Job.bids))
        .where(
            Job.status == "AWAITING_BIDS",
            Job.category_id.in_(category_ids),
            Job.customer_id != provider_id,
        )
    )
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Job.title.ilike(pattern),
                Job.description.ilike(pattern),
                ServiceCategory.name.ilike(pattern),
            )
        )
    if category:
        try:
            category_id = uuid.UUID(category)
            statement = statement.where(Job.category_id == category_id)
        except ValueError:
            statement = statement.where(ServiceCategory.slug == category.lower())
    if location:
        pattern = f"%{location.strip()}%"
        statement = statement.where(
            or_(
                CustomerProfile.default_city.ilike(pattern),
                CustomerProfile.default_state.ilike(pattern),
            )
        )
    if min_budget is not None:
        statement = statement.where(Job.budget_kobo >= int(min_budget * 100))
    if max_budget is not None:
        statement = statement.where(Job.budget_kobo <= int(max_budget * 100))

    budget_key = func.coalesce(Job.budget_kobo, 9223372036854775807)
    if sort == "budget-low":
        ordering = (budget_key.asc(), Job.id.asc())
    elif sort == "budget-high":
        ordering = (budget_key.desc(), Job.id.desc())
    else:
        ordering = (Job.created_at.desc(), Job.id.desc())
        sort = "newest"

    if cursor:
        decoded = _decode_cursor(cursor)
        if decoded.get("sort") != sort:
            raise _error(422, "CURSOR_INVALID", "The cursor does not match this sort order.")
        cursor_id = uuid.UUID(decoded["id"])
        if sort == "newest":
            created_at = datetime.fromisoformat(decoded["createdAt"])
            statement = statement.where(
                or_(
                    Job.created_at < created_at,
                    and_(Job.created_at == created_at, Job.id < cursor_id),
                )
            )
        else:
            key = int(decoded["budget"])
            if sort == "budget-low":
                statement = statement.where(
                    or_(budget_key > key, and_(budget_key == key, Job.id > cursor_id))
                )
            else:
                statement = statement.where(
                    or_(budget_key < key, and_(budget_key == key, Job.id < cursor_id))
                )

    rows = list(db.execute(statement.order_by(*ordering).limit(limit + 1)).all())
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = None
    if has_more and page:
        last_job, _ = page[-1]
        if sort == "newest":
            next_cursor = _encode_cursor(
                {
                    "sort": sort,
                    "createdAt": last_job.created_at.astimezone(UTC).isoformat(),
                    "id": str(last_job.id),
                }
            )
        else:
            next_cursor = _encode_cursor(
                {
                    "sort": sort,
                    "budget": last_job.budget_kobo
                    if last_job.budget_kobo is not None
                    else 9223372036854775807,
                    "id": str(last_job.id),
                }
            )
    return [_job_payload(job, customer) for job, customer in page], next_cursor


def get_provider_opportunity(db: Session, provider_id: uuid.UUID, job_id: uuid.UUID) -> dict:
    availability = db.get(ProviderAvailability, provider_id)
    if availability and not availability.is_available:
        raise _error(404, "JOB_NOT_AVAILABLE", "This job is not available to this provider.")
    categories = _provider_category_ids(db, provider_id)
    row = db.execute(
        select(Job, CustomerProfile)
        .outerjoin(CustomerProfile, CustomerProfile.user_id == Job.customer_id)
        .options(joinedload(Job.category), selectinload(Job.bids))
        .where(
            Job.id == job_id,
            Job.status == "AWAITING_BIDS",
            Job.category_id.in_(categories),
        )
    ).first()
    if not row:
        raise _error(404, "JOB_NOT_AVAILABLE", "This job is not available to this provider.")
    return _job_payload(row[0], row[1])


def _bid_payload(bid: Bid) -> dict:
    return {
        "id": str(bid.id),
        "jobId": str(bid.job_id),
        "jobTitle": bid.job.title,
        "price": _money(bid.amount_kobo),
        "priceKobo": bid.amount_kobo,
        "message": bid.message,
        "proposedSchedule": bid.proposed_schedule_at.isoformat()
        if bid.proposed_schedule_at
        else None,
        "status": bid.status,
        "createdAt": bid.created_at.isoformat(),
    }


def list_provider_bids(
    db: Session, provider_id: uuid.UUID, *, limit: int
) -> list[dict]:
    bids = list(
        db.scalars(
            select(Bid)
            .options(joinedload(Bid.job))
            .where(Bid.provider_id == provider_id)
            .order_by(Bid.created_at.desc(), Bid.id.desc())
            .limit(limit)
        ).unique()
    )
    return [_bid_payload(item) for item in bids]


def submit_provider_bid(
    db: Session, provider_id: uuid.UUID, job_id: uuid.UUID, payload: dict
) -> dict:
    availability = db.get(ProviderAvailability, provider_id)
    if availability and not availability.is_available:
        raise _error(403, "PROVIDER_UNAVAILABLE", "Set yourself available before submitting a bid.")
    job = db.scalar(
        select(Job).where(Job.id == job_id).with_for_update()
    )
    if not job or job.status != "AWAITING_BIDS":
        raise _error(409, "JOB_NOT_ACCEPTING_BIDS", "This job is no longer accepting bids.")
    if job.category_id not in _provider_category_ids(db, provider_id):
        raise _error(403, "PROVIDER_NOT_ELIGIBLE", "Your active services do not match this job.")
    existing = db.scalar(
        select(Bid).where(Bid.job_id == job_id, Bid.provider_id == provider_id)
    )
    if existing:
        raise _error(409, "BID_ALREADY_SUBMITTED", "You have already submitted a bid for this job.")
    proposed = payload.get("proposedSchedule")
    proposed_at = None
    if proposed:
        try:
            proposed_at = datetime.fromisoformat(proposed)
            if proposed_at.tzinfo is None:
                proposed_at = proposed_at.replace(tzinfo=ZoneInfo("Africa/Lagos"))
            proposed_at = proposed_at.astimezone(UTC)
        except (ValueError, TypeError) as exc:
            raise _error(422, "SCHEDULE_INVALID", "Use a valid proposed date and time.") from exc
    bid = Bid(
        job_id=job_id,
        provider_id=provider_id,
        amount_kobo=int(payload["price"] * 100),
        message=payload["message"],
        estimated_days=None,
        proposed_schedule_at=proposed_at,
        status="PENDING",
    )
    db.add(bid)
    db.commit()
    db.refresh(bid)
    bid.job = job
    return _bid_payload(bid)


def list_provider_jobs(
    db: Session, provider_id: uuid.UUID, *, status: str | None, limit: int
) -> list[dict]:
    statement = (
        select(Job, CustomerProfile)
        .outerjoin(CustomerProfile, CustomerProfile.user_id == Job.customer_id)
        .options(joinedload(Job.category), selectinload(Job.bids))
        .where(Job.accepted_provider_id == provider_id)
    )
    if status:
        if status in {"upcoming", "in-progress", "completed", "cancelled"}:
            mapping = {
                "upcoming": "IN_PROGRESS",
                "in-progress": "IN_PROGRESS",
                "completed": "COMPLETED",
                "cancelled": "CANCELLED",
            }
            statement = statement.where(Job.status == mapping[status])
        else:
            statement = statement.where(Job.status == status.upper())
    rows = list(
        db.execute(
            statement.order_by(Job.updated_at.desc(), Job.id.desc()).limit(limit)
        ).all()
    )
    return [_job_payload(job, customer) for job, customer in rows]


def update_provider_job_progress(
    db: Session,
    provider_id: uuid.UUID,
    job_id: uuid.UUID,
    transition: str,
    expected_updated_at: str | None,
) -> dict:
    row = db.execute(
        select(Job, CustomerProfile)
        .outerjoin(CustomerProfile, CustomerProfile.user_id == Job.customer_id)
        .options(joinedload(Job.category), selectinload(Job.bids))
        .where(Job.id == job_id, Job.accepted_provider_id == provider_id)
        .with_for_update()
    ).first()
    if not row:
        raise _error(404, "JOB_NOT_FOUND", "Accepted job was not found.")
    job, customer = row
    if expected_updated_at:
        try:
            expected = datetime.fromisoformat(expected_updated_at)
            if expected.tzinfo is None:
                raise ValueError
        except ValueError as exc:
            raise _error(422, "VERSION_INVALID", "The job update token is invalid.") from exc
        stored_updated_at = job.updated_at
        if stored_updated_at.tzinfo is None:
            stored_updated_at = stored_updated_at.replace(tzinfo=UTC)
        if stored_updated_at.astimezone(UTC) != expected.astimezone(UTC):
            raise _error(409, "JOB_CHANGED", "This job changed. Refresh before updating it.")
    if transition != "COMPLETE" or job.status != "IN_PROGRESS":
        raise _error(409, "TRANSITION_NOT_ALLOWED", "This job cannot be completed from its current status.")
    job.status = "COMPLETED"
    db.commit()
    db.refresh(job)
    return _job_payload(job, customer)


def get_provider_earnings(db: Session, provider_id: uuid.UUID, *, limit: int) -> dict:
    bids = list(
        db.scalars(
            select(Bid)
            .options(joinedload(Bid.job))
            .where(Bid.provider_id == provider_id, Bid.status == "PENDING")
            .order_by(Bid.created_at.desc(), Bid.id.desc())
            .limit(limit)
        ).unique()
    )
    jobs = list(
        db.scalars(
            select(Job)
            .where(
                Job.accepted_provider_id == provider_id,
                Job.agreed_price_kobo.is_not(None),
            )
            .order_by(Job.updated_at.desc(), Job.id.desc())
            .limit(limit)
        )
    )
    records = [
        {
            "id": str(bid.id),
            "reference": str(bid.id)[:8].upper(),
            "jobId": str(bid.job_id),
            "jobTitle": bid.job.title,
            "amount": _money(bid.amount_kobo),
            "amountKobo": bid.amount_kobo,
            "amountType": "estimated",
            "status": bid.status,
            "createdAt": bid.created_at.isoformat(),
        }
        for bid in bids
        if bid.job.status == "AWAITING_BIDS"
    ]
    records.extend(
        {
            "id": str(job.id),
            "reference": str(job.id)[:8].upper(),
            "jobId": str(job.id),
            "jobTitle": job.title,
            "amount": _money(job.agreed_price_kobo),
            "amountKobo": job.agreed_price_kobo,
            "amountType": "agreed",
            "status": job.status,
            "createdAt": job.updated_at.isoformat(),
        }
        for job in jobs
    )
    records.sort(key=lambda item: item["createdAt"], reverse=True)
    return {
        "items": records[:limit],
        "payoutStatus": "UNAVAILABLE",
        "paidRecordsAvailable": False,
    }
