"""Evidence chat service.

Given a natural-language question and an optional entity context
(incident_id or case_id), retrieves public RelationshipEvidence records
and constructs a deterministic, citation-backed answer.

No external LLM is invoked. Classification is rule-based, making
responses auditable and free from hallucination.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.entities import CrimeIncident, RelationshipEvidence
from app.services.text import normalize_text

_MAX_QUESTION_LEN: int = 500
_MAX_CITATIONS: int = 5
_DISCLAIMER: str = (
    "Evidence citations describe source records only. "
    "They are not proof of guilt, conviction, or any legal finding. "
    "All individuals are presumed innocent until proven guilty in a court of law."
)


@dataclass
class ChatCitation:
    evidence_id: int
    relationship_type: str
    evidence_type: str
    evidence_source: str
    excerpt: str | None
    confidence: float


@dataclass
class ChatResponse:
    question: str
    answer: str
    citations: list[ChatCitation] = field(default_factory=list)
    disclaimer: str = _DISCLAIMER
    incident_found: bool = False


def _sanitize_question(question: str) -> str:
    """Strip ASCII control characters and enforce length cap."""
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", question).strip()
    return cleaned[:_MAX_QUESTION_LEN]


def _score_evidence(evidence: RelationshipEvidence, question_tokens: set[str]) -> float:
    """Return a 0–1 relevance score based on keyword overlap and confidence."""
    text_parts = filter(None, [
        evidence.evidence_excerpt,
        evidence.relationship_type,
        evidence.evidence_type,
    ])
    text = " ".join(text_parts)
    if not text:
        return evidence.confidence
    evidence_tokens = set(normalize_text(text).split())
    overlap = len(question_tokens & evidence_tokens)
    max_possible = max(len(question_tokens), 1)
    keyword_score = min(1.0, overlap / max_possible)
    return (keyword_score + evidence.confidence) / 2.0


def chat_about_evidence(
    db: Session,
    question: str,
    *,
    incident_id: int | None = None,
    case_id: int | None = None,
) -> ChatResponse:
    """Answer a question using stored public evidence records.

    Returns a :class:`ChatResponse` with citations from
    :class:`~app.models.entities.RelationshipEvidence` rows. Returns a
    "no evidence found" response when no matching records exist or when the
    requested incident is not public.

    Args:
        db: Active database session.
        question: Raw natural-language question from the caller.
        incident_id: Optional crime incident primary key. Evidence is only
            returned when ``CrimeIncident.is_public`` is ``True``.
        case_id: Optional court case primary key.
    """
    question = _sanitize_question(question)
    question_tokens = set(normalize_text(question).split())

    conditions = []
    incident_found = False

    if incident_id is not None:
        # Guard: only expose evidence for records the public can already see.
        incident = db.scalar(
            select(CrimeIncident).where(
                CrimeIncident.id == incident_id,
                CrimeIncident.is_public.is_(True),
            )
        )
        if incident is None:
            # Incident does not exist or is not public — return nothing rather
            # than falling through to case_id queries and leaking related data.
            return ChatResponse(
                question=question,
                answer="No public evidence records found for the specified entity.",
                incident_found=False,
            )
        incident_found = True
        conditions.append(
            (RelationshipEvidence.from_entity_type == "crime_incident")
            & (RelationshipEvidence.from_entity_id == incident_id)
        )
        conditions.append(
            (RelationshipEvidence.to_entity_type == "crime_incident")
            & (RelationshipEvidence.to_entity_id == incident_id)
        )

    if case_id is not None:
        conditions.append(
            (RelationshipEvidence.from_entity_type == "court_case")
            & (RelationshipEvidence.from_entity_id == case_id)
        )
        conditions.append(
            (RelationshipEvidence.to_entity_type == "court_case")
            & (RelationshipEvidence.to_entity_id == case_id)
        )

    if not conditions:
        return ChatResponse(
            question=question,
            answer="No public evidence records found for the specified entity.",
            incident_found=incident_found,
        )

    stmt = select(RelationshipEvidence).where(or_(*conditions))
    evidence_rows = list(db.scalars(stmt).all())

    if not evidence_rows:
        return ChatResponse(
            question=question,
            answer="No relationship evidence records are available for this entity.",
            incident_found=incident_found,
        )

    # Rank by relevance to the question.
    scored = sorted(
        evidence_rows,
        key=lambda e: _score_evidence(e, question_tokens),
        reverse=True,
    )
    top = scored[:_MAX_CITATIONS]

    citations = [
        ChatCitation(
            evidence_id=e.id,
            relationship_type=e.relationship_type,
            evidence_type=e.evidence_type,
            evidence_source=e.evidence_source,
            excerpt=e.evidence_excerpt,
            confidence=e.confidence,
        )
        for e in top
    ]

    # Construct a plain-language answer from the top evidence.
    parts: list[str] = [f"Found {len(citations)} evidence record(s) for your query.", "Most relevant:"]
    for i, c in enumerate(citations, 1):
        raw_excerpt = c.excerpt or "(no excerpt)"
        snippet = raw_excerpt[:200] + "\u2026" if len(raw_excerpt) > 200 else raw_excerpt
        parts.append(f"{i}. [{c.relationship_type} / {c.evidence_type}] {snippet}")

    return ChatResponse(
        question=question,
        answer=" ".join(parts),
        citations=citations,
        incident_found=incident_found,
    )
