import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.security import digest_secret, expiry, hash_password, new_secret, utcnow, verify_password
from app.db.session import get_db_session
from app.models.auth import AuthSession, AuthToken
from app.models.profile import CustomerProfile, ProviderProfile
from app.models.user import User
from app.schemas.auth import EmailRequest, LoginRequest, RegisterRequest, ResetPasswordRequest, VerificationConfirmRequest
from app.services.email import send_auth_email

router = APIRouter(prefix="/auth", tags=["Authentication"])

def _user_payload(user: User) -> dict:
    profile = user.customer_profile if user.role == "customer" else user.provider_profile if user.role == "provider" else user.admin_profile
    return {"id": str(user.id), "name": profile.display_name if profile else "", "email": user.email, "phone": user.phone, "role": user.role, "emailVerified": user.email_verified_at is not None, "isActive": user.is_active, "capabilities": [user.role]}

def _issue_session(db: Session, user: User, response: Response) -> dict:
    settings = get_settings()
    raw, csrf = new_secret(), new_secret()
    db.add(AuthSession(user_id=user.id, token_hash=digest_secret(raw), csrf_hash=digest_secret(csrf), expires_at=expiry(settings.session_ttl_hours * 60)))
    db.commit()
    response.set_cookie(settings.session_cookie_name, raw, httponly=True, secure=settings.cookie_secure, samesite="lax", max_age=settings.session_ttl_hours * 3600, path="/")
    response.set_cookie(settings.csrf_cookie_name, csrf, httponly=False, secure=settings.cookie_secure, samesite="lax", max_age=settings.session_ttl_hours * 3600, path="/")
    return {"user": _user_payload(user), "csrfToken": csrf}

def current_user(request: Request, db: Session = Depends(get_db_session)) -> User:
    raw = request.cookies.get(get_settings().session_cookie_name)
    if not raw:
        raise HTTPException(status_code=401, detail={"code":"UNAUTHENTICATED","message":"Authentication required."})
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == digest_secret(raw), AuthSession.revoked_at.is_(None), AuthSession.expires_at > utcnow()))
    user = db.get(User, session.user_id) if session else None
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail={"code":"SESSION_EXPIRED","message":"Session is invalid or expired."})
    return user

def require_role(*roles: str):
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail={"code":"FORBIDDEN","message":"You do not have permission to perform this action."})
        return user
    return dependency

def _require_csrf(request: Request, db: Session, user: User) -> None:
    origin = request.headers.get("origin")
    if origin is None:
        return
    settings = get_settings()
    if origin not in settings.cors_origins:
        raise HTTPException(status_code=403, detail={"code":"ORIGIN_INVALID","message":"Request origin is not allowed."})
    cookie, header = request.cookies.get(settings.csrf_cookie_name), request.headers.get("x-csrf-token")
    if not cookie or not header or not secrets.compare_digest(cookie, header):
        raise HTTPException(status_code=403, detail={"code":"CSRF_INVALID","message":"CSRF validation failed."})
    raw = request.cookies.get(settings.session_cookie_name, "")
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == digest_secret(raw), AuthSession.revoked_at.is_(None)))
    if not session or not secrets.compare_digest(session.csrf_hash, digest_secret(header)):
        raise HTTPException(status_code=403, detail={"code":"CSRF_INVALID","message":"CSRF validation failed."})

@router.post("/register", status_code=201)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db_session)):
    email = str(payload.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail={"code":"ACCOUNT_EXISTS","message":"An account with this email already exists."})
    if payload.phone and db.scalar(select(User).where(User.phone == payload.phone)):
        raise HTTPException(status_code=409, detail={"code":"PHONE_EXISTS","message":"This phone number is already in use."})
    user = User(email=email, phone=payload.phone, password_hash=hash_password(payload.password), role=payload.role, is_active=True)
    db.add(user)
    db.flush()
    if payload.role == "customer":
        db.add(CustomerProfile(user_id=user.id, display_name=payload.name.strip()))
    else:
        db.add(ProviderProfile(user_id=user.id, display_name=payload.name.strip()))
    db.commit()
    db.refresh(user)
    token = new_secret()
    db.add(AuthToken(user_id=user.id, token_hash=digest_secret(token), purpose="email_verification", expires_at=expiry(30)))
    db.commit()
    send_auth_email(to=user.email, subject="Verify your FixIt email", text=f"Your FixIt email verification token (valid for 30 minutes): {token}")
    return {"data":{"user":_user_payload(user),"verificationRequired":True}}

@router.post("/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db_session)):
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if not user or not user.is_active or not verify_password(user.password_hash, payload.password):
        raise HTTPException(status_code=401, detail={"code":"INVALID_CREDENTIALS","message":"Email or password is incorrect."})
    return {"data":_issue_session(db, user, response)}

@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db_session), user: User = Depends(current_user)):
    _require_csrf(request, db, user)
    raw = request.cookies.get(get_settings().session_cookie_name, "")
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == digest_secret(raw), AuthSession.revoked_at.is_(None)))
    if session:
        session.revoked_at = utcnow()
        db.commit()
    settings = get_settings()
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
    return {"data":{"loggedOut":True}}

@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"data":_user_payload(user)}

@router.post("/password/forgot")
def forgot_password(payload: EmailRequest, db: Session = Depends(get_db_session)):
    user = db.scalar(select(User).where(User.email == str(payload.email).lower(), User.is_active.is_(True)))
    if user:
        token = new_secret()
        db.add(AuthToken(user_id=user.id, token_hash=digest_secret(token), purpose="password_reset", expires_at=expiry(30)))
        db.commit()
        send_auth_email(to=user.email, subject="Reset your FixIt password", text=f"Your FixIt password reset token (valid for 30 minutes): {token}")
    return {"data":{"message":"If the account exists, instructions will be sent shortly."}}

@router.post("/password/reset")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db_session)):
    record = db.scalar(select(AuthToken).where(AuthToken.token_hash == digest_secret(payload.token), AuthToken.purpose == "password_reset", AuthToken.consumed_at.is_(None), AuthToken.expires_at > utcnow()))
    if not record:
        raise HTTPException(status_code=400, detail={"code":"TOKEN_INVALID","message":"This reset token is invalid or expired."})
    record.consumed_at = utcnow()
    user = db.get(User, record.user_id)
    user.password_hash = hash_password(payload.password)
    for session in db.scalars(select(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))):
        session.revoked_at = utcnow()
    db.commit()
    return {"data":{"passwordReset":True}}

@router.post("/verification/request")
def request_verification(payload: EmailRequest, db: Session = Depends(get_db_session)):
    user = db.scalar(select(User).where(User.email == str(payload.email).lower(), User.is_active.is_(True)))
    if user and user.email_verified_at is None:
        recent = db.scalar(select(AuthToken).where(AuthToken.user_id == user.id, AuthToken.purpose == "email_verification", AuthToken.created_at > utcnow().replace(microsecond=0) - __import__("datetime").timedelta(minutes=2)))
        if not recent:
            token = new_secret()
            db.add(AuthToken(user_id=user.id, token_hash=digest_secret(token), purpose="email_verification", expires_at=expiry(30)))
            db.commit()
            send_auth_email(to=user.email, subject="Verify your FixIt email", text=f"Your FixIt email verification token (valid for 30 minutes): {token}")
    return {"data":{"message":"If verification is available, instructions will be sent shortly."}}

@router.post("/verification/confirm")
def confirm_verification(payload: VerificationConfirmRequest, db: Session = Depends(get_db_session)):
    record = db.scalar(select(AuthToken).where(AuthToken.token_hash == digest_secret(payload.token), AuthToken.purpose == "email_verification", AuthToken.consumed_at.is_(None), AuthToken.expires_at > utcnow()))
    if not record:
        raise HTTPException(status_code=400, detail={"code":"TOKEN_INVALID","message":"This verification token is invalid or expired."})
    record.consumed_at = utcnow()
    user = db.get(User, record.user_id)
    user.email_verified_at = utcnow()
    db.commit()
    return {"data":{"verified":True}}
