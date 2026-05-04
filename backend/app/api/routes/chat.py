"""AI evidence chat API endpoint.

POST /api/chat/evidence

Returns evidence-backed answers to questions about tracked incidents and cases.
Responses are citation-grounded and include a mandatory legal disclaimer.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.core.rate_limit import rate_limit_public
from app.db.session import get_db
from app.services.evidence_chat import (
    _MAX_QUESTION_LEN,
    ChatCitation,
    chat_about_evidence,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class EvidenceChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(..., min_length=3, max_length=_MAX_QUESTION_LEN)
    incident_id: int | None = Field(None, ge=1)
    case_id: int | None = Field(None, ge=1)

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be blank")
        return v


class CitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_id: int
    relationship_type: str
    evidence_type: str
    evidence_source: str
    excerpt: str | None
    confidence: float


class EvidenceChatResponse(BaseModel):
    question: str
    answer: str
    citations: list[CitationOut]
    disclaimer: str
    incident_found: bool
    safety_notes: list[str] = []
    unsupported_claims: list[str] = []


@router.post(
    "/evidence",
    response_model=EvidenceChatResponse,
    dependencies=[Depends(rate_limit_public)],
)
def post_evidence_chat(
    body: EvidenceChatRequest,
    db: Session = Depends(get_db),
) -> EvidenceChatResponse:
    """Answer a question about stored relationship evidence.

    At least one of ``incident_id`` or ``case_id`` must be supplied. Results
    are drawn exclusively from public evidence records.
    """
    if body.incident_id is None and body.case_id is None:
        raise HTTPException(
            status_code=422,
            detail="At least one of 'incident_id' or 'case_id' must be provided.",
        )

    result = chat_about_evidence(
        db,
        body.question,
        incident_id=body.incident_id,
        case_id=body.case_id,
    )
    return EvidenceChatResponse(
        question=result.question,
        answer=result.answer,
        citations=[
            CitationOut(
                evidence_id=c.evidence_id,
                relationship_type=c.relationship_type,
                evidence_type=c.evidence_type,
                evidence_source=c.evidence_source,
                excerpt=c.excerpt,
                confidence=c.confidence,
            )
            for c in result.citations
        ],
        disclaimer=result.disclaimer,
        incident_found=result.incident_found,
        safety_notes=[],
        unsupported_claims=(
            []
            if result.citations
            else ["No supporting evidence found for this question."]
        ),
    )
