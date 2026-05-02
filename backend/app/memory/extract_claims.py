"""Deterministic claim extraction from source snapshots.

Extracts structured claims about canonical entities from snapshot text.
Claims are returned as dicts; persistence is handled by rebuild.py.

Does NOT import from map_record, graph edge, or public event tables.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.memory import claim_key
from app.models.entities import CanonicalEntity, SourceSnapshot


def _build_claim(
    entity: CanonicalEntity,
    claim_type: str,
    predicate: str,
    normalized_text: str,
    confidence: float,
    span_start: int | None = None,
    span_end: int | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "claim_type": claim_type,
        "subject_type": entity.entity_type,
        "subject_id": entity.id,
        "predicate": predicate,
        "object_type": None,
        "object_id": None,
        "normalized_text": normalized_text,
    }
    key = claim_key(payload)
    return {
        "claim_key": key,
        "claim_type": claim_type,
        "entity_id": entity.id,
        "claim_value": normalized_text,
        "claim_value_json": extra,
        "confidence": confidence,
        "span_start": span_start,
        "span_end": span_end,
    }


_ROLE_PATTERNS: dict[str, list[str]] = {
    "district judge": [
        "district judge",
        "u.s. district judge",
        "federal district judge",
    ],
    "circuit judge": ["circuit judge", "appeals court judge", "court of appeals"],
    "magistrate judge": ["magistrate judge", "magistrate"],
    "bankruptcy judge": ["bankruptcy judge"],
    "chief judge": ["chief judge"],
    "senior judge": ["senior judge"],
}


def extract_claims(
    snapshot: SourceSnapshot,
    entity: CanonicalEntity,
    db: Session,  # noqa: ARG001 — reserved for future enrichment lookups
) -> list[dict[str, Any]]:
    """Extract structured claims about *entity* from *snapshot*.

    Returns a list of claim dicts without persisting anything.
    Each dict contains: claim_key, claim_type, entity_id, claim_value,
    claim_value_json, confidence, span_start, span_end.
    """
    text = snapshot.extracted_text or snapshot.raw_content or ""
    claims: list[dict[str, Any]] = []

    # Entity-type claim is always emitted when there is any text.
    if text:
        claims.append(
            _build_claim(
                entity=entity,
                claim_type="entity_type",
                predicate="is_type",
                normalized_text=entity.entity_type,
                confidence=1.0,
                extra={"entity_type": entity.entity_type},
            )
        )

    # Canonical-name mention claim when entity name appears in text.
    name_pattern = re.compile(re.escape(entity.canonical_name), re.IGNORECASE)
    first_match = name_pattern.search(text)
    if first_match:
        claims.append(
            _build_claim(
                entity=entity,
                claim_type="name_mention",
                predicate="mentioned_in",
                normalized_text=entity.canonical_name.strip().lower(),
                confidence=0.95,
                span_start=first_match.start(),
                span_end=first_match.end(),
            )
        )

    # Role keyword extraction.
    text_lower = text.lower()
    for role, patterns in _ROLE_PATTERNS.items():
        for pat in patterns:
            idx = text_lower.find(pat)
            if idx != -1:
                claims.append(
                    _build_claim(
                        entity=entity,
                        claim_type="role",
                        predicate="has_role",
                        normalized_text=role,
                        confidence=0.8,
                        span_start=idx,
                        span_end=idx + len(pat),
                        extra={"role": role, "matched_pattern": pat},
                    )
                )
                break  # one match per role type

    return claims
