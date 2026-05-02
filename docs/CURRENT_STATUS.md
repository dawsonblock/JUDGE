# Judge Atlas - Current Status & Limitations

**Date:** 2026-05-02  
**Release Status:** **ALPHA - Not Production Ready**

## What This Is

Judge Atlas is a map-first legal & public-record transparency prototype. It shows court events and reported crime incidents as separate layers on a North America map, with strong safety gates to prevent abuse.

- **Core Data Model:** Locations, courts, judges, cases, defendants, events, crimes, source registry, evidence snapshots, review items, audit logs, graph edges, entity linking, AI rule-based classification
- **Backend:** FastAPI, SQLAlchemy ORM, 22 Alembic migrations, PostGIS
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

### 1. Memory System Is Contract-Only
- File: `docs/MEMORY_INTEGRATION_CONTRACT.md`
- No memory tables, embeddings, retrieval planner, invalidation engine, or API
- Backend is ready to receive a fluid memory layer, but memory is not implemented
- **Do not claim the app uses memory yet**

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
- Proof artifacts are from 19 migrations; repo now has 22
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

**Total Migrations:** 22 (correct as of 2026-05-02)

Recent migrations:
- `20260502_0001_add_snapshot_integrity_fields.py` — storage_backend, content_size_bytes, truncation_flag
- `20260502_0002_add_audit_actor_fields.py` — audit_logs.actor_id
- `20260502_0003_expand_source_registry_source_type.py` — source_type String(20)→String(80)

**Proof Status:** Alembic upgrade head tested on SQLite; full migration suite not yet re-proven against 22 migrations. Run `bash scripts/proof_all.sh` with fixed JTA_DATABASE_URL to verify current state.

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
- [ ] Verify all 22 migrations pass

### Phase 2 (Crawlee Safety)
- [x] Fix publish_recommendation ("hold" → "review_required")
- [x] Add test coverage for Crawlee safety defaults
- [x] Production startup checks added

### Phase 3 (Production Safety)
- [x] Disable admin endpoints by default in docker-compose.yml
- [x] Require explicit token configuration in .env
- [x] Startup validation: fail if tokens missing, dev tokens detected, wildcard CORS, Redis unavailable

### Phase 4 (Source Registry)
- [ ] Make source enable/disable the real control switch in admin UI
- [ ] Add UI controls to enable/disable courtlistener, saskatoon_police, statscan, etc.
- [ ] Verify ingestion runner respects source is_active

### Phase 5 (Evidence Vault)
- [ ] Configure JTA_EVIDENCE_STORE_ROOT=/Volumes/ExternalDrive/judge-atlas-evidence (or equivalent)
- [ ] Add startup verification: path exists, writable, not inside repo
- [ ] Large snapshots stored on external drive by hash

### Phase 6 (Fluid Memory)
- [ ] Design memory as derivative layer, not source of truth
- [ ] Add memory claim state tables with invalidation, checksums, rebuild status
- [ ] Embeddings, summaries, relationship hints reference source IDs, review IDs, graph edge IDs
- [ ] Rebuilds trigger when evidence changes

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
- [x] "Ready for local development and research"

---

**Maintainer Note:**  
This app is the best version of Judge Atlas foundation so far as an alpha. The schema is correct, the safety spine is strong, and the next moves are clear. Do not call it production-ready yet. Do not expose admin endpoints publicly with dev tokens. Do complete the source registry UI, evidence vault, and memory layer before expanding to multi-user or public deployment.
