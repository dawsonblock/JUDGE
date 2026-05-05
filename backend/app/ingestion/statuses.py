"""Canonical ingestion run status constants.

All code that writes to ``IngestionRun.status`` MUST import from here so
that the values stay consistent with the DB column and the admin API
contract.  Do **not** use string literals for status values elsewhere.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Individual status values
# ---------------------------------------------------------------------------

PENDING = "pending"
RUNNING = "running"
COMPLETED = "completed"
COMPLETED_WITH_ERRORS = "completed_with_errors"
FAILED = "failed"
CANCELLED = "cancelled"
QUARANTINED = "quarantined"

# ---------------------------------------------------------------------------
# Convenience sets
# ---------------------------------------------------------------------------

ALL_STATUSES: frozenset[str] = frozenset(
    [PENDING, RUNNING, COMPLETED, COMPLETED_WITH_ERRORS, FAILED, CANCELLED, QUARANTINED]
)

TERMINAL_STATUSES: frozenset[str] = frozenset(
    [COMPLETED, COMPLETED_WITH_ERRORS, FAILED, CANCELLED]
)

# Legacy aliases kept for backward compatibility during the transition period.
# These should not be written to the DB; they exist only so that existing rows
# with old values are still recognised by status-checking code.
_LEGACY_STATUS_MAP: dict[str, str] = {
    "complete": COMPLETED,
    "partial": COMPLETED_WITH_ERRORS,
    "success": COMPLETED,
    "error": FAILED,
}


def normalize_status(raw: str) -> str:
    """Return the canonical form of *raw*, or *raw* unchanged if already canonical."""
    return _LEGACY_STATUS_MAP.get(raw, raw)
