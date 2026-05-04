"""Tests for memory_graph_bridge.sync_claims_to_graph.

Verifies that:
- Each mapped claim type produces exactly one EntityGraphEdge.
- Unknown claim types are silently skipped (0 edges inserted).
- A second call with identical claims inserts 0 new edges (idempotency).
- An empty claim list returns 0.
"""

from __future__ import annotations

import uuid

from app.db.session import SessionLocal
from app.memory.memory_graph_bridge import sync_claims_to_graph
from app.models.entities import CanonicalEntity, EntityGraphEdge, MemoryClaim


def _uid() -> str:
    return uuid.uuid4().hex[:10]


def _make_entity(db) -> CanonicalEntity:
    entity = CanonicalEntity(
        entity_type="judge",
        canonical_name=f"Bridge Test Judge {_uid()}",
        canonical_id_external=f"bridge-judge-{_uid()}",
        merge_confidence=1.0,
        status="active",
    )
    db.add(entity)
    db.flush()
    return entity


def _make_claim(db, entity_id: int, claim_type: str) -> MemoryClaim:
    claim = MemoryClaim(
        claim_type=claim_type,
        entity_id=entity_id,
        claim_value="test value",
        confidence=0.9,
        is_active=True,
        status="active",
    )
    db.add(claim)
    db.flush()
    return claim


class TestMemoryGraphBridge:
    """Unit tests for sync_claims_to_graph."""

    def test_known_claim_types_produce_edges(self) -> None:
        """Every mapped claim type creates exactly one EntityGraphEdge."""
        known_types = ["name_mention", "role", "location", "affiliation", "title"]
        with SessionLocal() as db:
            entity = _make_entity(db)
            claims = [_make_claim(db, entity.id, ct) for ct in known_types]
            inserted = sync_claims_to_graph(entity.id, claims, db)
            db.flush()

            edges = (
                db.query(EntityGraphEdge)
                .filter(
                    EntityGraphEdge.subject_type == "canonical_entity",
                    EntityGraphEdge.subject_id == entity.id,
                )
                .all()
            )
            assert inserted == len(known_types)
            assert len(edges) == len(known_types)
            predicates = {e.predicate for e in edges}
            assert predicates == {
                "has_alias",
                "has_role",
                "located_in",
                "affiliated_with",
                "holds_title",
            }

    def test_unknown_claim_type_is_skipped(self) -> None:
        """Unknown claim types produce no edges and the function returns 0."""
        with SessionLocal() as db:
            entity = _make_entity(db)
            claim = _make_claim(db, entity.id, "unknown_type_xyz")
            inserted = sync_claims_to_graph(entity.id, [claim], db)
            assert inserted == 0

    def test_idempotent_second_call(self) -> None:
        """A second call with the same claims inserts 0 new edges."""
        with SessionLocal() as db:
            entity = _make_entity(db)
            claim = _make_claim(db, entity.id, "role")

            first = sync_claims_to_graph(entity.id, [claim], db)
            second = sync_claims_to_graph(entity.id, [claim], db)
            db.flush()

            assert first == 1
            assert second == 0
            edges = (
                db.query(EntityGraphEdge)
                .filter(
                    EntityGraphEdge.subject_type == "canonical_entity",
                    EntityGraphEdge.subject_id == entity.id,
                    EntityGraphEdge.predicate == "has_role",
                )
                .all()
            )
            assert len(edges) == 1

    def test_empty_claims_returns_zero(self) -> None:
        """An empty claim list inserts nothing and returns 0."""
        with SessionLocal() as db:
            entity = _make_entity(db)
            inserted = sync_claims_to_graph(entity.id, [], db)
            assert inserted == 0
