# Judge Atlas - Current Status & Limitations

**Date:** 2026-05-03 (updated post-JUDGE-main-19 correctness patches)  
**Release Status:** **ALPHA - Not Production Ready**

## What This Is

Judge Atlas is a map-first legal & public-record transparency prototype. It shows court events and reported crime incidents as separate layers on a North America map, with strong safety gates to prevent abuse.

- **Core Data Model:** Locations, courts, judges, cases, defendants, events, crimes, source registry, evidence snapshots, review items, audit logs, graph edges, entity linking, AI rule-based classification
- **Backend:** FastAPI, SQLAlchemy ORM, 28 Alembic migrations, PostGIS
- **Frontend:** Next.js, Leaflet, TypeScript, TailwindCSS
- **Map:** North America Leaflet base, event layers, crime aggregates, visibility controls
- **Admin:** Review queue, audit logs, source registry, AI correctness (rule-based)

## What Works

- **Core Schema:** Sufficient for long-term goals (entity linking, graph edges, evidence vault, memory derivatives)
- **Public Safety Gates:** Filters by public_visibility=True, approved statuses, non-placeholder locations, safe precision
- **Evidence Layer:** SourceSnapshot stores raw content, hashes, extracted text, storage backend path, truncation flags (ready for external vault)
- **Review System:** All ingested data is pending_review by default; nothing auto-publishes without admin approval
- **Source Registry:** Ingestion sources disabled by default; only active sources execute
- **Audit Logging:** All admin mutations captured with actor, action, entity, payload, request metadata

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
- [ ] Verify all 28 migrations pass

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

## Do Not Yet Claim

- [ ] "Production-ready" — Alpha only
- [ ] "AI-powered" — Rule-based extraction only
- [ ] "Uses memory" — Contract defined, not implemented
- [ ] "Complete Canadian law coverage" — Stubs only
- [ ] "Live CourtListener sync" — Scaffolding only
- [ ] "Enterprise authentication" — Shared-token alpha only

## Do Claim

- [x] "Open-source legal transparency research prototype"
- [x] "Map-first, review-first, fail-closed design"
- [x] "Strong source-first and evidence-first commitment"
- [x] "No auto-publish without human review"
- [x] "All admin mutations audited"
- [x] "Source registry is fail-closed: new sources start disabled"
- [x] "Memory rebuilds scoped per-entity via EntityEvidenceLink"
- [x] "Snapshot integrity verifiable via /verify endpoint"
- [x] "Ready for local development and research"

---

**Maintainer Note:**  
This app is the best version of Judge Atlas foundation so far as an alpha. The schema is correct, the safety spine is strong, and the next moves are clear. Do not call it production-ready yet. Do not expose admin endpoints publicly with dev tokens. Do complete the source registry UI, evidence vault, and memory layer before expanding to multi-user or public deployment.
