"""Evidence store validation service.

Validates that configured evidence store root exists, is writable,
is not inside the repo, and can handle actual disk I/O.
"""

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Any


def validate_evidence_store_root(
    root: str | None,
    *,
    required: bool,
    probe_write: bool = True,
    repo_root: str | None = None,
) -> dict[str, Any]:
    """Validate evidence store root directory.

    Args:
        root: Path to evidence store root (None = not configured)
        required: If True, raise RuntimeError if not configured or invalid
        probe_write: If True, write/verify/delete probe file to test write access
        repo_root: Path to application repo (used to check root is not inside it)

    Returns:
        {"enabled": bool, "root": str | None, "snapshots_dir": str | None, "reason": str | None}

    Raises:
        RuntimeError: If required=True and root is invalid
    """
    if not root:
        if required:
            raise RuntimeError(
                "JTA_EVIDENCE_STORE_ROOT is required but not configured"
            )
        return {"enabled": False, "root": None, "snapshots_dir": None, "reason": "not_configured"}

    # Resolve path
    path = Path(root).expanduser().resolve()

    # Check existence
    if not path.exists():
        raise RuntimeError(f"Evidence store root does not exist: {path}")

    # Check is directory
    if not path.is_dir():
        raise RuntimeError(f"Evidence store root is not a directory: {path}")

    # Check not inside repo
    if repo_root:
        repo_path = Path(repo_root).resolve()
        try:
            path.relative_to(repo_path)
            # If we got here, path IS inside repo
            raise RuntimeError(
                f"Evidence store root must not be inside the application repo. "
                f"Configured: {path}, Repo: {repo_path}"
            )
        except ValueError:
            # Good: path is not inside repo
            pass

    # Check read/write/execute permissions
    if not os.access(path, os.R_OK | os.W_OK | os.X_OK):
        raise RuntimeError(
            f"Evidence store root is not readable/writable/searchable: {path}"
        )

    # Ensure snapshots directory structure exists
    snapshots_dir = path / "snapshots" / "sha256"
    try:
        snapshots_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise RuntimeError(f"Failed to create snapshots directory: {snapshots_dir}, {e}")

    # Probe write if requested
    if probe_write:
        probe_file = path / ".jta_evidence_store_probe"
        probe_payload = b"judge-atlas-evidence-store-probe"
        probe_hash = hashlib.sha256(probe_payload).hexdigest()

        try:
            # Write
            probe_file.write_bytes(probe_payload)

            # Verify
            read_data = probe_file.read_bytes()
            read_hash = hashlib.sha256(read_data).hexdigest()

            if read_hash != probe_hash:
                raise RuntimeError(
                    f"Evidence store probe hash mismatch. "
                    f"Expected {probe_hash}, got {read_hash}"
                )

            # Clean up
            probe_file.unlink(missing_ok=True)

        except OSError as e:
            raise RuntimeError(f"Evidence store probe write failed: {e}")

    return {
        "enabled": True,
        "root": str(path),
        "snapshots_dir": str(snapshots_dir),
        "reason": None,
    }
