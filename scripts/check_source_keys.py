#!/usr/bin/env python3
"""CI guard: no hardcoded source key strings outside of app/ingestion/source_keys.py.

Scans all .py files under backend/app and fails if any file other than
source_keys.py contains a bare string literal that matches a canonical
source key (e.g. "saskatoon_police", "courtlistener", etc.).

Usage:
    python scripts/check_source_keys.py
    python scripts/check_source_keys.py --root backend/app
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

# These are the canonical source key literals that must not appear hardcoded
# outside of source_keys.py or test files.
_CANONICAL_KEYS = {
    "saskatoon_police",
    "regina_police",
    "winnipeg_police",
    "edmonton_police",
    "calgary_police",
    "vancouver_police",
    "toronto_police",
    "ottawa_police",
    "montreal_police",
    "rcmp",
    "courtlistener",
    "courtlistener_bulk",
    "pacer",
    "csv_import",
    "manual_entry",
    "unknown",
}

_ALLOWED_SUFFIXES = {
    "source_keys.py",
}

_TEST_DIR_PARTS = {"tests", "test"}


def _is_allowed_path(path: Path) -> bool:
    if path.name in _ALLOWED_SUFFIXES:
        return True
    if any(part in _TEST_DIR_PARTS for part in path.parts):
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
            if value in _CANONICAL_KEYS:
                violations.append(f"{py_file}:{lineno}: hardcoded source key {value!r}")
    if violations:
        print(
            "ERROR: hardcoded source key strings detected (use resolve_source_key()):"
        )
        for v in violations:
            print(f"  {v}")
        return 1
    print(f"OK: no hardcoded source key strings in {root}")
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
