# Authentication Roadmap

## Current Status: Shared-Token Alpha Auth

The current admin authentication system uses a shared admin token (configured via `JTA_ADMIN_TOKEN`). 

**This is acceptable for:**
- Local development
- Private demos
- Alpha-stage prototypes with a single trusted operator

**This is NOT acceptable for:**
- Public deployment
- Multi-user systems
- Production environments
- Systems requiring user accountability

## Why Current Auth Is Limited

The shared-token approach lacks:

1. **Per-User Identity** - No way to distinguish which team member performed an action
2. **Revocation** - Cannot invalidate a token for a specific user (only system-wide)
3. **Expiry** - Tokens do not automatically expire
4. **Multi-Factor Authentication (MFA)** - No additional security factors
5. **Durable Audit Trail** - Audit logs cannot attribute actions to named individuals
6. **Rate Limiting Per User** - Cannot throttle individual abusers without affecting everyone

## Production Auth Options

When preparing for public deployment, implement one of:

### Option 1: Clerk (Recommended for SaaS)
- Multi-user management with built-in social login
- MFA and security policies
- Audit logs with user attribution
- Setup: https://clerk.com
- Estimated effort: 2-3 days

### Option 2: Auth0 (Enterprise)
- Industry-standard OAuth2/OIDC provider
- Rich policy and role management
- Comprehensive audit logging
- Setup: https://auth0.com
- Estimated effort: 2-3 days

### Option 3: Supabase Auth (Self-Hosted Option)
- Open-source authentication layer
- PostgreSQL-backed user tables
- Email/phone verification
- JWT-based sessions
- Setup: https://supabase.com/docs/guides/auth
- Estimated effort: 3-4 days

### Option 4: Custom Users Table (DIY)
- Store users in PostgreSQL
- Implement password hashing (bcrypt/argon2)
- Session/JWT management
- Email verification flow
- Setup: In-house development
- Estimated effort: 1-2 weeks

## Migration Path

1. **Alpha (current)**: Shared token, single operator
2. **Beta**: User registration + password auth, audit logging per user
3. **Production**: MFA, role-based access control, compliance audit trail

## Do Not Block Current Repair On This

The current shared-token system is **sufficient for alpha-stage work**. Do not defer the safety fixes (database length, rate limiting, URL validation) waiting for real auth. Implement user auth after stabilizing the core platform.

## See Also

- [DEPLOYMENT.md](../DEPLOYMENT.md) - Deployment and security hardening
- [AUTH_ROADMAP.md](./AUTH_ROADMAP.md) - This file
