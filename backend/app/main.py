import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api.routes import router
from app.core.config import get_settings
from app.db.session import SessionLocal, engine
from app.db.spatial import initialize_postgis
from app.models import entities  # noqa: F401
from app.seed.sample_data import seed_sample_data
from app.seed.source_registry import seed_source_registry


def _validate_cors_origins(cors_origins: str, app_env: str) -> list[str]:
    """Validate CORS origins. In production, fail if empty or wildcard."""
    origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

    # In production, reject empty or wildcard origins
    if app_env == "production":
        if not origins:
            print(
                "ERROR: JTA_CORS_ORIGINS required in production. "
                "Set explicit HTTPS URLs."
            )
            sys.exit(1)
        if "*" in origins:
            print(
                "ERROR: Wildcard '*' not allowed in JTA_CORS_ORIGINS "
                "in production mode."
            )
            sys.exit(1)
        # Verify all origins are HTTPS
        non_https = [o for o in origins if not o.startswith("https://")]
        if non_https:
            print(f"ERROR: Non-HTTPS origins not allowed: {non_https}")
            sys.exit(1)

    return origins if origins else ["*"]


def _validate_production_safety(settings) -> None:
    """Validate production safety settings. Fail fast if unsafe."""
    if settings.app_env != "production":
        return  # Skip checks outside production

    # Check for missing admin tokens
    if not settings.admin_token:
        print("ERROR: JTA_ADMIN_TOKEN required in production")
        sys.exit(1)
    if not settings.admin_review_token:
        print("ERROR: JTA_ADMIN_REVIEW_TOKEN required in production")
        sys.exit(1)

    # Reject dev tokens
    dev_token_markers = ["dev", "change-in-production", "localhost", "test"]
    for token in [settings.admin_token, settings.admin_review_token]:
        if any(marker in token.lower() for marker in dev_token_markers):
            print(
                "ERROR: Development token detected in production. "
                "Use secure, random tokens for production."
            )
            sys.exit(1)

    # Reject in-memory rate limiting in production (not safe across multiple workers/replicas)
    # unless the operator explicitly opts in with JTA_ALLOW_IN_MEMORY_RATE_LIMIT_PRODUCTION=true.
    if settings.rate_limit_backend != "redis":
        allow_override = os.environ.get(
            "JTA_ALLOW_IN_MEMORY_RATE_LIMIT_PRODUCTION", ""
        ).lower()
        if allow_override not in ("1", "true", "yes"):
            print(
                "ERROR: JTA_RATE_LIMIT_BACKEND=memory is unsafe in production with "
                "multiple workers or replicas. Set JTA_RATE_LIMIT_BACKEND=redis, or "
                "set JTA_ALLOW_IN_MEMORY_RATE_LIMIT_PRODUCTION=true only for "
                "verified single-node deployments."
            )
            sys.exit(1)

    # Check Redis availability if configured
    if settings.rate_limit_backend == "redis":
        import redis

        try:
            r = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
            r.ping()
        except Exception as e:
            print(
                f"ERROR: Redis configured but unavailable in production: {e}. "
                "Rate limiting requires Redis in production."
            )
            sys.exit(1)

    # Require evidence vault in production
    if not settings.evidence_store_required:
        print(
            "ERROR: JTA_EVIDENCE_STORE_REQUIRED must be true in production. "
            "Set JTA_EVIDENCE_STORE_REQUIRED=true and configure JTA_EVIDENCE_STORE_ROOT."
        )
        sys.exit(1)

    print("[STARTUP] Production safety checks passed")


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size using Content-Length header."""

    def __init__(self, app, max_size: int):
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        limit_exceeded = False
        if request.method in ("POST", "PUT", "PATCH"):
            # Check Content-Length header first (cheaper path)
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    size = int(content_length)
                    if size > self.max_size:
                        return JSONResponse(
                            status_code=413,
                            content={
                                "error": "Request too large",
                                "max_size_bytes": self.max_size,
                                "content_length": size,
                            },
                        )
                except ValueError:
                    # Invalid Content-Length value — fall through to streaming check
                    pass
            else:
                # No Content-Length (chunked / streaming upload): wrap receive to
                # enforce byte cap without buffering the whole body at once.
                original_receive = request._receive
                bytes_seen = 0

                async def capped_receive():
                    nonlocal bytes_seen, limit_exceeded
                    message = await original_receive()
                    if message.get("type") == "http.request":
                        chunk = message.get("body", b"")
                        bytes_seen += len(chunk)
                        if bytes_seen > self.max_size:
                            limit_exceeded = True
                            return {
                                "type": "http.request",
                                "body": b"",
                                "more_body": False,
                            }
                    return message

                request._receive = capped_receive
        response = await call_next(request)
        if limit_exceeded:
            return JSONResponse(
                status_code=413,
                content={
                    "error": "Request too large",
                    "max_size_bytes": self.max_size,
                },
            )
        return response


def create_app() -> FastAPI:
    from pathlib import Path
    from app.services.evidence_store_validation import validate_evidence_store_root

    settings = get_settings()

    # Validate production safety before proceeding
    _validate_production_safety(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Validate evidence store before initializing database
        try:
            validate_evidence_store_root(
                settings.evidence_store_root,
                required=settings.evidence_store_required,
                probe_write=settings.evidence_store_probe_write,
                repo_root=str(Path(__file__).resolve().parents[2]),
            )
            print("[STARTUP] Evidence store validated")
        except RuntimeError as e:
            print(f"ERROR: Evidence store validation failed: {e}")
            sys.exit(1)

        initialize_postgis(engine)
        # Source registry is seeded independently of sample data (prod-safe)
        if settings.seed_source_registry:
            with SessionLocal() as db:
                seed_source_registry(db)
        if settings.auto_seed and settings.app_env == "development":
            with SessionLocal() as db:
                seed_sample_data(db)
        from app.workers.scheduler import build_scheduler

        scheduler = build_scheduler(SessionLocal)
        scheduler.start()
        yield
        scheduler.shutdown(wait=False)

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    # Configure rate limiting (simple in-memory limiter raises HTTPException(429) directly)
    from app.core.rate_limit import get_rate_limiter

    limiter = get_rate_limiter()
    if limiter:
        app.state.limiter = limiter

    # Configure request size limits
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_size=settings.max_request_size,
    )

    origins = _validate_cors_origins(settings.cors_origins, settings.app_env)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
