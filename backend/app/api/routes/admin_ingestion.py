"""Admin ingestion run dashboard endpoints.

View ingestion run history, metrics, errors, and related entities.
Provides observability into the data ingestion pipeline.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import case, desc, func
from sqlalchemy.orm import Session

from app.auth.admin import require_admin_token
from app.auth.actor import AdminActor
from app.db.session import get_db
from app.models.entities import IngestionRun, ReviewItem, SourceRegistry, SourceSnapshot

router = APIRouter(prefix="/api/admin/ingestion-runs", tags=["admin"])


class IngestionRunSummary(BaseModel):
    """Summary of an ingestion run for listing."""

    id: int
    source_name: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    fetched_count: int
    parsed_count: int
    persisted_count: int
    skipped_count: int
    error_count: int
    duration_seconds: float | None = None

    model_config = ConfigDict(from_attributes=True)


class IngestionRunDetail(BaseModel):
    """Detailed view of an ingestion run."""

    id: int
    source_name: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    fetched_count: int
    parsed_count: int
    persisted_count: int
    skipped_count: int
    error_count: int
    errors: list | None
    duration_seconds: float | None = None
    success_rate: float | None = None

    model_config = ConfigDict(from_attributes=True)


class DailyStats(BaseModel):
    """Daily ingestion statistics."""

    date: date
    total_runs: int
    successful_runs: int
    failed_runs: int
    total_fetched: int
    total_parsed: int
    total_persisted: int
    total_errors: int


class SourceStats(BaseModel):
    """Statistics for a specific source."""

    source: str
    total_runs: int
    success_rate: float
    avg_duration_seconds: float | None
    total_fetched: int
    total_persisted: int
    last_run_at: datetime | None


@router.get("", response_model=list[IngestionRunSummary])
def list_ingestion_runs(
    db: Session = Depends(get_db),
    _: AdminActor = Depends(require_admin_token),
    source: str | None = Query(None, description="Filter by source key"),
    status: str | None = Query(None, description="Filter by status"),
    from_date: date | None = Query(None, description="Start date filter"),
    to_date: date | None = Query(None, description="End date filter"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[IngestionRun]:
    """List ingestion runs with filtering and pagination."""
    query = db.query(IngestionRun)

    if source:
        query = query.filter(IngestionRun.source_name == source)
    if status:
        query = query.filter(IngestionRun.status == status)
    if from_date:
        query = query.filter(IngestionRun.started_at >= from_date)
    if to_date:
        query = query.filter(IngestionRun.started_at <= to_date)

    runs = query.order_by(desc(IngestionRun.started_at)).offset(skip).limit(limit).all()

    return runs


@router.get("/stats/daily", response_model=list[DailyStats])
def get_daily_stats(
    db: Session = Depends(get_db),
    _: AdminActor = Depends(require_admin_token),
    days: int = Query(7, ge=1, le=90),
) -> list[DailyStats]:
    """Get daily ingestion statistics for the last N days."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Group by date
    daily = (
        db.query(
            func.date(IngestionRun.started_at).label("run_date"),
            func.count(IngestionRun.id).label("total_runs"),
            func.sum(case((IngestionRun.status == "completed", 1), else_=0)).label(
                "successful"
            ),
            func.sum(case((IngestionRun.status == "failed", 1), else_=0)).label(
                "failed"
            ),
            func.sum(IngestionRun.fetched_count).label("total_fetched"),
            func.sum(IngestionRun.parsed_count).label("total_parsed"),
            func.sum(IngestionRun.persisted_count).label("total_persisted"),
            func.sum(IngestionRun.error_count).label("total_errors"),
        )
        .filter(IngestionRun.started_at >= cutoff)
        .group_by(func.date(IngestionRun.started_at))
        .order_by("run_date")
        .all()
    )

    return [
        DailyStats(
            date=row.run_date,
            total_runs=row.total_runs,
            successful_runs=row.successful or 0,
            failed_runs=row.failed or 0,
            total_fetched=row.total_fetched or 0,
            total_parsed=row.total_parsed or 0,
            total_persisted=row.total_persisted or 0,
            total_errors=row.total_errors or 0,
        )
        for row in daily
    ]


@router.get("/stats/by-source", response_model=list[SourceStats])
def get_source_stats(
    db: Session = Depends(get_db),
    _: AdminActor = Depends(require_admin_token),
    days: int = Query(30, ge=1, le=90),
) -> list[SourceStats]:
    """Get statistics grouped by source."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Get runs grouped by source
    runs = db.query(IngestionRun).filter(IngestionRun.started_at >= cutoff).all()

    # Group by source_name in Python
    from collections import defaultdict

    source_groups = defaultdict(list)
    for run in runs:
        source_groups[run.source_name].append(run)

    results = []
    for source_name, source_runs in source_groups.items():
        total_runs = len(source_runs)
        successful = sum(1 for r in source_runs if r.status == "completed")

        # Calculate avg duration in Python (SQLite-safe)
        durations = []
        for r in source_runs:
            if r.finished_at and r.started_at:
                durations.append((r.finished_at - r.started_at).total_seconds())
        avg_duration = sum(durations) / len(durations) if durations else None

        total_fetched = sum(r.fetched_count for r in source_runs)
        total_persisted = sum(r.persisted_count for r in source_runs)
        last_run = max(r.started_at for r in source_runs) if source_runs else None

        results.append(
            SourceStats(
                source=source_name,
                total_runs=total_runs,
                success_rate=(successful / total_runs * 100) if total_runs else 0,
                avg_duration_seconds=avg_duration,
                total_fetched=total_fetched,
                total_persisted=total_persisted,
                last_run_at=last_run,
            )
        )

    return results


@router.get("/{run_id}", response_model=IngestionRunDetail)
def get_ingestion_run(
    run_id: int,
    db: Session = Depends(get_db),
    _: AdminActor = Depends(require_admin_token),
) -> IngestionRun:
    """Get detailed information about a specific ingestion run."""
    run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    return run


@router.get("/{run_id}/review-items")
def get_run_review_items(
    run_id: int,
    db: Session = Depends(get_db),
    _: AdminActor = Depends(require_admin_token),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """Get review items created by an ingestion run."""
    run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    # Query review items directly linked to this ingestion run
    items = (
        db.query(ReviewItem)
        .filter(ReviewItem.ingestion_run_id == run_id)
        .order_by(desc(ReviewItem.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "run_id": run_id,
        "source_name": run.source_name,
        "total_items": len(items),
        "items": [
            {
                "id": item.id,
                "record_type": item.record_type,
                "source_url": item.source_url,
                "status": item.status,
                "created_at": item.created_at,
            }
            for item in items
        ],
    }


@router.get("/{run_id}/snapshots")
def get_run_snapshots(
    run_id: int,
    db: Session = Depends(get_db),
    _: AdminActor = Depends(require_admin_token),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """Get source snapshots related to an ingestion run."""
    run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    # Find snapshots directly linked to this ingestion run
    snapshots = (
        db.query(SourceSnapshot)
        .filter(SourceSnapshot.ingestion_run_id == run_id)
        .order_by(desc(SourceSnapshot.fetched_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "run_id": run_id,
        "source_name": run.source_name,
        "total_snapshots": len(snapshots),
        "snapshots": [
            {
                "id": s.id,
                "source_url": s.source_url,
                "fetched_at": s.fetched_at,
                "http_status": s.http_status,
                "storage_backend": s.storage_backend,
            }
            for s in snapshots
        ],
    }


@router.post("/{run_id}/retry")
def retry_ingestion_run(
    run_id: int,
    db: Session = Depends(get_db),
    _: AdminActor = Depends(require_admin_token),
) -> dict[str, Any]:
    """Re-trigger ingestion for the source that produced a given run.

    Creates a new IngestionRun; the original run is not mutated.
    Returns 404 if the run does not exist, 403 if the source is disabled,
    400 if the run is currently active, 422 if the source is not machine_ingest,
    and 501 if no adapter is registered for the source parser.
    """
    run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    # Guard: refuse to retry if the source is currently disabled.
    from app.services.source_control import SourceDisabledError, require_source_enabled

    try:
        require_source_enabled(db, run.source_name)
    except SourceDisabledError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    if run.status == "running":
        raise HTTPException(
            status_code=400, detail="Cannot retry a run that is currently running"
        )

    # Look up the SourceRegistry entry so we can build the adapter.
    source = (
        db.query(SourceRegistry)
        .filter(SourceRegistry.source_key == run.source_name)
        .first()
    )
    if not source:
        raise HTTPException(
            status_code=404,
            detail=f"Source '{run.source_name}' no longer exists in registry; cannot retry.",
        )

    source_class = getattr(source, "source_class", None)
    if source_class != "machine_ingest":
        raise HTTPException(
            status_code=422,
            detail={
                "source_key": source.source_key,
                "source_class": source_class,
                "reason": "Only machine_ingest sources can be retried.",
            },
        )

    from app.core.config import get_settings
    from app.ingestion.source_adapter_factory import build_adapter
    from app.ingestion.source_runner import persist_ingestion_result
    from app.ingestion.statuses import COMPLETED, COMPLETED_WITH_ERRORS, FAILED
    from app.ingestion.source_registry_ctl import update_source_health

    adapter = build_adapter(source, get_settings())
    if adapter is None:
        raise HTTPException(
            status_code=501,
            detail=f"No adapter registered for parser '{source.parser}'. Cannot retry.",
        )

    new_run = IngestionRun(
        source_name=source.source_key,
        started_at=datetime.now(timezone.utc),
        status="running",
    )
    db.add(new_run)
    db.commit()

    try:
        result = adapter.run()
    except Exception as exc:
        new_run.status = FAILED
        new_run.finished_at = datetime.now(timezone.utc)
        new_run.error_count = 1
        new_run.errors = [str(exc)]
        update_source_health(db, source.source_key, new_run)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Adapter error: {exc}") from exc

    new_run.status = COMPLETED if result.success else COMPLETED_WITH_ERRORS
    new_run.finished_at = datetime.now(timezone.utc)
    new_run.fetched_count = result.records_fetched
    new_run.parsed_count = len(result.created_records) + len(result.review_items)
    new_run.skipped_count = result.records_skipped
    new_run.error_count = len(result.errors)
    new_run.errors = result.errors or None

    persist_summary = persist_ingestion_result(db, source, new_run, result)
    db.commit()

    update_source_health(db, source.source_key, new_run)
    db.commit()

    return {
        "retried_run_id": run_id,
        "new_run_id": new_run.id,
        "run_id": new_run.id,
        "source_key": source.source_key,
        "records_fetched": result.records_fetched,
        "records_skipped": result.records_skipped,
        "adapter_records": len(result.created_records),
        "created_records": persist_summary.persisted_incidents,
        "duplicates_skipped": persist_summary.skipped_duplicates,
        "review_items": persist_summary.persisted_review_items,
        "errors": result.errors,
        "success": result.success,
    }
