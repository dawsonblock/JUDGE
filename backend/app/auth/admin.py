import hmac
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.actor import AdminActor
from app.auth.jwt_handler import decode_token
from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.models.entities import (
    AuditLog,
)

_TOKEN_ROLE_IMPORTS = "import"
_TOKEN_ROLE_REVIEW = "review"
_TOKEN_ROLE_ADMIN = "admin"

# Role hierarchy: lower rank = fewer privileges.
ROLE_RANK: dict[str, int] = {
    "viewer": 0,
    "reviewer": 1,
    "source_admin": 2,
    "system_admin": 3,
}


def enforce_min_role(actor: "AdminActor", required: str) -> "AdminActor":
    """Raise 403 if actor's role does not meet *required* rank; else return actor."""
    if ROLE_RANK.get(actor.role, -1) < ROLE_RANK[required]:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{actor.role}' is insufficient; '{required}' or higher required.",
        )
    return actor


def _compare_token(provided: str | None, expected: str | None) -> bool:
    """Constant-time token comparison using hmac.compare_digest."""
    if not provided or not expected:
        return False
    return hmac.compare_digest(provided.encode(), expected.encode())


def _require_token_for_role(
    settings: Settings,
    x_jta_admin_token: str | None,
    role: str,
) -> None:
    """Fail closed with 403 if token does not match the required role."""
    if role == _TOKEN_ROLE_IMPORTS:
        token = settings.admin_token
        configured = bool(token)
    elif role == _TOKEN_ROLE_REVIEW:
        token = settings.admin_review_token or settings.admin_token
        configured = bool(token)
    else:
        token = settings.admin_token or settings.admin_review_token
        configured = bool(token)

    if not configured:
        raise HTTPException(
            status_code=403,
            detail=f"Admin token not configured for role: {role}",
        )
    if not _compare_token(x_jta_admin_token, token):
        raise HTTPException(status_code=403, detail="Invalid admin token")


def require_admin_imports(
    x_jta_admin_token: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    if not settings.enable_admin_imports:
        raise HTTPException(status_code=403, detail="Admin imports are disabled")
    _require_token_for_role(settings, x_jta_admin_token, _TOKEN_ROLE_IMPORTS)


def require_admin_review(
    x_jta_admin_token: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    if not settings.enable_admin_review:
        raise HTTPException(status_code=403, detail="Admin review is disabled")
    _require_token_for_role(settings, x_jta_admin_token, _TOKEN_ROLE_REVIEW)


# AUTH GAP — shared-token limitations (see docs/AUTH_ROADMAP.md for upgrade path):
#   1. All valid tokens produce actor_id="shared-admin-token" — no per-user attribution.
#   2. Tokens never expire — a leaked token requires a redeploy to revoke.
#   3. No role separation at the *identity* level: reviewer and importer roles are
#      enforced by which endpoint is called, not by separate credentials.
#   4. No MFA or second-factor support.
#   5. Concurrent sessions from multiple operators are indistinguishable in audit logs.
# Upgrade: AUTH_ROADMAP.md §Phase 2 — replace with OIDC/Clerk/Auth0 JWT verification;
# extract sub claim as actor_id; keep AdminActor shape stable so callsites don't change.
def require_admin_token(
    x_jta_admin_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> AdminActor:
    """Require a valid admin token for general admin operations.

    When ``jwt_auth_enabled=True`` in config, a ``Authorization: Bearer <jwt>``
    header with a valid access token is accepted in addition to the legacy
    ``X-JTA-Admin-Token`` header.  The Bearer JWT path takes precedence.

    Returns an AdminActor with a stable, non-secret actor_id. The raw
    token value is NEVER returned or stored.
    """
    settings = get_settings()

    # --- JWT path (preferred when jwt_auth_enabled) ---------------------------
    if (
        settings.jwt_auth_enabled
        and authorization
        and authorization.startswith("Bearer ")
    ):
        raw_token = authorization.removeprefix("Bearer ").strip()
        try:
            payload = decode_token(raw_token)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc))
        if payload.token_type != "access":
            raise HTTPException(status_code=401, detail="Access token required")
        return AdminActor(
            actor_id=payload.email,
            actor_type="user",
            role=payload.role,  # type: ignore[arg-type]
            auth_method="jwt",
            email=payload.email,
        )

    # --- Legacy shared-token path ---------------------------------------------
    token = settings.admin_token or settings.admin_review_token

    if not token:
        raise HTTPException(status_code=403, detail="Admin token not configured")

    if not _compare_token(x_jta_admin_token, token):
        raise HTTPException(status_code=403, detail="Invalid admin token")

    # Shared-token mode: all valid tokens get system_admin role.
    # actor_id is a stable label — never the raw token value.
    return AdminActor(
        actor_id="shared-admin-token",
        actor_type="shared_token",
        role="system_admin",
        auth_method="shared_token",
    )


def require_viewer(
    x_jta_admin_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> AdminActor:
    """Require valid admin token with at least viewer role."""
    actor = require_admin_token(x_jta_admin_token, authorization)
    return enforce_min_role(actor, "viewer")


def require_reviewer(
    x_jta_admin_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> AdminActor:
    """Require valid admin token with at least reviewer role."""
    actor = require_admin_token(x_jta_admin_token, authorization)
    return enforce_min_role(actor, "reviewer")


def require_source_admin(
    x_jta_admin_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> AdminActor:
    """Require valid admin token with at least source_admin role."""
    actor = require_admin_token(x_jta_admin_token, authorization)
    return enforce_min_role(actor, "source_admin")


def require_system_admin(
    x_jta_admin_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> AdminActor:
    """Require valid admin token; returns actor with system_admin role."""
    return require_admin_token(x_jta_admin_token, authorization)


def require_public_event_post(
    x_jta_admin_token: str | None = Header(default=None),
) -> None:
    """Require admin token when public event posting is enabled."""
    settings = get_settings()
    if not settings.enable_public_event_post:
        raise HTTPException(status_code=403, detail="Public event posting is disabled")
    _require_token_for_role(settings, x_jta_admin_token, _TOKEN_ROLE_ADMIN)


def log_mutation(
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    payload: dict[str, Any] | None = None,
    request: Request | None = None,
    token_role: str | None = None,
    actor: AdminActor | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> None:
    """Log a mutation action to the audit log.

    Raw token values must never appear in the payload or actor fields.
    Pass an AdminActor to populate actor identity fields safely.
    """
    db: Session = SessionLocal()
    try:
        full_payload: dict[str, Any] = payload or {}
        if token_role:
            full_payload = {**full_payload, "token_role": token_role}

        # Resolve user_agent from request if not explicitly provided
        resolved_user_agent = user_agent
        if resolved_user_agent is None and request is not None:
            resolved_user_agent = request.headers.get("user-agent")

        log_entry = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=full_payload,
            actor_ip=(request.client.host if request and request.client else None),
            created_at=datetime.now(timezone.utc),
            # Actor identity — never store raw token values
            actor_id=actor.actor_id if actor else None,
            actor_type=actor.actor_type if actor else None,
            actor_role=actor.role if actor else None,
            user_agent=resolved_user_agent,
            request_id=request_id,
        )
        db.add(log_entry)
        db.commit()
    except Exception:
        logging.exception("audit log write failed for action=%s", action)
        db.rollback()
    finally:
        db.close()
