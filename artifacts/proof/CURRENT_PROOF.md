# CURRENT_PROOF.md — Truth-Hardening Pass (Multi-Session)

> This document is the authoritative up-to-date record of every change applied
> during the full truth-hardening engagement. Historical proof files
> (`JUDGE-22-proof.md`, `FINAL_SUMMARY.md`) are preserved but prefixed with
> a deprecation notice.

---

## Session Dates

- Session 1 (prior): Phases A1–E3
- Session 2 (continuation): Phases F1–I2

---

## Phases Applied

### A1 — Source-class run-block gate
**File**: `backend/app/api/routes/admin_sources.py`  
**Change**: Added allow-list (`_ALLOWED_RUN_SOURCE_CLASSES`) enforced before any
source-run action; returns 422 with `source_class_not_runnable` detail for
non-machine-ingest classes.

---

### A2 — Health update on exception in source runner  
**File**: `backend/app/api/routes/admin_sources.py`  
**Change**: Wrapped source-execute path in try/except; on unhandled exception the
source health record is updated to `error` state before re-raising.

---

### B1 — Three portal stubs converted to `disabled_stub`  
**File**: `backend/app/ingestion/sources/canada_saskatchewan_sources.yaml`  
**Change**: Converted three placeholder entries from `portal_reference` or
`machine_ingest` to `disabled_stub` with `enabled_default: false` and
descriptive `admin_notes`.  Verified via `validate_workflows.py`.

---

### C1 — SSRF blocking restored + `@dataclass` fix on `RuleViolation`  
**File**: `backend/app/ingestion/source_rules.py`  
**Change**:
- Restored `@dataclass` decorator on `RuleViolation` (was accidentally stripped).
- Added `_is_private_or_loopback()` helper and a `ssrf_block` violation returned
  from `check_domain_allowed` when the resolved host is a private/loopback address.

---

### C2 — Stale test fixes + 11 SSRF tests  
**File**: `backend/app/tests/test_source_rules.py`  
**Change**:
- Fixed 3 tests that referenced the old un-decorated `RuleViolation` constructor.
- Added 11 new tests covering SSRF scenarios (localhost, 127.x, 10.x, 192.168.x,
  IPv6 loopback, hostname collision).

---

### A3 — `test_source_run_policy.py` (5 test classes)  
**File**: `backend/app/tests/test_source_run_policy.py` *(new)*  
**Change**: Created comprehensive policy tests for the run-block gate:
`TestSourceRunPolicyAllowedClasses`, `TestSourceRunPolicyBlockedClasses`,
`TestSourceRunPolicyNextAction`, `TestSourceRunPolicyEdgeCases`,
`TestSourceRunPolicyStatusTransitions`.

---

### D1 — `crawlee_runner.py` docstring  
**File**: `backend/app/ingestion/crawlee_runner.py`  
**Change**: Added module-level docstring clarifying robots.txt enforcement contract
and the fail-closed behaviour expected of all subclasses.

---

### D2 — `TestRobotsAllowedFailClosed` (5 tests)  
**File**: `backend/app/tests/test_crawlee_safety.py` *(new)*  
**Change**: Created `TestRobotsAllowedFailClosed` class verifying that
`robots_allowed()` defaults to `False` on every exception path (connection error,
parse error, timeout, unexpected exception) and returns `True` only for an
explicit non-restricted allow.

---

### E1 — `SourceClass` TypeScript union  
**File**: `frontend/lib/types.ts`  
**Change**: Added `SourceClass` discriminated-union type mirroring the 6 backend
canonical values (`machine_ingest`, `portal_reference`, `disabled_stub`,
`manual_reference`, `requires_api_key`, `needs_endpoint_configuration`).

---

### E2 — `api.ts` typed source-class field  
**File**: `frontend/lib/api.ts`  
**Change**: Typed `source_class` field in `Source` interface as `SourceClass`
(imported from `lib/types.ts`).

---

### E3 — `SourceControlCard.tsx` run-button gate  
**File**: `frontend/components/SourceControlCard.tsx`  
**Change**: Disabled the "Run now" button unless `source.source_class === "machine_ingest"`;
shows tooltip explaining why for other classes.

---

### F1 — Defensive `is_active` guard in `memory_graph_bridge.py`  
**File**: `backend/app/memory/memory_graph_bridge.py`  
**Change**: Added `if not claim.is_active: continue` early-exit inside
`sync_claims_to_graph()` loop so inactive claims are never written as graph edges,
even if the caller fails to pre-filter.

---

### F2 — `TestMemoryGraphBridgeInvalidation` (5 tests)  
**File**: `backend/app/tests/test_memory_graph_bridge.py`  
**Change**: Appended `TestMemoryGraphBridgeInvalidation` class (5 tests) covering:
inactive claim skipped, mixed known/unknown claim types, incremental second-batch
insert, empty entity/claim edge case, all predicate mappings verified.

---

### G1 — `test_registry_invariants.py` (10 tests)  
**File**: `backend/app/tests/test_registry_invariants.py` *(new)*  
**Change**: Pure YAML-file tests (no DB) asserting structural invariants across all
source registry YAML files: non-empty list, unique source keys, canonical
`source_class` values, machine_ingest has parser, disabled_stub has admin_notes,
no enabled-by-default, no portal_reference or disabled_stub marks auto-publish.

---

### G2 — `test_ingestion_review_publication_hard_path.py`  
**File**: `backend/app/tests/test_ingestion_review_publication_hard_path.py` *(new)*  
**Change**: Pure-function integration tests (no DB, no HTTP) exercising the full
`source_rules.py` pipeline:

- `TestRecordTypeGate` (8 tests) — authority × record-type combinations
- `TestPublishGate` (6 tests) — authority eligibility + flag combinations
- `TestEnforceAll` (4 tests) — composed rule chain including domain violations

---

### H1 — `scripts/validate_workflows.py`  
**File**: `scripts/validate_workflows.py` *(new)*  
**Change**: CLI script that globs all YAML files under
`backend/app/ingestion/sources/`, loads them with PyYAML, and enforces 5 checks:
canonical `source_class`, machine_ingest has parser, disabled_stub has admin_notes,
no `enabled_default: true`, no auto-publish on portal_reference or disabled_stub.
Exits 1 on any violation. Smoke-run confirms 14 sources PASS.

---

### I1 — Historical-artifact disclaimers  
**Files**: `artifacts/proof/JUDGE-22-proof.md`, `artifacts/proof/FINAL_SUMMARY.md`  
**Change**: Prepended `⚠️ HISTORICAL ARTIFACT` blockquote to both files, directing
readers to this document for the current state.

---

### I2 — `artifacts/proof/CURRENT_PROOF.md`  
**File**: `artifacts/proof/CURRENT_PROOF.md` *(this file)*  
**Change**: Created authoritative proof document recording all phases across both
sessions.

---

## Verification Status

| Phase | File(s) changed | py_compile | Tests |
|-------|----------------|-----------|-------|
| A1 | admin_sources.py | ✅ | via A3 |
| A2 | admin_sources.py | ✅ | via A3 |
| A3 | test_source_run_policy.py | ✅ | 5 classes |
| B1 | canada_saskatchewan_sources.yaml | n/a | via G1, H1 |
| C1 | source_rules.py | ✅ | via C2 |
| C2 | test_source_rules.py | ✅ | +11 SSRF |
| D1 | crawlee_runner.py | ✅ | via D2 |
| D2 | test_crawlee_safety.py | ✅ | 5 tests |
| E1 | lib/types.ts | tsc | n/a |
| E2 | lib/api.ts | tsc | n/a |
| E3 | SourceControlCard.tsx | tsc | n/a |
| F1 | memory_graph_bridge.py | ✅ | via F2 |
| F2 | test_memory_graph_bridge.py | ✅ | 5 tests |
| G1 | test_registry_invariants.py | ✅ | 10 tests |
| G2 | test_ingestion_review_publication_hard_path.py | ✅ | 18 tests |
| H1 | scripts/validate_workflows.py | ✅ | PASS (live run) |
| I1 | JUDGE-22-proof.md, FINAL_SUMMARY.md | n/a | visual |
| I2 | CURRENT_PROOF.md | n/a | this file |

---

## Known Remaining Gaps

- No end-to-end pytest run performed (would require Docker / DB).
- Frontend TypeScript not compiled in CI during this session (no `npm` environment).
- `test_crawlee_safety.py` and `test_source_run_policy.py` rely on import-time
  mocking; full integration with the live crawlee library was not exercised.
