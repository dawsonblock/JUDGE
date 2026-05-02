# Authentication Roadmap

## Current Status: Alpha (Shared-Token Auth Only)

The current authentication system uses a shared admin token for all admin operations. This is **acceptable for local development and private demos**, but **not suitable for public deployment**.

### Current Implementation
- **Single shared token** (`JTA_ADMIN_TOKEN`, `JTA_ADMIN_REVIEW_TOKEN`)
- **No per-user identity** — all valid tokens get the same admin privileges
- **No token revocation** — invalidating a token requires code changes and redeployment
- **No MFA** — two-factor authentication not supported
- **No audit trail of per-user actions** — all mutations logged as "shared-admin-token"
- **No session management** — tokens never expire

### Why This Matters
This architecture is intentional for alpha stability:
- Simplifies deployment and development
- Avoids dependency on external auth services
- Allows rapid iteration on core features

However, it creates accountability gaps:
- Multiple team members using the same token cannot be distinguished in audit logs
- A compromised token cannot be revoked without redeploy
- No way to restrict specific users to specific operations (e.g., reviewer vs. admin)

### Next Steps: Real Authentication (Phase 2)

Replace shared-token auth with one of these options:

#### Option 1: Clerk (Recommended)
- **Pros**: Zero-friction login, built-in MFA, per-user API keys
- **Integration**: Add Clerk middleware, extract user ID from JWT in audit logs
- **Cost**: Free tier up to 10,000 monthly active users
- **Docs**: https://clerk.com/docs

#### Option 2: Auth0
- **Pros**: Enterprise-grade, multi-tenant, extensive integrations
- **Integration**: OAuth 2.0 / OIDC, verify JWT, extract subject claim
- **Cost**: Free tier up to 10,000 users
- **Docs**: https://auth0.com/docs

#### Option 3: Supabase Auth
- **Pros**: Open-source alternative, PostgreSQL-native, self-hostable
- **Integration**: Use Supabase REST API, verify JWT with Supabase key
- **Cost**: Free tier included with Supabase database
- **Docs**: https://supabase.com/docs/guides/auth

#### Option 4: Local Users Table
- **Pros**: Full control, no external dependencies
- **Cons**: Responsibility for password security, MFA implementation
- **Integration**: SQLAlchemy models for users/roles, implement JWT token issuance
- **Cost**: None (but higher operational burden)

### Deprecation Plan

1. **Phase 1 (Current)**: Shared-token auth with clear documentation of limitations
2. **Phase 2 (Q3 2026)**: Add real auth option alongside shared-token (no breaking changes)
3. **Phase 3 (Q4 2026)**: Default to real auth, keep shared-token as development-only option
4. **Phase 4 (2027)**: Remove shared-token auth entirely

### Implementation Checklist

When ready to implement real auth:
- [ ] Choose auth provider (Clerk, Auth0, Supabase, or local)
- [ ] Implement login UI in frontend
- [ ] Add JWT verification middleware to backend
- [ ] Update `AdminActor` to extract real user ID from JWT
- [ ] Update audit logging to use real user IDs (not "shared-admin-token")
- [ ] Add per-user role assignments (viewer, reviewer, source_admin, system_admin)
- [ ] Add token management endpoints (list, revoke)
- [ ] Add MFA setup flows
- [ ] Update documentation
- [ ] Migrate existing admin tokens to new system
- [ ] Deprecate shared-token auth in production

### Security Review Checklist (Before Public Launch)

- [ ] Replace shared-token auth with real authentication
- [ ] Enable HTTPS in production (not http://)
- [ ] Use strong API keys for CourtListener, external APIs
- [ ] Run security audit on database schema (no PII exposed without consent)
- [ ] Implement rate limiting with Redis backend (do not fail open in production)
- [ ] Add CORS allowlist validation (do not allow all origins)
- [ ] Review all public endpoints for information leakage
- [ ] Implement data retention policies for sensitive content
- [ ] Add backup/disaster recovery procedures
- [ ] Set up security event logging and alerting

---

**Do not proceed to public launch until real authentication is in place.**
