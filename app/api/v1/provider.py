import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.v1.auth import _require_csrf, require_role
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.provider import (
    AvailabilityUpdate,
    ProviderBidCreate,
    ProviderJobProgressUpdate,
    ProviderProfileUpdate,
    ProviderServiceCreate,
    ProviderServiceUpdate,
)
from app.services.provider import (
    create_provider_service,
    delete_provider_service,
    get_provider_availability,
    get_provider_earnings,
    get_provider_opportunity,
    get_provider_profile,
    list_provider_bids,
    list_provider_jobs,
    list_provider_opportunities,
    list_provider_services,
    submit_provider_bid,
    update_provider_availability,
    update_provider_job_progress,
    update_provider_profile,
    update_provider_service,
)

router = APIRouter(prefix="/provider", tags=["Provider"])
ProviderUser = Annotated[User, Depends(require_role("provider"))]


def _csrf(request: Request, db: Session, user: User) -> None:
    _require_csrf(request, db, user)


@router.get("/me")
def provider_profile(
    user: ProviderUser, db: Session = Depends(get_db_session)
):
    return {"data": get_provider_profile(db, user)}


@router.patch("/me")
def patch_provider_profile(
    payload: ProviderProfileUpdate,
    request: Request,
    user: ProviderUser,
    db: Session = Depends(get_db_session),
):
    _csrf(request, db, user)
    return {
        "data": update_provider_profile(
            db, user, payload.model_dump(exclude_unset=True)
        )
    }


@router.get("/me/services")
def provider_services(
    user: ProviderUser, db: Session = Depends(get_db_session)
):
    return {"data": list_provider_services(db, user.id)}


@router.post("/me/services", status_code=201)
def post_provider_service(
    payload: ProviderServiceCreate,
    request: Request,
    user: ProviderUser,
    db: Session = Depends(get_db_session),
):
    _csrf(request, db, user)
    return {
        "data": create_provider_service(
            db, user.id, payload.model_dump()
        )
    }


@router.patch("/me/services/{listing_id}")
def patch_provider_service(
    listing_id: uuid.UUID,
    payload: ProviderServiceUpdate,
    request: Request,
    user: ProviderUser,
    db: Session = Depends(get_db_session),
):
    _csrf(request, db, user)
    return {
        "data": update_provider_service(
            db, user.id, listing_id, payload.model_dump(exclude_unset=True)
        )
    }


@router.delete("/me/services/{listing_id}")
def delete_provider_service_route(
    listing_id: uuid.UUID,
    request: Request,
    user: ProviderUser,
    db: Session = Depends(get_db_session),
):
    _csrf(request, db, user)
    delete_provider_service(db, user.id, listing_id)
    return {"data": {"id": str(listing_id), "removed": True}}


@router.get("/me/availability")
def provider_availability(
    user: ProviderUser, db: Session = Depends(get_db_session)
):
    return {"data": get_provider_availability(db, user.id)}


@router.put("/me/availability")
def put_provider_availability(
    payload: AvailabilityUpdate,
    request: Request,
    user: ProviderUser,
    db: Session = Depends(get_db_session),
):
    _csrf(request, db, user)
    return {
        "data": update_provider_availability(
            db, user.id, payload.model_dump()
        )
    }


@router.get("/jobs")
def provider_opportunities(
    user: ProviderUser,
    search: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, max_length=120),
    location: str | None = Query(default=None, max_length=120),
    minBudget: Decimal | None = Query(default=None, ge=0),
    maxBudget: Decimal | None = Query(default=None, ge=0),
    sort: str = Query(default="newest", pattern="^(newest|budget-low|budget-high)$"),
    limit: int = Query(default=20, ge=1, le=50),
    cursor: str | None = Query(default=None, max_length=512),
    db: Session = Depends(get_db_session),
):
    if minBudget is not None and maxBudget is not None and minBudget > maxBudget:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "BUDGET_RANGE_INVALID",
                "message": "Minimum budget cannot exceed maximum budget.",
            },
        )
    items, next_cursor = list_provider_opportunities(
        db,
        user.id,
        limit=limit,
        cursor=cursor,
        search=search,
        category=category,
        location=location,
        min_budget=minBudget,
        max_budget=maxBudget,
        sort=sort,
    )
    return {"data": {"items": items, "nextCursor": next_cursor}}


@router.get("/jobs/{job_id}")
def provider_opportunity(
    job_id: uuid.UUID,
    user: ProviderUser,
    db: Session = Depends(get_db_session),
):
    return {"data": get_provider_opportunity(db, user.id, job_id)}


@router.get("/me/bids")
def provider_bids(
    user: ProviderUser,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db_session),
):
    return {"data": {"items": list_provider_bids(db, user.id, limit=limit)}}


@router.post("/jobs/{job_id}/bids", status_code=201)
def post_provider_bid(
    job_id: uuid.UUID,
    payload: ProviderBidCreate,
    request: Request,
    user: ProviderUser,
    db: Session = Depends(get_db_session),
):
    _csrf(request, db, user)
    bid = submit_provider_bid(db, user.id, job_id, payload.model_dump())
    return {"data": {"bid": bid}}


@router.get("/me/jobs")
def provider_jobs(
    user: ProviderUser,
    status: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db_session),
):
    return {
        "data": {
            "items": list_provider_jobs(
                db, user.id, status=status, limit=limit
            )
        }
    }


@router.patch("/me/jobs/{job_id}/progress")
def patch_provider_job_progress(
    job_id: uuid.UUID,
    payload: ProviderJobProgressUpdate,
    request: Request,
    user: ProviderUser,
    db: Session = Depends(get_db_session),
):
    _csrf(request, db, user)
    job = update_provider_job_progress(
        db,
        user.id,
        job_id,
        payload.transition,
        payload.expectedUpdatedAt,
    )
    return {"data": {"job": job}}


@router.get("/me/earnings")
def provider_earnings(
    user: ProviderUser,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db_session),
):
    return {"data": get_provider_earnings(db, user.id, limit=limit)}
