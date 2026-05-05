"""Auth API routes: register, login, refresh, and current-user.

These endpoints back the JWT authentication system.  The shared-token
auth path in admin.py remains active until jwt_auth_enabled=True and
at least one admin user record exists.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth.actor import AdminActor, AdminRole
from app.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import AuditLog, User

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / response shapes
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None
    role: str = "viewer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class MeResponse(BaseModel):
    email: str
    role: str
    display_name: str | None
    is_active: bool


# ---------------------------------------------------------------------------
# Helper: extract Bearer token from Authorization header
# ---------------------------------------------------------------------------


def _extract_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )
    return authorization.removeprefix("Bearer ").strip()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/register", status_code=201)
def register(
    body: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Create a new admin user.

    The first registered user always gets ``system_admin`` role regardless
    of the requested role.  Subsequent registrations require an existing
    system_admin to be authenticated (enforced by checking the
    ``Authorization`` header when users already exist).
    """
    settings = get_settings()

    existing_count: int = db.query(User).count()
    is_bootstrap = existing_count == 0

    # In non-development environments, require a bootstrap secret for first-user creation
    if is_bootstrap and settings.app_env != "development":
        bootstrap_secret = request.headers.get("X-JTA-Bootstrap-Secret")
        if not settings.first_admin_secret:
            raise HTTPException(
                status_code=503,
                detail="Bootstrap not available: JTA_FIRST_ADMIN_SECRET is not configured.",
            )
        if bootstrap_secret != settings.first_admin_secret:
            raise HTTPException(
                status_code=403,
                detail="Invalid bootstrap secret.",
            )

    # After bootstrap, require jwt-authenticated system_admin
    if not is_bootstrap:
        auth_header = request.headers.get("Authorization")
        token = _extract_bearer(auth_header)
        try:
            payload = decode_token(token)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc))
        if payload.token_type != "access":
            raise HTTPException(status_code=401, detail="Access token required")
        if payload.role != "system_admin":
            raise HTTPException(
                status_code=403, detail="Only system_admin may register new users"
            )

    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    _validate_password_strength(body.password)

    assigned_role: AdminRole = "system_admin" if is_bootstrap else body.role  # type: ignore[assignment]

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        role=assigned_role,
        display_name=body.display_name,
        is_active=True,
    )
    db.add(user)
    db.flush()

    db.add(
        AuditLog(
            action="user.register",
            entity_type="user",
            entity_id=str(user.id),
            actor_id=body.email,
            actor_type="user",
            actor_role=assigned_role,
            actor_ip=_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )
    )
    db.commit()

    return {"id": user.id, "email": user.email, "role": user.role}


@router.post("/login")
def login(
    body: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Exchange email + password for JWT access and refresh tokens."""
    user: User | None = db.query(User).filter(User.email == body.email).first()

    # Constant-time path regardless of user existence to prevent user enumeration
    dummy_hash = "$2b$12$KIXtSFl0u6OXo9yEUv1AqeHU4WFn0sBfJQv9JR7Ogh.dkGJPMRrFC"
    ok = verify_password(body.password, user.hashed_password if user else dummy_hash)

    if not user or not ok or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Update last login timestamp
    user.last_login_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            action="user.login",
            entity_type="user",
            entity_id=str(user.id),
            actor_id=user.email,
            actor_type="user",
            actor_role=user.role,
            actor_ip=_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )
    )
    db.commit()

    return TokenResponse(
        access_token=create_access_token(user.email, user.role),
        refresh_token=create_refresh_token(user.email, user.role),
    )


@router.post("/refresh")
def refresh_tokens(
    body: RefreshRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Exchange a valid refresh token for a new access + refresh token pair."""
    try:
        payload = decode_token(body.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    if payload.token_type != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token required")

    user: User | None = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return TokenResponse(
        access_token=create_access_token(user.email, user.role),
        refresh_token=create_refresh_token(user.email, user.role),
    )


@router.get("/me")
def me(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> MeResponse:
    """Return the profile of the currently authenticated user."""
    token = _extract_bearer(authorization)
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    if payload.token_type != "access":
        raise HTTPException(status_code=401, detail="Access token required")

    user: User | None = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return MeResponse(
        email=user.email,
        role=user.role,
        display_name=user.display_name,
        is_active=user.is_active,
    )


# ---------------------------------------------------------------------------
# Dependency: require_jwt_user — usable as FastAPI Depends target
# ---------------------------------------------------------------------------


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AdminActor:
    """FastAPI dependency that validates a Bearer JWT and returns an AdminActor."""
    token = _extract_bearer(authorization)
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    if payload.token_type != "access":
        raise HTTPException(status_code=401, detail="Access token required")

    user: User | None = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return AdminActor(
        actor_id=user.email,
        actor_type="user",
        role=user.role,  # type: ignore[arg-type]
        auth_method="jwt",
        display_name=user.display_name,
        email=user.email,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _validate_password_strength(password: str) -> None:
    """Enforce minimum password requirements. Raises HTTPException on failure."""
    if len(password) < 12:
        raise HTTPException(
            status_code=422,
            detail="Password must be at least 12 characters",
        )
    if not any(c.isupper() for c in password):
        raise HTTPException(
            status_code=422,
            detail="Password must contain at least one uppercase letter",
        )
    if not any(c.isdigit() for c in password):
        raise HTTPException(
            status_code=422,
            detail="Password must contain at least one digit",
        )
