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


def _validate_cors_origins(cors_origins: str, app_env: str) -> list[str]:
    """Validate CORS origins. In production, fail if empty or wildcard."""
    origins = [
        origin.strip()
        for origin in cors_origins.split(",")
        if origin.strip()
    ]

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

    print("[STARTUP] Production safety checks passed")


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size using Content-Length header."""

    def __init__(self, app, max_size: int):
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            # Check Content-Length header first (safer than reading body)
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
                    # Invalid Content-Length, let request proceed
                    pass
        return await call_next(request)


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
        if settings.auto_seed and settings.app_env == "development":
            with SessionLocal() as db:
                seed_sample_data(db)
        yield

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
