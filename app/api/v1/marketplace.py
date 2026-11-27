import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.marketplace import (
    PublicCategoryEnvelope,
    PublicProviderDetailEnvelope,
    PublicProviderListEnvelope,
)
from app.services.marketplace import (
    get_public_provider,
    list_public_categories,
    list_public_providers,
    serialize_category,
    serialize_provider,
)

router = APIRouter(prefix="/public", tags=["Public marketplace"])


@router.get("/categories", response_model=PublicCategoryEnvelope)
def get_categories(
    q: str | None = Query(default=None, max_length=120),
    parent_id: uuid.UUID | None = Query(default=None, alias="parentId"),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db_session),
) -> dict:
    categories = list_public_categories(
        db, search=q, parent_id=parent_id, limit=limit
    )
    return {
        "data": {
            "items": [serialize_category(category) for category in categories],
            "nextCursor": None,
        }
    }


@router.get("/providers", response_model=PublicProviderListEnvelope)
def get_providers(
    q: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, max_length=120),
    city: str | None = Query(default=None, max_length=100),
    state: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=20, ge=1, le=50),
    cursor: str | None = Query(default=None, max_length=512),
    db: Session = Depends(get_db_session),
) -> dict:
    try:
        profiles, next_cursor = list_public_providers(
            db,
            search=q,
            category=category,
            city=city,
            state=state,
            limit=limit,
            cursor=cursor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "data": {
            "items": [serialize_provider(profile) for profile in profiles],
            "nextCursor": next_cursor,
        }
    }


@router.get(
    "/providers/{provider_id}", response_model=PublicProviderDetailEnvelope
)
def get_provider(
    provider_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> dict:
    profile = get_public_provider(db, provider_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "PROVIDER_NOT_FOUND",
                "message": "This provider profile is not publicly available.",
            },
        )
    return {"data": serialize_provider(profile)}
