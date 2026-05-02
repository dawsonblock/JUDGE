"""Memory rebuild orchestration.

Drives a MemoryRebuildRun: iterates canonical entities, extracts claims
via extract_claims.py, upserts MemoryClaim + MemoryEvidenceLink rows,
and updates MemoryEntityState checksums.

Does NOT import from map_record, graph edge, or public event tables.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.memory import entity_summary_checksum
from app.memory.extract_claims import extract_claims
from app.models.entities import (
    CanonicalEntity,
    MemoryClaim,
    MemoryEntityState,
    MemoryEvidenceLink,
    MemoryRebuildRun,
    SourceSnapshot,
)


def _get_latest_snapshot_for_entity(
    entity: CanonicalEntity,
    db: Session,
) -> SourceSnapshot | None:
    """Return the most recent SourceSnapshot in the store.

    In the current schema there is no direct canonical-entity → snapshot FK;
    the most recent snapshot is used as a reasonable default for text-based
    claim extraction. Future work may refine this via ingestion-run linkage.
    """
    return db.query(SourceSnapshot).order_by(SourceSnapshot.fetched_at.desc()).first()


def _upsert_claims(
    entity: CanonicalEntity,
    snapshot: SourceSnapshot,
    extracted: list[dict],
    db: Session,
) -> tuple[int, int]:
    """Insert new claims, skip existing (by claim_key).

    Returns:
        (created, skipped) counts.
    """
    created = 0
    skipped = 0
    for c in extracted:
        key = c["claim_key"]
        existing = db.query(MemoryClaim).filter(MemoryClaim.claim_key == key).first()
        if existing is not None:
            skipped += 1
            continue

        claim = MemoryClaim(
            claim_key=key,
            claim_type=c["claim_type"],
            entity_id=c["entity_id"],
            claim_value=c["claim_value"],
            claim_value_json=c.get("claim_value_json"),
            confidence=c.get("confidence", 0.0),
            source_snapshot_id=snapshot.id,
            is_active=True,
        )
        db.add(claim)
        db.flush()  # populate claim.id

        span_text: str | None = None
        if c.get("span_start") is not None and c.get("span_end") is not None:
            src = snapshot.extracted_text or ""
            span_text = src[c["span_start"] : c["span_end"]]

        db.add(
            MemoryEvidenceLink(
                claim_id=claim.id,
                snapshot_id=snapshot.id,
                evidence_checksum=snapshot.content_hash or "",
                span_start=c.get("span_start"),
                span_end=c.get("span_end"),
                span_text=span_text,
            )
        )
        created += 1
    return created, skipped


def _rebuild_entity_state(
    entity: CanonicalEntity,
    rebuild_run: MemoryRebuildRun,
    db: Session,
) -> bool:
    """Compute and upsert MemoryEntityState for *entity*.

    Returns True if the state was created or updated, False if unchanged.
    """
    active_claims = (
        db.query(MemoryClaim)
        .filter(MemoryClaim.entity_id == entity.id, MemoryClaim.is_active.is_(True))
        .all()
    )
    claims_as_dicts = [
        {"claim_key": c.claim_key, "claim_type": c.claim_type} for c in active_claims
    ]
    checksum = entity_summary_checksum(claims_as_dicts)

    state = (
        db.query(MemoryEntityState)
        .filter(MemoryEntityState.entity_id == entity.id)
        .first()
    )

    aliases: list[str] = []
    roles: list[str] = []
    for claim in active_claims:
        if claim.claim_type == "name_mention":
            val = (claim.claim_value_json or {}).get("alias") or claim.claim_value
            if val and val not in aliases:
                aliases.append(val)
        elif claim.claim_type == "role":
            role = (claim.claim_value_json or {}).get("role") or claim.claim_value
            if role and role not in roles:
                roles.append(role)

    now = datetime.now(timezone.utc)

    if state is None:
        db.add(
            MemoryEntityState(
                entity_id=entity.id,
                state_checksum=checksum,
                display_name=entity.canonical_name,
                aliases=aliases or None,
                roles=roles or None,
                jurisdictions=None,
                last_rebuild_run_id=rebuild_run.id,
                rebuilt_at=now,
                active_claim_count=len(active_claims),
            )
        )
        return True

    if state.state_checksum == checksum:
        return False  # nothing changed

    state.state_checksum = checksum
    state.display_name = entity.canonical_name
    state.aliases = aliases or None
    state.roles = roles or None
    state.last_rebuild_run_id = rebuild_run.id
    state.rebuilt_at = now
    state.active_claim_count = len(active_claims)
    return True


def run_rebuild(
    scope: str,
    db: Session,
    entity_id: int | None = None,
) -> MemoryRebuildRun:
    """Orchestrate a memory rebuild run.

    Args:
        scope:     "full" rebuilds all active entities; "entity" scopes to one.
        db:        SQLAlchemy session (caller is responsible for commit/rollback).
        entity_id: Required when scope="entity".

    Returns:
        The completed (or failed) MemoryRebuildRun.
    """
    if scope not in {"full", "entity"}:
        raise ValueError(f"Unknown rebuild scope: {scope!r}")
    if scope == "entity" and entity_id is None:
        raise ValueError("entity_id is required for scope='entity'")

    run = MemoryRebuildRun(
        rebuild_scope=scope,
        scope_entity_id=entity_id,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.flush()

    try:
        if scope == "entity":
            entity = db.get(CanonicalEntity, entity_id)
            if entity is None:
                raise ValueError(f"CanonicalEntity {entity_id} does not exist")
            entities: list[CanonicalEntity] = [entity]
        else:
            entities = (
                db.query(CanonicalEntity)
                .filter(CanonicalEntity.status == "active")
                .all()
            )

        for entity in entities:
            run.entities_processed += 1
            snapshot = _get_latest_snapshot_for_entity(entity, db)
            if snapshot is None:
                continue

            extracted = extract_claims(snapshot, entity, db)
            created, _ = _upsert_claims(entity, snapshot, extracted, db)
            run.claims_created += created

            if _rebuild_entity_state(entity, run, db):
                run.states_updated += 1

        run.status = "completed"
        run.finished_at = datetime.now(timezone.utc)

    except Exception as exc:
        run.status = "failed"
        run.finished_at = datetime.now(timezone.utc)
        run.error_message = str(exc)

    return run
