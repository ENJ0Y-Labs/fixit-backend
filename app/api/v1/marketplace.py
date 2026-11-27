import uuid
from typing import Annotated

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
    q: Annotated[str | None, Query(max_length=120)] = None,
    parent_id: Annotated[uuid.UUID | None, Query(alias="parentId")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    db: Session = Depends(get_db_session),
) -> dict:
    categories = list_public_categories(db, search=q, parent_id=parent_id, limit=limit)
    return {
        "data": {
            "items": [serialize_category(category) for category in categories],
            "nextCursor": None,
        }
    }


@router.get("/providers", response_model=PublicProviderListEnvelope)
def get_providers(
    q: Annotated[str | None, Query(max_length=120)] = None,
    category: Annotated[str | None, Query(max_length=120)] = None,
    city: Annotated[str | None, Query(max_length=100)] = None,
    state: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
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


@router.get("/providers/{provider_id}", response_model=PublicProviderDetailEnvelope)
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
