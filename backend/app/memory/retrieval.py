"""Read-only memory layer queries.

Provides stable, filtered access to MemoryClaim and MemoryEntityState
data for API and service consumers.

Does NOT import from map_record, graph edge, or public event tables.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import MemoryClaim, MemoryEntityState


def get_entity_state(entity_id: int, db: Session) -> MemoryEntityState | None:
    """Return the current MemoryEntityState for *entity_id*, or None."""
    return (
        db.query(MemoryEntityState)
        .filter(MemoryEntityState.entity_id == entity_id)
        .first()
    )


def get_active_claims(entity_id: int, db: Session) -> list[MemoryClaim]:
    """Return all active MemoryClaims for *entity_id* ordered by id."""
    return (
        db.query(MemoryClaim)
        .filter(
            MemoryClaim.entity_id == entity_id,
            MemoryClaim.is_active.is_(True),
            MemoryClaim.status == "active",
        )
        .order_by(MemoryClaim.id)
        .all()
    )


def list_claims(
    db: Session,
    entity_id: int | None = None,
    claim_type: str | None = None,
) -> list[MemoryClaim]:
    """Return MemoryClaims with optional filters.

    Args:
        db:         SQLAlchemy session.
        entity_id:  Filter by subject entity (optional).
        claim_type: Filter by claim type (optional).

    Returns:
        Matching MemoryClaim rows ordered by id.
    """
    q = db.query(MemoryClaim)
    if entity_id is not None:
        q = q.filter(MemoryClaim.entity_id == entity_id)
    if claim_type is not None:
        q = q.filter(MemoryClaim.claim_type == claim_type)
    return q.order_by(MemoryClaim.id).all()
