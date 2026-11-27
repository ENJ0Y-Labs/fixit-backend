import base64
import binascii
import json
import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.profile import ProviderProfile
from app.models.service import ProviderService, Service
from app.models.service_category import ServiceCategory
from app.models.user import User


def encode_provider_cursor(display_name: str, user_id: uuid.UUID) -> str:
    payload = json.dumps(
        {"name": display_name, "id": str(user_id)}, separators=(",", ":")
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def decode_provider_cursor(cursor: str) -> tuple[str, uuid.UUID]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        name = payload["name"]
        user_id = uuid.UUID(payload["id"])
        if not isinstance(name, str):
            raise ValueError
        return name, user_id
    except (
        ValueError,
        TypeError,
        KeyError,
        binascii.Error,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ValueError("The pagination cursor is invalid.") from exc


def encode_service_cursor(name: str, service_id: uuid.UUID) -> str:
    payload = json.dumps(
        {"name": name, "id": str(service_id)}, separators=(",", ":")
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def decode_service_cursor(cursor: str) -> tuple[str, uuid.UUID]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        name = payload["name"]
        service_id = uuid.UUID(payload["id"])
        if not isinstance(name, str):
            raise ValueError
        return name, service_id
    except (
        ValueError,
        TypeError,
        KeyError,
        binascii.Error,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ValueError("The pagination cursor is invalid.") from exc


def list_public_categories(
    db: Session, *, search: str | None, parent_id: uuid.UUID | None, limit: int
) -> list[ServiceCategory]:
    statement = select(ServiceCategory).where(ServiceCategory.is_active.is_(True))
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                ServiceCategory.name.ilike(term),
                ServiceCategory.description.ilike(term),
            )
        )
    if parent_id:
        statement = statement.where(ServiceCategory.parent_id == parent_id)
    return list(
        db.scalars(
            statement.order_by(
                ServiceCategory.sort_order,
                ServiceCategory.name,
                ServiceCategory.id,
            ).limit(limit)
        )
    )


def list_public_services(
    db: Session,
    *,
    search: str | None,
    category_id: uuid.UUID | None,
    limit: int,
    cursor: str | None,
) -> tuple[list[Service], str | None]:
    statement = (
        select(Service)
        .join(Service.category)
        .options(joinedload(Service.category))
        .where(
            Service.is_active.is_(True),
            ServiceCategory.is_active.is_(True),
        )
    )
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(Service.name.ilike(term), Service.description.ilike(term))
        )
    if category_id:
        statement = statement.where(Service.category_id == category_id)
    if cursor:
        last_name, last_id = decode_service_cursor(cursor)
        statement = statement.where(
            or_(
                Service.name > last_name,
                and_(Service.name == last_name, Service.id > last_id),
            )
        )

    services = list(
        db.scalars(
            statement.order_by(Service.name, Service.id).limit(limit + 1)
        ).unique()
    )
    has_more = len(services) > limit
    page = services[:limit]
    next_cursor = (
        encode_service_cursor(page[-1].name, page[-1].id)
        if has_more and page
        else None
    )
    return page, next_cursor


def list_public_providers(
    db: Session,
    *,
    search: str | None,
    category: str | None,
    service_id: uuid.UUID | None,
    city: str | None,
    state: str | None,
    limit: int,
    cursor: str | None,
) -> tuple[list[ProviderProfile], str | None]:
    statement = (
        select(ProviderProfile)
        .join(ProviderProfile.user)
        .outerjoin(ProviderProfile.primary_category)
        .options(
            joinedload(ProviderProfile.user),
            joinedload(ProviderProfile.primary_category),
            selectinload(ProviderProfile.services)
            .joinedload(ProviderService.service)
            .joinedload(Service.category),
        )
        .where(User.role == "provider", User.is_active.is_(True))
    )

    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                ProviderProfile.display_name.ilike(term),
                ProviderProfile.headline.ilike(term),
                ProviderProfile.bio.ilike(term),
            )
        )
    if category:
        try:
            category_id = uuid.UUID(category)
        except ValueError:
            statement = statement.where(
                and_(
                    ServiceCategory.is_active.is_(True),
                    ServiceCategory.slug == category.strip().lower(),
                )
            )
        else:
            statement = statement.where(
                and_(
                    ServiceCategory.is_active.is_(True),
                    ServiceCategory.id == category_id,
                )
            )
    if service_id:
        statement = (
            statement.join(ProviderProfile.services)
            .join(ProviderService.service)
            .where(
                ProviderService.is_active.is_(True),
                Service.is_active.is_(True),
                Service.category.has(ServiceCategory.is_active.is_(True)),
                Service.id == service_id,
            )
        )
    if city:
        statement = statement.where(
            ProviderProfile.service_area_city.ilike(city.strip())
        )
    if state:
        statement = statement.where(
            ProviderProfile.service_area_state.ilike(state.strip())
        )
    if cursor:
        last_name, last_id = decode_provider_cursor(cursor)
        statement = statement.where(
            or_(
                ProviderProfile.display_name > last_name,
                and_(
                    ProviderProfile.display_name == last_name,
                    ProviderProfile.user_id > last_id,
                ),
            )
        )

    profiles = list(
        db.scalars(
            statement.order_by(
                ProviderProfile.display_name, ProviderProfile.user_id
            ).limit(limit + 1)
        ).unique()
    )
    has_more = len(profiles) > limit
    page = profiles[:limit]
    next_cursor = (
        encode_provider_cursor(page[-1].display_name, page[-1].user_id)
        if has_more and page
        else None
    )
    return page, next_cursor


def get_public_provider(db: Session, provider_id: uuid.UUID) -> ProviderProfile | None:
    statement = (
        select(ProviderProfile)
        .join(ProviderProfile.user)
        .options(
            joinedload(ProviderProfile.user),
            joinedload(ProviderProfile.primary_category),
            selectinload(ProviderProfile.services)
            .joinedload(ProviderService.service)
            .joinedload(Service.category),
        )
        .where(
            ProviderProfile.user_id == provider_id,
            User.role == "provider",
            User.is_active.is_(True),
        )
    )
    return db.scalar(statement)


def serialize_category(category: ServiceCategory) -> dict:
    return {
        "id": str(category.id),
        "slug": category.slug,
        "name": category.name,
        "description": category.description,
        "parentId": str(category.parent_id) if category.parent_id else None,
        "sortOrder": category.sort_order,
    }


def serialize_service(service: Service) -> dict:
    return {
        "id": str(service.id),
        "slug": service.slug,
        "name": service.name,
        "description": service.description,
        "sortOrder": service.sort_order,
        "category": serialize_category(service.category),
    }


def serialize_provider(profile: ProviderProfile) -> dict:
    payload = {
        "id": str(profile.user_id),
        "displayName": profile.display_name,
    }
    optional_fields = {
        "headline": profile.headline,
        "bio": profile.bio,
        "avatarUrl": profile.avatar_url,
    }
    payload.update(
        {key: value for key, value in optional_fields.items() if value is not None}
    )

    category = profile.primary_category
    if category and category.is_active:
        payload["category"] = {
            "id": str(category.id),
            "name": category.name,
        }

    listings = [
        listing
        for listing in profile.services
        if listing.is_active
        and listing.service.is_active
        and listing.service.category.is_active
    ]
    if listings:
        payload["services"] = [
            {
                "id": str(listing.service.id),
                "name": listing.service.name,
                "description": listing.description,
                "pricing": listing.pricing_mode,
                **(
                    {
                        "price": {
                            "amount": listing.price_kobo // 100,
                            "currency": "NGN",
                        }
                    }
                    if listing.price_kobo is not None
                    else {}
                ),
            }
            for listing in listings
        ]

    if profile.service_area_city:
        payload["serviceAreas"] = [{"city": profile.service_area_city}]
    if profile.hourly_rate_kobo is not None:
        payload["hourlyRate"] = {
            "amount": round(profile.hourly_rate_kobo / 100, 2),
            "currency": "NGN",
            "unit": "hour",
        }
    return payload
