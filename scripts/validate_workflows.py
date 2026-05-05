#!/usr/bin/env python3
"""Validate all source YAML workflow files in backend/app/ingestion/sources/.

Checks enforced:
  1. All source_class values are in the canonical set
  2. Every machine_ingest source has a parser field
  3. Every disabled_stub source has an admin_notes field
  4. No source has enabled_default: true
  5. No portal_reference or disabled_stub has auto_publish_enabled: true

Exit code: 0 if all checks pass, 1 if any violation is found.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SOURCES_DIR = _REPO_ROOT / "backend" / "app" / "ingestion" / "sources"

_CANONICAL_CLASSES = frozenset(
    {
        "machine_ingest",
        "portal_reference",
        "disabled_stub",
        "manual_reference",
        "requires_api_key",
        "needs_endpoint_configuration",
    }
)

_NO_AUTO_PUBLISH = frozenset({"portal_reference", "disabled_stub"})


def _load_all_sources() -> list[dict]:
    """Return every source entry from every YAML file in _SOURCES_DIR."""
    entries: list[dict] = []
    for path in sorted(_SOURCES_DIR.glob("*.yaml")):
        with path.open() as fh:
            data = yaml.safe_load(fh) or {}
        sources = data.get("sources") or data.get("source_list") or []
        if isinstance(sources, list):
            for s in sources:
                if isinstance(s, dict):
                    s["_file"] = path.name
                    entries.append(s)
    return entries


def main() -> int:
    yaml_files = list(_SOURCES_DIR.glob("*.yaml"))
    if not yaml_files:
        print(f"FAIL  No YAML files found in {_SOURCES_DIR}")
        return 1

    sources = _load_all_sources()
    if not sources:
        print(f"FAIL  No source entries loaded from {len(yaml_files)} file(s)")
        return 1

    violations: list[str] = []

    for s in sources:
        key = s.get("source_key") or f"<unnamed in {s.get('_file')}>"
        sc = s.get("source_class")

        # 1. Canonical source_class
        if sc not in _CANONICAL_CLASSES:
            violations.append(
                f"{key}: unrecognised source_class {sc!r} "
                f"(not in {sorted(_CANONICAL_CLASSES)})"
            )

        # 2. machine_ingest must have parser
        if sc == "machine_ingest" and not s.get("parser"):
            violations.append(f"{key}: machine_ingest missing 'parser' field")

        # 3. disabled_stub must have admin_notes
        if sc == "disabled_stub" and not s.get("admin_notes"):
            violations.append(f"{key}: disabled_stub missing 'admin_notes' field")

        # 4. enabled_default must not be True
        if s.get("enabled_default") is True:
            violations.append(
                f"{key}: enabled_default is True (sources must default to disabled)"
            )

        # 5. portal_reference / disabled_stub must not auto-publish
        if sc in _NO_AUTO_PUBLISH and s.get("auto_publish_enabled") is True:
            violations.append(f"{key}: {sc} must not have auto_publish_enabled: true")

    if violations:
        print(f"FAIL  {len(violations)} violation(s) detected:\n")
        for v in violations:
            print(f"  - {v}")
        return 1

    n = len(sources)
    print(f"PASS  {n} source(s) across {len(yaml_files)} file(s) validated OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
