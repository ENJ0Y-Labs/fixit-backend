import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.v1.auth import _require_csrf, require_role
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.customer import CustomerProfileUpdate, JobCreate, JobUpdate
from app.services.customer import (
    accept_customer_bid,
    add_customer_favorite,
    cancel_customer_job,
    create_customer_job,
    get_customer_job,
    get_customer_profile,
    list_customer_bids,
    list_customer_favorites,
    list_customer_jobs,
    remove_customer_favorite,
    serialize_bid,
    serialize_favorite,
    serialize_job,
    update_customer_job,
    update_customer_profile,
)

router = APIRouter(prefix="/customer/me", tags=["Customer"])


def _csrf(request: Request, db: Session, user: User) -> None:
    _require_csrf(request, db, user)


@router.get("")
def customer_profile(
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db_session),
):
    return {"data": get_customer_profile(db, user)}


@router.patch("")
def patch_customer_profile(
    payload: CustomerProfileUpdate,
    request: Request,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db_session),
):
    _csrf(request, db, user)
    return {"data": update_customer_profile(db, user, payload.model_dump(exclude_unset=True))}


@router.get("/jobs")
def customer_jobs(
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db_session),
):
    jobs, next_cursor = list_customer_jobs(db, user.id, limit=limit, cursor=cursor)
    return {
        "data": {
            "items": [serialize_job(job) for job in jobs],
            "nextCursor": next_cursor,
        }
    }


@router.post("/jobs", status_code=201)
def post_customer_job(
    payload: JobCreate,
    request: Request,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db_session),
):
    _csrf(request, db, user)
    job = create_customer_job(db, user.id, payload.model_dump())
    return {"data": serialize_job(job)}


@router.get("/jobs/{job_id}")
def customer_job(
    job_id: uuid.UUID,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db_session),
):
    return {"data": serialize_job(get_customer_job(db, user.id, job_id))}


@router.patch("/jobs/{job_id}")
def patch_customer_job(
    job_id: uuid.UUID,
    payload: JobUpdate,
    request: Request,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db_session),
):
    _csrf(request, db, user)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return {"data": serialize_job(get_customer_job(db, user.id, job_id))}
    return {"data": serialize_job(update_customer_job(db, user.id, job_id, changes))}


@router.post("/jobs/{job_id}/cancel")
def post_cancel_customer_job(
    job_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db_session),
):
    _csrf(request, db, user)
    return {"data": serialize_job(cancel_customer_job(db, user.id, job_id))}


@router.get("/jobs/{job_id}/bids")
def customer_job_bids(
    job_id: uuid.UUID,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db_session),
):
    bids = list_customer_bids(db, user.id, job_id)
    return {"data": {"items": [serialize_bid(bid) for bid in bids]}}


@router.post("/jobs/{job_id}/bids/{bid_id}/accept")
def post_accept_customer_bid(
    job_id: uuid.UUID,
    bid_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db_session),
):
    _csrf(request, db, user)
    job = accept_customer_bid(db, user.id, job_id, bid_id)
    return {"data": serialize_job(job)}


@router.get("/favorites")
def customer_favorites(
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db_session),
):
    profiles = list_customer_favorites(db, user.id)
    return {"data": {"items": [serialize_favorite(profile) for profile in profiles]}}


@router.put("/favorites/{provider_id}", status_code=200)
def put_customer_favorite(
    provider_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db_session),
):
    _csrf(request, db, user)
    add_customer_favorite(db, user.id, provider_id)
    return {"data": {"providerId": str(provider_id), "favorited": True}}


@router.delete("/favorites/{provider_id}")
def delete_customer_favorite(
    provider_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db_session),
):
    _csrf(request, db, user)
    remove_customer_favorite(db, user.id, provider_id)
    return {"data": {"providerId": str(provider_id), "favorited": False}}
