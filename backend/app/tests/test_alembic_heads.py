"""Tests that the Alembic migration chain has exactly one head.

A branched migration chain causes `alembic upgrade head` to fail in CI and
`alembic_single_head` step in proof_all.sh to catch it. This test is the
in-process equivalent so it can fail fast in pytest before the shell proof runs.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent.parent  # backend/


def _run_alembic(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        capture_output=True,
        text=True,
        cwd=BACKEND_DIR,
    )


def test_single_alembic_head() -> None:
    """alembic heads must list exactly one (head) revision."""
    result = _run_alembic(["heads"])
    assert (
        result.returncode == 0
    ), f"alembic heads failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    head_lines = [line for line in result.stdout.splitlines() if "(head)" in line]
    assert (
        len(head_lines) == 1
    ), f"Expected exactly 1 alembic head, got {len(head_lines)}:\n{result.stdout}"


def test_latest_migration_is_0009() -> None:
    """The single head revision must be 20260504_0002 (latest migration)."""
    result = _run_alembic(["heads"])
    assert result.returncode == 0
    head_lines = [line for line in result.stdout.splitlines() if "(head)" in line]
    assert len(head_lines) == 1
    assert (
        "20260504_0002" in head_lines[0]
    ), f"Expected head to be 20260504_0002, got:\n{head_lines[0]}"


def test_alembic_history_parses() -> None:
    """alembic history must exit 0 and list known migrations."""
    result = _run_alembic(["history", "--verbose"])
    assert (
        result.returncode == 0
    ), f"alembic history failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    # Spot check a few revision ids
    for rev in ("20260502_0009", "20260502_0006", "20260502_0005"):
        assert rev in result.stdout, f"Missing revision {rev} in alembic history"
