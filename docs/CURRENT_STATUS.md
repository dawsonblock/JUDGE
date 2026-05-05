# Judge Atlas - Current Status & Limitations

**Date:** 2026-05-03 (updated post-Phase-10 Canada-first pipeline hardening)  
**Release Status:** **ALPHA - Not Production Ready**

## What This Is

Judge Atlas is a map-first legal & public-record transparency prototype. It shows court events and reported crime incidents as separate layers on a North America map, with strong safety gates to prevent abuse.

- **Core Data Model:** Locations, courts, judges, cases, defendants, events, crimes, source registry, evidence snapshots, review items, audit logs, graph edges, entity linking, AI rule-based classification
- **Backend:** FastAPI, SQLAlchemy ORM, 28 Alembic migrations, PostGIS
- **Frontend:** Next.js, Leaflet, TypeScript, TailwindCSS
- **Map:** North America Leaflet base, event layers, crime aggregates, visibility controls
- **Admin:** Review queue, audit logs, source registry, automated validation (rule-based)

## What Works

- **Core Schema:** Sufficient for long-term goals (entity linking, graph edges, evidence vault, memory derivatives)
- **Public Safety Gates:** Filters by public_visibility=True, approved statuses, non-placeholder locations, safe precision
- **Evidence Layer:** SourceSnapshot stores raw content, hashes, extracted text, storage backend path, truncation flags (ready for external vault)
- **Review System:** All ingested data is pending_review by default; nothing auto-publishes without admin approval
- **Source Registry:** Ingestion sources disabled by default; only active sources execute
- **Audit Logging:** All admin mutations captured with actor, action, entity, payload, request metadata
- **Scheduler:** Background APScheduler is **disabled by default** (`JTA_ENABLE_SCHEDULER=false`); set `JTA_ENABLE_SCHEDULER=true` only in deployments that have active, correctly-seeded source registry entries

## Known Limitations

### 1. Memory System Is Under Active Repair
- Memory tables now exist: `memory_claims`, `memory_entity_states`, `memory_rebuild_runs`,
  `memory_relationship_states`, `memory_evidence_links`, `entity_evidence_links`
- `MemoryClaim.status` lifecycle field ("active"/"inactive") added alongside existing `is_active`
- `invalidate_claim` / `invalidate_entity_state` set both `is_active=False` and `status="inactive"`
- `get_active_claims` filters on both fields (belt-and-suspenders)
- `_get_latest_snapshot_for_entity` scoped to entity via `EntityEvidenceLink` — no cross-entity contamination
- `_upsert_claims` accumulates `MemoryEvidenceLink` rows for existing claims instead of silently skipping
- `run_rebuild()` performs diff-based stale claim invalidation: claims whose key is no longer produced by the current snapshot are marked `is_active=False, status=inactive` before upserting new ones
- Memory is still a derivative layer: no public API, no embeddings, no semantic retrieval
- **Do not claim the app uses production-grade memory**

### 2. Canadian Law Is Stub-Only
- Files: `backend/app/ingestion/laws/canada_*.py`
- Only placeholder law sections; no real Canadian law text ingestion
- Not a blocker for Saskatoon police/crime use case, but Canadian legal context is missing

### 3. AI is Rule-Based, Not True AI
- Files: `backend/app/ai/classify.py`, `redaction.py`, `summarize.py`, `pipeline.py`
- Uses deterministic keyword patterns, redaction rules, and extraction rules
- No LLM, no embeddings, no semantic understanding
- **Marketing label:** Should be "Automated Validation Checks" or "Rule-Based Extraction," not "AI Correctness Engine"

### 4. CourtListener Is Scaffolding, Not Live Ingestion
- Model and bulk normalizer exist
- No turnkey "pull all court decisions" pipeline
- Requires manual source registry enablement, retry handling, admin review workflow
- **Not production-ready for CourtListener live sync**

### 5. Admin Auth Is Shared-Token Alpha
- Single shared token for all admin operations
- No per-user identity, no roles, no OAuth/OIDC, no MFA, no session management
- Audit logs show actor="shared-admin-token"
- **Not acceptable for public deployment**

### 6. Proof System Has Known Bug
- `scripts/proof_all.sh` uses `DATABASE_URL` instead of `JTA_DATABASE_URL`
- Alembic reads `JTA_DATABASE_URL`, so migration proof may not test intended database
- Proof artifacts are from 19 migrations; repo now has 28
- **Fixed in recent commit**

### 7. Crawlee Web Monitor Is Alpha
- Crawlee runner was updated to use review_required instead of invalid "hold" status
- Confidence capped at 0.5
- All crawled content starts as pending_review
- Test coverage added but not yet full

### 8. Docker Compose Admin Defaults Were Unsafe
- Previously hardcoded dev tokens and enabled admin endpoints by default
- **Fixed in recent commit:** admin endpoints now disabled by default, tokens must come from .env

### 9. Redis Rate Limiter Has Fallback
- Can fall back to in-memory rate limiter if Redis unavailable
- In production, this should fail closed
- **Fixed in recent commit:** production startup checks Redis availability

## Migration Status

**Total Migrations:** 28 (as of 2026-05-02 repair)

Recent migrations (Phase 4-6 repair):
- `20260502_0005_add_memory_tables.py` — core memory tables
- `20260502_0006_add_entity_evidence_links.py` — `entity_evidence_links` table (scopes rebuild to entity)
- `20260502_0007_add_memory_claim_lifecycle.py` — `status` + `last_seen_at` columns on `memory_claims`

**Proof Status:** `alembic heads` now verified to return exactly one head (checked by `test_alembic_heads.py` and `alembic_single_head` step in `proof_all.sh`). Run `bash scripts/proof_all.sh` to verify full migration chain.

## What Is Safe

- **Public Map Endpoints:** Filter rigorously; filter by public_visibility=True, approved review status, non-placeholder coordinates
- **Source Snapshots:** Do not auto-publish; stored with integrity (hash, truncation flags, storage backend metadata)
- **Evidence Vault Design:** Ready for external storage at JTA_EVIDENCE_STORE_ROOT; snapshot_writer refuses silent truncation
- **Review Queue:** All ingested data mandatory for human review before public visibility
- **Audit Trail:** All admin mutations logged with actor, action, entity, timestamp, request metadata

## What Is Not Safe

- **Shared-Token Admin Auth:** No per-user identity; not suitable for multi-person teams or public internet
- **CourtListener Live Sync:** Not yet production-grade retry pipeline or admin UI integration
- **Dev Tokens in Production:** Must use secure random tokens; no "change-in-production" markers allowed
- **Wildcard CORS:** Startup validation now rejects wildcard origins in production
- **Redis Fallback:** Startup validation now fails if Redis is required but unavailable

## Next Repair Order

### Phase 0 (Status Documentation)
- [x] Update this file with true current status

### Phase 1 (Fix Proof System)
- [x] Patch `scripts/proof_all.sh` to use `JTA_DATABASE_URL`
- [ ] Run clean proof command on current state
- [ ] Verify all 36 migrations pass

### Phase 2 (Crawlee Safety)
- [x] Fix publish_recommendation ("hold" → "review_required")
- [x] Add test coverage for Crawlee safety defaults
- [x] Production startup checks added

### Phase 3 (Production Safety)
- [x] Disable admin endpoints by default in docker-compose.yml
- [x] Require explicit token configuration in .env
- [x] Startup validation: fail if tokens missing, dev tokens detected, wildcard CORS, Redis unavailable

### Phase 4 (Source Registry)
- [x] Source registry `is_active` defaults to `False` — fail-closed by default
- [x] All 11 admin ingestion routes call `_check_source_active` before running ingestion
- [x] `require_source_registry` auto-creates disabled entry when source key unknown
- [x] `test_source_gate.py` added: verifies disabled source → HTTP 403; enabled → no gate 403
- [x] Admin UI controls to enable/disable sources (`/admin/sources` page in frontend)

### Phase 5 (Evidence Vault)
- [x] `GET /api/admin/evidence-store/verify/{snapshot_id}` endpoint added
- [x] Computes SHA-256 of stored content, compares with `original_content_hash`
- [x] Returns `{"status": "ok"|"corrupted"|"unavailable", "stored_hash", "actual_hash", ...}`
- [x] `test_snapshot_verify.py` added: covers ok / corrupted / unavailable / 404 / auth required
- [ ] Configure `JTA_EVIDENCE_STORE_ROOT` for external drive storage

### Phase 6 (Fluid Memory)
- [x] `MemoryRelationshipState` ORM + migration
- [x] `EntityEvidenceLink` ORM + migration (scopes snapshot queries to entity)
- [x] `_get_latest_snapshot_for_entity` now scoped via `EntityEvidenceLink` join
- [x] `_upsert_claims` accumulates `MemoryEvidenceLink` for existing claims (no silent skip)
- [x] `MemoryClaim.status` lifecycle field + `last_seen_at` + migration
- [x] `invalidate_claim` / `invalidate_entity_state` set `status="inactive"`
- [x] `get_active_claims` filters both `is_active` and `status == "active"`
- [x] `test_memory_rebuild_accumulation.py` + `test_memory_claim_lifecycle.py` added
- [ ] Embeddings, summaries, semantic retrieval — not yet implemented

### Phase 7 (Correctness Patches)
- [x] `EvidenceStore.__init__` raises `RuntimeError` on non-existent/non-directory/non-writable path instead of silently disabling
- [x] `EvidenceStore.write_snapshot` asserts file exists and is non-zero after write
- [x] `snapshots.py GET /api/admin/snapshots/{id}/raw` hashes raw bytes (not base64 wrapper); returns 409 on mismatch; sets `encoding="base64"` correctly
- [x] `map_record.py` detail endpoints expose top-level `review_status`, `source_quality`/`verification_status`, `source_count` alongside nested `audit` dict
- [x] `_replace_known_defendant_names` uses word-boundary case-insensitive regex instead of `str.replace` (prevents partial-name leakage)
- [x] `memory/rebuild.py` invalidates stale claims before upserting: keys absent from current extracted set are marked inactive
- [x] `test_evidence_store.py` updated; `test_source_registry_control_plane.py` extended with runner-level block test

### Phase 9 (Auto-Ingest Scheduler + Frontend Live API)
- [x] `apscheduler>=3.10.0` added to backend dependencies
- [x] `backend/app/workers/scheduler.py` — `build_scheduler(db_factory)` builds one `IntervalTrigger` APScheduler job per active, non-manual `SourceRegistry` row that has a matching `WebMonitorTarget`
- [x] Scheduler wired into FastAPI `lifespan` context manager (`scheduler.start()` / `scheduler.shutdown(wait=False)`)
- [x] `_run_source_job` catches all exceptions; scheduled job failure doesn't crash the server
- [x] `frontend/lib/api.ts` extended: `ChatCitation`, `ChatResponse` types; `fetchCrimeIncidents()` and `chatAboutEvidence()` helpers
- [x] `frontend/components/crime-map/CrimeMapWorkspace.tsx` — replaced mock data with live `GET /api/map/crime-incidents` via `fetchCrimeIncidents()` + feature-to-domain mapper
- [x] `frontend/components/crime-map/EvidenceChatPanel.tsx` — new evidence chat UI panel (128 lines); calls `POST /api/chat/evidence`; renders answer + citations
- [x] `backend/app/tests/test_scheduler.py` — 23 unit tests covering `_TARGET_BY_SOURCE_KEY`, `build_scheduler`, `_run_source_job`; 720 total tests collected

### Phase 8 (JUDGE-main 19 — Canada-First Safety Patches)
- [x] `resolve_publication_policy()` added to `publish_rules.py` — SourceRegistry is now THE authority; fail-closed (TIER_HOLD) if source missing/inactive/review-required
- [x] `persist_crime_incident` accepts `source_key` and calls registry-aware policy post-block
- [x] Source registry seed fully normalized: canonical `source_tier` values (`official_police_open_data`, `official_government_statistics`, `court_record`, `news_only_context`)
- [x] `saskatoon_crime.is_active` tied to dev env var (`JTA_CANADA_FIRST_DEV_ENABLE_SASKATOON`); off by default in production
- [x] `courtlistener` and `courtlistener_bulk` now have `requires_manual_review=True`
- [x] `seed_source_registry` decoupled from sample data; runs independently with `seed_source_registry: bool = True` config gate (prod-safe, defaults on)
- [x] `fetch_statscan_csv` now extracts CSV from ZIP response via `extract_csv_from_response()` — fixes silent garbage-text bug when StatsCan serves a ZIP archive
- [x] `EvidenceStore.read_snapshot` and `delete_snapshot` now guard against path traversal with `.resolve()` + `.is_relative_to()`
- [x] Saskatchewan law stub tests extended: `test_fetch_correctional_services` and `test_fetch_victims_of_crime` now assert `all(s.is_stub for s in sections)`

### Phase 10 (Canada-First Pipeline Hardening)
- [x] `resolve_publication_policy()` now passes `registry=registry` to `source_tier()` — registry can promote via `TIER_AUTO`; previously this arg was silently dropped, causing a bypass
- [x] `saskatoon.py` — reads all CSV content upfront, computes SHA-256 `import_batch_hash`, passes it through to `persist_crime_incident()`; Gate 0b quarantine cleared
- [x] `statscan.py` — replaces peek-and-seek ZIP detection with read-all-upfront pattern; computes `import_batch_hash` for binary and text paths; passes hash to `persist_crime_incident()`
- [x] `crawlee_runner.py` — replaced brittle `if/elif` action chain with `_ACTION_MAP` dispatch dict; unknown actions default to `review_required/pending` (fail-closed)
- [x] `test_seed_repair.py` — fixed stale tests that asserted on `requires_manual_review`/`auto_publish_enabled` (which are excluded from `_REPAIR_FIELDS`); now deviate and assert on `source_tier`; added `test_operational_flags_not_reset_by_repair` to prove admin-set flags survive repair
- [x] `config.py` — `enable_scheduler: bool = False` added; env var `JTA_ENABLE_SCHEDULER`; scheduler is **off by default** for safe cold deploys
- [x] `main.py` — scheduler start/stop gated behind `settings.enable_scheduler`; `scheduler = None` when disabled; `if scheduler is not None: scheduler.shutdown()`
- [x] `test_scheduler.py` — `TestSchedulerLifespanGate` class added: verifies `build_scheduler` is not called when disabled, and is called when enabled
- [x] `entities.py RelationshipEvidence` — 4 new columns: `public_visibility` (bool, default false), `verification_status` (str|None), `relationship_status` (str|None, default pending), `auto_publish_reason` (str|None)
- [x] Migration `20260503_0002_add_relationship_evidence_visibility.py` — adds 4 columns to `relationship_evidence` table; reversible
- [x] `evidence_chat.py` — case guard: verifies ≥1 public `CrimeIncident` linked to `case_id` via `CrimeIncidentEventLink`→`Event` before surfacing evidence; visibility filter: `public_visibility IS TRUE`; confidence floor: `confidence >= 0.25`
- [x] `frontend/app/map/page.tsx` — replaced `CrimeMapWorkspace` import with `JudgeNorthAmericaMapClient`
- [x] `frontend/components/map/MapRecordDrawer.tsx` — added `"evidence"` tab type; `EvidenceChatPanel` tab shown for incident records

## Do Not Yet Claim

- [ ] "Production-ready" — Alpha only
- [ ] "AI-powered" — Rule-based extraction only
- [ ] "Uses memory" — Contract defined, not implemented
- [ ] "Complete Canadian law coverage" — Stubs only
- [ ] "Live CourtListener sync" — Scaffolding only
- [ ] "Enterprise authentication" — Shared-token alpha only
- [ ] "Auto-publish pipeline" — All evidence requires `public_visibility=True` AND `confidence >= 0.25` AND human review; no record auto-publishes without those gates

## Do Claim

- [x] "Open-source legal transparency research prototype"
- [x] "Map-first, review-first, fail-closed design"
- [x] "Strong source-first and evidence-first commitment"
- [x] "No evidence surfaces without public_visibility=True, confidence ≥ 0.25, and a public linked incident"
- [x] "Background scheduler disabled by default — requires JTA_ENABLE_SCHEDULER=true to activate"
- [x] "All admin mutations audited"
- [x] "Source registry is fail-closed: new sources start disabled"
- [x] "Memory rebuilds scoped per-entity via EntityEvidenceLink"

## Phase 11 (Ingestion Architecture Hardening)
- [x] `app/ingestion/statuses.py` — canonical status constants (`PENDING`, `RUNNING`, `COMPLETED`, `COMPLETED_WITH_ERRORS`, `FAILED`, `CANCELLED`, `QUARANTINED`); `normalize_status()`; replaces all bare string literals in `admin_sources.py` and `ingestion_log.py`
- [x] `app/ingestion/source_keys.py` — 16 canonical source key constants + `COURTLISTENER_BULK` + `LEGACY_SOURCE_ALIASES` + `resolve_source_key()` + `is_canonical_source_key()`; `admin_ingest.py` updated to use `resolve_source_key()`
- [x] `app/ingestion/external_id.py` — `make_external_id(source_key, raw_id)` and `split_external_id(external_id)` for stable `source_key:raw_id` compound IDs
- [x] `app/ingestion/normalization.py` — `parse_datetime_safe()` (8 common date formats, UTC-naïve handling) and `normalize_coordinates()` (bounds validation, zero-island guard)
- [x] `app/ingestion/normalized.py` — `NormalizedIncident` frozen dataclass (17 fields); `to_payload()` serializes datetimes to ISO strings
- [x] `app/ingestion/publish_rules.py` — `PublicationDecision` frozen dataclass (typed gate result); `evaluate_publication_policy()` bridges ingestion layer to `app.services.publish_rules.is_publishable()`; re-exports `UNSAFE_MAP_PRECISIONS`
- [x] `app/ingestion/source_adapters/saskatoon_csv.py` — precision bug fixed: `"exact"` → `"neighbourhood_centroid"`; uses `make_external_id()` for all ID construction
- [x] `frontend/lib/sourceContracts.ts` — `PublicRecordAuthority` and `SourceTier` types, colour helpers; used in `admin/sources/page.tsx`
- [x] `app/api/routes/map.py` — `selectinload(CrimeIncident.source_links).selectinload(CrimeIncidentSource.source)` and `selectinload(CrimeIncident.event_links)` added to both crime-incident query endpoints; eliminates N+1 lazy loading
- [x] `scripts/check_source_keys.py` — CI guard: fails if canonical source key strings appear hardcoded outside `source_keys.py` or test files
- [x] `scripts/check_statuses.py` — CI guard: fails if canonical ingestion status strings appear hardcoded outside `statuses.py`, `alembic/`, or test files
- [x] `app/tests/test_ingestion_statuses.py` — 9 tests covering all status constants, `TERMINAL_STATUSES`, `ALL_STATUSES`, `normalize_status()`
- [x] `app/tests/test_source_keys.py` — 9 tests covering constants, `resolve_source_key()`, `is_canonical_source_key()`, legacy alias resolution
- [x] "Snapshot integrity verifiable via /verify endpoint"
- [x] "Ready for local development and research"

---

**Maintainer Note:**  
This app is the best version of Judge Atlas foundation so far as an alpha. The schema is correct, the safety spine is strong, and the next moves are clear. Do not call it production-ready yet. Do not expose admin endpoints publicly with dev tokens. Do complete the source registry UI, evidence vault, and memory layer before expanding to multi-user or public deployment.
