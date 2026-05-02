"""Canonical snapshot writer service for source snapshots.

This service provides a unified interface for writing source snapshots,
supporting both filesystem storage (via EvidenceStore) and database fallback.
All snapshot writes should go through this service to ensure consistency.

Evidence integrity contract:
- The hash stored in content_hash / original_content_hash is ALWAYS the hash
  of the FULL, un-truncated content.
- stored_content_hash is the hash of what is actually stored; it MUST equal
  original_content_hash on every successful write.
- is_truncated MUST always be False after a successful write.
- If content is too large for DB storage and no evidence store is configured,
  write_snapshot() raises ValueError rather than creating a partial snapshot.
"""

import hashlib
import json
import os
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.models.entities import SourceSnapshot
from app.services.evidence_store import EvidenceStore

if TYPE_CHECKING:
    pass


# Maximum size for DB storage (1MB)
MAX_DB_SIZE = 1024 * 1024


def write_snapshot(
    db: Session,
    source_url: str,
    fetched_at: datetime,
    content: bytes | str,
    extracted_text: str | None = None,
    headers: dict | None = None,
    http_status: int | None = None,
    content_type: str | None = None,
    error_message: str | None = None,
    ingestion_run_id: int | None = None,
    extractor_name: str | None = None,
    extractor_version: str | None = None,
) -> SourceSnapshot:
    """Write a source snapshot using canonical storage logic.

    Evidence integrity: stored content always matches the stored hash.
    If content is too large for DB and no evidence store is configured,
    raises ValueError rather than creating a partial snapshot.

    Args:
        db: Database session
        source_url: URL of the source
        fetched_at: Timestamp when content was fetched
        content: Raw content as bytes or string
        extracted_text: Extracted plain text (optional)
        headers: HTTP headers dict (optional)
        http_status: HTTP status code (optional)
        content_type: Content-Type header (optional)
        error_message: Error message if fetch failed (optional)
        ingestion_run_id: ID of the ingestion run that created this snapshot (optional)
        extractor_name: Name of the text extractor used (optional)
        extractor_version: Version of the text extractor used (optional)

    Returns:
        SourceSnapshot: Created snapshot record (not yet committed)

    Raises:
        ValueError: If content exceeds MAX_DB_SIZE and no evidence store is configured.
    """
    # Convert content to bytes if needed
    if isinstance(content, str):
        content_bytes = content.encode("utf-8")
        content_text = content
    else:
        content_bytes = content
        content_text = content.decode("utf-8", errors="replace")

    # Compute SHA256 hash of full original content
    original_hash = hashlib.sha256(content_bytes).hexdigest()
    content_size = len(content_bytes)

    # Determine storage backend
    evidence_root = os.getenv("JTA_EVIDENCE_STORE_ROOT")

    if content_size <= MAX_DB_SIZE:
        # Content fits in DB — store directly, hashes match by definition
        storage_backend = "db"
        storage_path = None
        raw_content = content_text
        stored_hash = original_hash
        stored_size = content_size
    elif evidence_root:
        # Content is large; try filesystem evidence store
        evidence_store = EvidenceStore(root_path=evidence_root)
        storage_path = evidence_store.write_snapshot(content_bytes, original_hash)
        storage_backend = "filesystem"
        raw_content = None  # Don't duplicate in DB
        stored_hash = original_hash
        stored_size = content_size
    else:
        # Content too large and no evidence store — refuse to create partial snapshot
        raise ValueError(
            f"Content size {content_size} bytes exceeds MAX_DB_SIZE ({MAX_DB_SIZE}) "
            "and JTA_EVIDENCE_STORE_ROOT is not configured. "
            "Configure an evidence store to handle large content, or ensure the "
            "fetcher enforces a size limit before calling write_snapshot()."
        )

    # Create SourceSnapshot with full integrity metadata
    snapshot = SourceSnapshot(
        source_url=source_url,
        fetched_at=fetched_at,
        content_hash=original_hash,
        raw_content=raw_content,
        extracted_text=extracted_text,
        http_status=http_status,
        content_type=content_type,
        headers_json=json.dumps(headers) if headers else None,
        error_message=error_message,
        storage_backend=storage_backend,
        storage_path=storage_path,
        ingestion_run_id=ingestion_run_id,
        # Evidence integrity fields
        original_content_hash=original_hash,
        stored_content_hash=stored_hash,
        content_size_bytes=content_size,
        stored_size_bytes=stored_size,
        is_truncated=False,
        extractor_name=extractor_name,
        extractor_version=extractor_version,
    )

    db.add(snapshot)
    # Caller is responsible for commit/refresh

    return snapshot


def read_snapshot_content(db: Session, snapshot: SourceSnapshot) -> bytes | None:
    """Read snapshot content from appropriate storage backend.

    Args:
        db: Database session
        snapshot: SourceSnapshot record

    Returns:
        Raw content as bytes, or None if unavailable
    """
    if snapshot.storage_backend == "filesystem" and snapshot.storage_path:
        try:
            evidence_root = os.getenv("JTA_EVIDENCE_STORE_ROOT")
            if evidence_root:
                evidence_store = EvidenceStore(root_path=evidence_root)
                return evidence_store.read_snapshot(snapshot.storage_path)
        except Exception:
            # Fall through to DB fallback
            pass

    # DB fallback
    if snapshot.raw_content:
        return snapshot.raw_content.encode("utf-8")

    return None

