#!/usr/bin/env python3
"""CI guard: no hardcoded ingestion status strings outside of app/ingestion/statuses.py.

Scans all .py files under backend/app and fails if any file other than
statuses.py contains a bare string literal matching a canonical status value
("pending", "running", "completed", "completed_with_errors", "failed",
"cancelled", "quarantined").

Usage:
    python scripts/check_statuses.py
    python scripts/check_statuses.py --root backend/app
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

_STATUS_LITERALS = {
    "pending",
    "running",
    "completed",
    "completed_with_errors",
    "failed",
    "cancelled",
    "quarantined",
}

_ALLOWED_SUFFIXES = {
    "statuses.py",
}

_TEST_DIR_PARTS = {"tests", "test"}

# Alembic migration files define schema defaults — allow them.
_ALEMBIC_DIR_PARTS = {"alembic", "versions"}


def _is_allowed_path(path: Path) -> bool:
    if path.name in _ALLOWED_SUFFIXES:
        return True
    if any(part in _TEST_DIR_PARTS for part in path.parts):
        return True
    if any(part in _ALEMBIC_DIR_PARTS for part in path.parts):
        return True
    return False


def _string_literals(tree: ast.AST) -> list[tuple[int, str]]:
    results: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            results.append((node.lineno, node.value))
    return results


def check(root: Path) -> int:
    violations: list[str] = []
    for py_file in root.rglob("*.py"):
        if _is_allowed_path(py_file):
            continue
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError:
            continue
        for lineno, value in _string_literals(tree):
            if value in _STATUS_LITERALS:
                violations.append(
                    f"{py_file}:{lineno}: hardcoded status literal {value!r}"
                    " (import from app.ingestion.statuses)"
                )
    if violations:
        print("ERROR: hardcoded ingestion status strings detected:")
        for v in violations:
            print(f"  {v}")
        return 1
    print(f"OK: no hardcoded ingestion status strings in {root}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default="backend/app",
        help="Directory to scan (default: backend/app)",
    )
    args = parser.parse_args()
    root = Path(args.root)
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        sys.exit(2)
    sys.exit(check(root))


if __name__ == "__main__":
    main()
