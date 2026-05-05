"""Admin source registry management endpoints.

Manage ingestion sources: enable/disable, configure rate limits,
view health status, and control trust tiers.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.auth.admin import require_admin_token, require_source_admin, log_mutation
from app.auth.actor import AdminActor
from app.core.rate_limit import rate_limit_admin
from app.db.session import get_db
from app.models.entities import IngestionRun, SourceRegistry
from app.ingestion.statuses import COMPLETED, COMPLETED_WITH_ERRORS, FAILED

router = APIRouter(prefix="/api/admin/sources", tags=["admin"])


class SourceUpdateRequest(BaseModel):
    """Request to update source configuration."""

    is_active: bool | None = None
    rate_limit_rpm: int | None = Field(None, ge=1, le=10000)
    source_tier: str | None = Field(
        None,
        pattern=r"^(court_record|official_police_open_data|official_government_statistics|verified_news_context|news_only_context)$",
    )
    admin_notes: str | None = None
    config_json: str | None = None
    auto_publish_enabled: bool | None = None
    requires_manual_review: bool | None = None
    # New Canada-first metadata fields
    priority: int | None = Field(None, ge=1, le=100)
    base_url: str | None = Field(None, max_length=2048)
    allowed_domains: str | None = None  # JSON array
    refresh_interval_minutes: int | None = Field(None, ge=1)
    parser: str | None = Field(None, max_length=120)


class SourceHealthMetrics(BaseModel):
    """Health metrics for a source."""

    health_score: float  # 0.0-1.0
    last_successful_fetch: datetime | None
    last_error: str | None
    last_error_at: datetime | None
    last_ingested_at: datetime | None
    recent_run_count: int
    recent_error_count: int


class SourceResponse(BaseModel):
    """Source registry entry response."""

    id: int
    source_key: str
    source_name: str
    source_type: str
    country: str | None
    province_state: str | None
    city: str | None
    source_tier: str
    is_active: bool
    rate_limit_rpm: int | None
    health_score: float
    last_successful_fetch: datetime | None
    last_ingested_at: datetime | None
    admin_notes: str | None
    auto_publish_enabled: bool
    requires_manual_review: bool
    created_at: datetime
    updated_at: datetime
    # Canada-first metadata fields
    jurisdiction: str | None = None
    category: str | None = None
    priority: int = 50
    enabled_default: bool = False
    public_record_authority: str = "unknown"
    base_url: str | None = None
    allowed_domains: str | None = None
    refresh_interval_minutes: int | None = None
    parser: str | None = None
    creates: str | None = None
    public_publish_default: bool = False
    terms_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class IngestionRunSummary(BaseModel):
    """Summary of an ingestion run."""

    id: int
    status: str
    started_at: datetime
    finished_at: datetime | None
    fetched_count: int
    parsed_count: int
    persisted_count: int
    error_count: int

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=list[SourceResponse])
def list_sources(
    db: Session = Depends(get_db),
    _: AdminActor = Depends(require_admin_token),
    is_active: bool | None = Query(None, description="Filter by active status"),
    source_type: str | None = Query(None, description="Filter by source type"),
    country: str | None = Query(None, description="Filter by country"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[SourceRegistry]:
    """List all ingestion sources with optional filters."""
    query = db.query(SourceRegistry)

    if is_active is not None:
        query = query.filter(SourceRegistry.is_active == is_active)
    if source_type:
        query = query.filter(SourceRegistry.source_type == source_type)
    if country:
        query = query.filter(SourceRegistry.country == country)

    sources = query.order_by(SourceRegistry.source_name).offset(skip).limit(limit).all()
    return sources


@router.get("/{source_key}", response_model=SourceResponse)
def get_source(
    source_key: str,
    db: Session = Depends(get_db),
    _: AdminActor = Depends(require_admin_token),
) -> SourceRegistry:
    """Get detailed information about a specific source."""
    source = (
        db.query(SourceRegistry).filter(SourceRegistry.source_key == source_key).first()
    )

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    return source


@router.patch(
    "/{source_key}",
    response_model=SourceResponse,
    dependencies=[Depends(rate_limit_admin)],
)
def update_source(
    source_key: str,
    update: SourceUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_admin_token),
) -> SourceRegistry:
    """Update source configuration (enable/disable, rate limit, tier, notes)."""
    source = (
        db.query(SourceRegistry).filter(SourceRegistry.source_key == source_key).first()
    )

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    # Apply updates
    if update.is_active is not None:
        source.is_active = update.is_active
    if update.rate_limit_rpm is not None:
        source.rate_limit_rpm = update.rate_limit_rpm
    if update.source_tier is not None:
        source.source_tier = update.source_tier
    if update.admin_notes is not None:
        source.admin_notes = update.admin_notes
    if update.config_json is not None:
        import json

        try:
            json.loads(update.config_json)
        except (json.JSONDecodeError, TypeError) as exc:
            raise HTTPException(
                status_code=422, detail=f"config_json is not valid JSON: {exc}"
            )
        source.config_json = update.config_json
    if update.auto_publish_enabled is not None:
        source.auto_publish_enabled = update.auto_publish_enabled
    if update.requires_manual_review is not None:
        source.requires_manual_review = update.requires_manual_review
    if update.priority is not None:
        source.priority = update.priority
    if update.base_url is not None:
        source.base_url = update.base_url
    if update.allowed_domains is not None:
        import json

        try:
            json.loads(update.allowed_domains)
        except (json.JSONDecodeError, TypeError) as exc:
            raise HTTPException(
                status_code=422, detail=f"allowed_domains is not valid JSON: {exc}"
            )
        source.allowed_domains = update.allowed_domains
    if update.refresh_interval_minutes is not None:
        source.refresh_interval_minutes = update.refresh_interval_minutes
    if update.parser is not None:
        source.parser = update.parser

    source.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(source)

    # Log the mutation
    log_mutation(
        action="source.update",
        entity_type="source_registry",
        entity_id=source.source_key,
        payload=update.model_dump(exclude_unset=True),
        request=request,
        actor=actor,
    )

    return source


@router.post(
    "/{source_key}/enable",
    response_model=SourceResponse,
    dependencies=[Depends(rate_limit_admin)],
)
def enable_source(
    source_key: str,
    request: Request,
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_source_admin),
) -> SourceRegistry:
    """Enable a source for ingestion."""
    source = (
        db.query(SourceRegistry).filter(SourceRegistry.source_key == source_key).first()
    )

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    source.is_active = True
    source.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(source)

    # Log the mutation
    log_mutation(
        action="source.enable",
        entity_type="source_registry",
        entity_id=source.source_key,
        payload={"is_active": True},
        request=request,
        actor=actor,
    )

    return source


@router.post(
    "/{source_key}/disable",
    response_model=SourceResponse,
    dependencies=[Depends(rate_limit_admin)],
)
def disable_source(
    source_key: str,
    request: Request,
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_source_admin),
) -> SourceRegistry:
    """Disable a source (stops active crawls)."""
    source = (
        db.query(SourceRegistry).filter(SourceRegistry.source_key == source_key).first()
    )

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    source.is_active = False
    source.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(source)

    # Log the mutation
    log_mutation(
        action="source.disable",
        entity_type="source_registry",
        entity_id=source.source_key,
        payload={"is_active": False},
        request=request,
        actor=actor,
    )

    return source


@router.get("/{source_key}/health", response_model=SourceHealthMetrics)
def get_source_health(
    source_key: str,
    db: Session = Depends(get_db),
    _: AdminActor = Depends(require_admin_token),
    days: int = Query(7, ge=1, le=90, description="Lookback period in days"),
) -> dict[str, Any]:
    """Get health metrics for a source."""
    source = (
        db.query(SourceRegistry).filter(SourceRegistry.source_key == source_key).first()
    )

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    # Calculate recent run metrics
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    run_stats = (
        db.query(
            func.count(IngestionRun.id).label("total_runs"),
            func.sum(IngestionRun.error_count).label("total_errors"),
        )
        .filter(
            IngestionRun.source_name == source_key, IngestionRun.started_at >= cutoff
        )
        .first()
    )

    return {
        "health_score": source.health_score,
        "last_successful_fetch": source.last_successful_fetch,
        "last_error": source.last_error,
        "last_error_at": source.last_error_at,
        "last_ingested_at": source.last_ingested_at,
        "recent_run_count": run_stats.total_runs or 0,
        "recent_error_count": run_stats.total_errors or 0,
    }


class RunResult(BaseModel):
    """Result of a manually triggered ingestion run."""

    source_key: str
    records_fetched: int
    records_skipped: int
    adapter_records: int  # rows the adapter returned before dedup
    created_records: int  # rows actually persisted to DB (after dedup)
    duplicates_skipped: int  # rows skipped as duplicates during persist
    review_items: int
    errors: list[str]
    success: bool


@router.post(
    "/{source_key}/run",
    response_model=RunResult,
    dependencies=[Depends(rate_limit_admin)],
)
def run_source_now(
    source_key: str,
    request: Request,
    db: Session = Depends(get_db),
    actor: AdminActor = Depends(require_source_admin),
) -> dict[str, Any]:
    """Manually trigger an ingestion run for a source."""
    source = (
        db.query(SourceRegistry).filter(SourceRegistry.source_key == source_key).first()
    )

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    if not source.is_active:
        raise HTTPException(
            status_code=409,
            detail=f"Source '{source_key}' is disabled; enable it before running.",
        )

    source_class = getattr(source, "source_class", None)
    if source_class == "portal_reference":
        raise HTTPException(
            status_code=422,
            detail=(
                f"Source '{source_key}' is a portal_reference and cannot be "
                "auto-run. Update base_url to a machine-readable API endpoint "
                "and set source_class to 'machine_ingest'."
            ),
        )

    from app.core.config import get_settings
    from app.ingestion.source_adapter_factory import build_adapter
    from app.ingestion.source_runner import persist_ingestion_result

    adapter = build_adapter(source, get_settings())
    if adapter is None:
        raise HTTPException(
            status_code=501,
            detail=f"No adapter registered for parser '{source.parser}'. Run not started.",
        )

    # Persist an IngestionRun record before executing
    run_record = IngestionRun(
        source_name=source.source_key,
        started_at=datetime.now(timezone.utc),
        status="running",
    )
    db.add(run_record)
    db.commit()

    try:
        result = adapter.run()
    except Exception as exc:
        run_record.status = FAILED
        run_record.finished_at = datetime.now(timezone.utc)
        run_record.error_count = 1
        run_record.errors = [str(exc)]
        db.commit()
        raise HTTPException(status_code=500, detail=f"Adapter error: {exc}") from exc

    run_record.status = COMPLETED if result.success else COMPLETED_WITH_ERRORS
    run_record.finished_at = datetime.now(timezone.utc)
    run_record.fetched_count = result.records_fetched
    run_record.parsed_count = len(result.created_records) + len(result.review_items)
    run_record.skipped_count = result.records_skipped
    run_record.error_count = len(result.errors)
    run_record.errors = result.errors or None

    persist_summary = persist_ingestion_result(db, source, run_record, result)
    db.commit()

    log_mutation(
        action="source.run",
        entity_type="source_registry",
        entity_id=source.source_key,
        payload={
            "ingestion_run_id": run_record.id,
            "records_fetched": result.records_fetched,
            "created_records": persist_summary.persisted_incidents,
            "skipped_duplicates": persist_summary.skipped_duplicates,
            "review_items": persist_summary.persisted_review_items,
            "errors": result.errors,
        },
        request=request,
        actor=actor,
    )

    return {
        "source_key": source_key,
        "records_fetched": result.records_fetched,
        "records_skipped": result.records_skipped,
        "adapter_records": len(result.created_records),
        "created_records": persist_summary.persisted_incidents,
        "duplicates_skipped": persist_summary.skipped_duplicates,
        "review_items": len(result.review_items),
        "errors": result.errors,
        "success": result.success,
    }


@router.get("/{source_key}/runs", response_model=list[IngestionRunSummary])
def get_source_runs(
    source_key: str,
    db: Session = Depends(get_db),
    _: AdminActor = Depends(require_admin_token),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[IngestionRun]:
    """Get ingestion run history for a source."""
    source = (
        db.query(SourceRegistry).filter(SourceRegistry.source_key == source_key).first()
    )

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found")

    runs = (
        db.query(IngestionRun)
        .filter(IngestionRun.source_name == source_key)
        .order_by(desc(IngestionRun.started_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return runs
