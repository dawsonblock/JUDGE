> ⚠️ **HISTORICAL ARTIFACT** — represents the codebase state prior to the current truth-hardening session. See [CURRENT_PROOF.md](CURRENT_PROOF.md) for the up-to-date record.

# JUDGE-main 22 — Proof of Work

**Date:** 2026-05-03  
**Base commit:** `04844ea` (JUDGE-main 21)  
**Result commit:** `d13be28` (JUDGE-main 22)  
**Status:** All phases complete; 621 tests pass (0 failures, 2 skipped)

## Proof Metadata

| Field | Value |
|-------|-------|
| Python | 3.12 |
| Node | 20+ |
| OS (local) | macOS |
| OS (CI) | ubuntu-latest |
| Backend command | `cd backend && python -m pytest -q` |
| Backend exit code | 0 |
| Backend result | 621 passed, 2 skipped, 0 failed |
| Frontend command | `npm run lint && npm run typecheck && npm run build` |
| Frontend result | lint pass, typecheck pass, build pass |
| Database (tests) | SQLite (in-memory via `DATABASE_URL=sqlite:///./test.db`) |
| Database (CI) | SQLite only — no PostgreSQL/PostGIS job yet (see postgres-gate roadmap) |
| Test count discrepancy note | 394 in older `docs/REPAIR_PROOF.md` snapshot; 621 reflects post-JUDGE-22 state. Both are accurate for their respective runs. |

---

## Changes Made

### Phase 2 — Evidence-Store Config Coupling

| File | Change |
|------|--------|
| `backend/app/services/snapshot_writer.py` | `os.getenv("JTA_EVIDENCE_STORE_ROOT")` → `get_settings().evidence_store_root` (both `write_snapshot` and `read_snapshot_content`) |
| `backend/app/api/routes/evidence_store.py` | Added `from pathlib import Path`; `/status` endpoint now passes `repo_root=str(Path(__file__).resolve().parents[4])` to `validate_evidence_store_root()` |

**Rationale:** Settings must be read through the canonical `get_settings()` so feature flags, env validation, and test isolation are consistent.

---

### Phase 3 — Stale-Claim Invalidation in `rebuild.py`

| Change | Detail |
|--------|--------|
| New import | `from app.memory.invalidation import invalidate_claim` |
| New module constant | `_HARD_REASONS: frozenset[str] = frozenset({"manual_reject", "source_rejected", "privacy_violation"})` |
| `_upsert_claims()` return type | `tuple[int, int]` → `tuple[int, int, set[str]]`; tracks `produced_keys` (one key per claim that was created or already existed) |
| `run_rebuild()` entity loop | Accumulates `entity_produced_keys`; after processing all snapshots queries active claims for the entity; calls `invalidate_claim(claim.id, "stale_rebuild", db, run.id)` for any claim whose `claim_key` is not in `entity_produced_keys` and whose `invalidation_reason` is not hard-protected |
| `run.claims_invalidated` | Incremented for each stale claim invalidated |

---

### Phase 4 — Circuit-Breaker Error Messages in `admin_ingest.py`

All 7 `raise HTTPException(status_code=403, detail="... disabled")` messages updated to name the env var and mention SourceRegistry:

```
"GDELT global circuit breaker off (set JTA_GDELT_ENABLED=true). Ensure source is also active in SourceRegistry."
"Local feeds circuit breaker off (set JTA_LOCAL_FEEDS_ENABLED=true). Ensure source is also active in SourceRegistry."
"StatsCan global circuit breaker off (set JTA_STATSCAN_ENABLED=true). Ensure source is also active in SourceRegistry."
"FBI Crime global circuit breaker off (set JTA_FBI_CRIME_ENABLED=true). Ensure source is also active in SourceRegistry."
```

---

### Phase 5 — `.env` Files CourtListener Prefix

| File | Change |
|------|--------|
| `.env.example` | Added `JTA_COURTLISTENER_*` prefixed vars with comment explaining Docker Compose remapping; added `JTA_EVIDENCE_STORE_ROOT` comment |
| `.env.example.production` | Added `JTA_COURTLISTENER_API_TOKEN` and `JTA_COURTLISTENER_BASE_URL` alongside unprefixed equivalents |

---

### Phase 6 — Documentation Updates

| File | Change |
|------|--------|
| `docs/MEMORY_INTEGRATION_CONTRACT.md` | Status header updated; stale-claim invalidation checklist item marked `[x]` |
| `docs/PHASES_4_5_6_ROADMAP.md` | Status line updated; §5.1 marked `✅ COMPLETE`; §5.2 updated to reflect JUDGE-22 fix |

---

## Test Results

```
621 passed, 2 skipped, 5 warnings in 4.40s
```

### Test Fixes Applied (JUDGE-22 companion)

| File | Fix |
|------|-----|
| `test_snapshot_writer.py` | Added `from app.core.config import get_settings`; added `autouse` fixture that calls `get_settings.cache_clear()` before/after each test in `TestOversizedWithEvidenceStore`; added `get_settings.cache_clear()` inside each `patch.dict` block so the `lru_cache` sees the overridden env var |
| `test_memory_rebuild.py` | Updated `_upsert_claims` mock returns from 2-tuples to 3-tuples `(n, m, set())`; replaced `db.query.return_value = q` with `db.query.side_effect` that returns an empty-list mock for `MemoryClaim` and the entity mock for `CanonicalEntity` |
| `test_saskatoon_ingest_endpoint.py` | Changed `assert "disabled" in detail.lower()` → `assert "circuit breaker" in detail.lower() or "jta_local_feeds_enabled" in detail.lower()` to match updated circuit-breaker message |

---

## Frontend

```
621 backend tests pass
Lint: 1 pre-existing warning (react-hooks/exhaustive-deps), 0 errors
Typecheck: tsc --noEmit exits 0
Build: next build exits 0
```

---

## Files Changed (production code)

```
backend/app/services/snapshot_writer.py
backend/app/api/routes/evidence_store.py
backend/app/memory/rebuild.py
backend/app/api/routes/admin_ingest.py
.env.example
.env.example.production
docs/MEMORY_INTEGRATION_CONTRACT.md
docs/PHASES_4_5_6_ROADMAP.md
```

## Files Changed (tests)

```
backend/app/tests/test_snapshot_writer.py
backend/app/tests/test_memory_rebuild.py
backend/app/tests/test_saskatoon_ingest_endpoint.py
```
