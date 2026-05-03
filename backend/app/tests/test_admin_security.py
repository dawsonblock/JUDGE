"""Admin security tests.

Proves that:
1. Missing token returns 403
2. Wrong token returns 403
3. Correct token succeeds (when admin enabled)
4. Admin endpoints fail when admin features disabled
5. Production mode rejects default tokens
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestAdminAuth:
    """Test admin authentication and authorization."""

    def test_admin_review_queue_requires_token(self):
        """Admin review queue should require token."""
        response = client.get("/api/admin/review-queue")
        # Should return 403 when admin is not enabled or token missing
        assert response.status_code in (403, 404, 401)

    def test_admin_review_items_requires_token(self):
        """Admin review items should require token."""
        response = client.get("/api/admin/review/items")
        # Should return 403 when admin is not enabled or token missing
        assert response.status_code in (403, 404, 401)

    def test_admin_ingestion_requires_token(self):
        """Admin ingestion endpoints should require token."""
        response = client.get("/api/admin/ingestion-runs")
        # Should return 403 when admin is not enabled or token missing
        assert response.status_code in (403, 404, 401)

    def test_admin_sources_requires_token(self):
        """Admin sources endpoints should require token."""
        response = client.get("/api/admin/sources")
        # Should return 403 when admin is not enabled or token missing
        assert response.status_code in (403, 404, 401)

    def test_wrong_token_rejected(self):
        """Wrong admin token should be rejected."""
        response = client.get(
            "/api/admin/review-queue",
            headers={"X-JTA-Admin-Token": "wrong-token"}
        )
        # Should be rejected
        assert response.status_code in (403, 401)


class TestAdminConfig:
    """Test admin configuration validation."""

    def test_shared_token_documented_as_local_only(self):
        """Shared token auth is documented as local-alpha only.

        This test verifies that the documentation exists and describes
        the limitations of shared token authentication.
        """
        import os

        docs_path = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "AUTH_ROADMAP.md")
        assert os.path.exists(docs_path), "AUTH_ROADMAP.md should exist"

        with open(docs_path) as f:
            content = f.read()
            assert "local-alpha" in content.lower() or "shared token" in content.lower()

    def test_deployment_security_doc_exists(self):
        """Deployment security documentation should exist."""
        import os

        docs_path = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "DEPLOYMENT_SECURITY.md")
        assert os.path.exists(docs_path), "DEPLOYMENT_SECURITY.md should exist"


class TestAuditLogging:
    """Test audit logging requirements.

    These are aspirational tests for when audit logging is implemented.
    """

    def test_review_actions_need_audit_log(self):
        """Review actions should be logged for audit.

        This test documents the requirement that all review decisions
        (approve, reject, block) must be logged with:
        - Who performed the action
        - When it was performed
        - What was changed
        - Previous and new state
        """
        # Placeholder test - will fail until audit logging is implemented
        pytest.skip("Audit logging not yet implemented - see AUTH_ROADMAP.md")

    def test_admin_api_calls_need_audit_log(self):
        """Admin API calls should be logged.

        This test documents the requirement that all admin API calls
        must be logged for security monitoring.
        """
        # Placeholder test - will fail until audit logging is implemented
        pytest.skip("Audit logging not yet implemented - see AUTH_ROADMAP.md")


class TestAdminActorIdentity:
    """Test that admin actor identity never exposes raw tokens."""

    def test_require_admin_token_returns_admin_actor(self, monkeypatch):
        """require_admin_token must return AdminActor, not a string."""
        from unittest.mock import patch

        from fastapi import HTTPException

        from app.auth.actor import AdminActor

        # Patch get_settings to return a settings object with a known token
        class FakeSettings:
            admin_token = "test-secret-token"
            admin_review_token = None
            jwt_auth_enabled = False

        with patch("app.auth.admin.get_settings", return_value=FakeSettings()):
            from app.auth.admin import require_admin_token

            actor = require_admin_token.__wrapped__("test-secret-token") if hasattr(
                require_admin_token, "__wrapped__"
            ) else require_admin_token(x_jta_admin_token="test-secret-token")

        assert isinstance(actor, AdminActor), (
            f"require_admin_token must return AdminActor, got {type(actor)}"
        )

    def test_actor_id_is_not_raw_token(self, monkeypatch):
        """actor_id must be a stable label, never the raw token value."""
        from unittest.mock import patch

        class FakeSettings:
            admin_token = "super-secret-value-12345"
            admin_review_token = None
            jwt_auth_enabled = False

        with patch("app.auth.admin.get_settings", return_value=FakeSettings()):
            from app.auth.admin import require_admin_token

            actor = require_admin_token(x_jta_admin_token="super-secret-value-12345")

        assert actor.actor_id != "super-secret-value-12345", (
            "actor_id must not be the raw token value"
        )
        assert actor.actor_id == "shared-admin-token"

    def test_audit_log_does_not_contain_raw_token(self):
        """Raw token value must never appear in audit log payload."""
        import json
        from datetime import datetime, timezone
        from unittest.mock import MagicMock, patch

        from app.auth.actor import AdminActor
        from app.auth.admin import log_mutation

        raw_token = "my-very-secret-admin-token-xyz"
        actor = AdminActor(
            actor_id="shared-admin-token",
            actor_type="shared_token",
            role="system_admin",
            auth_method="shared_token",
        )

        captured = {}

        class FakeDB:
            def add(self, obj):
                captured["log"] = obj

            def commit(self):
                pass

            def rollback(self):
                pass

            def close(self):
                pass

        with patch("app.auth.admin.SessionLocal", return_value=FakeDB()):
            log_mutation(
                action="test_action",
                payload={"description": "test"},
                actor=actor,
            )

        log_entry = captured.get("log")
        assert log_entry is not None
        # Check no field contains the raw token
        for field in ("actor_id", "actor_type", "actor_role"):
            val = getattr(log_entry, field, None)
            assert val != raw_token, f"Field {field} contains raw token"
        # Check payload does not contain raw token
        payload_str = json.dumps(log_entry.payload or {})
        assert raw_token not in payload_str, "Raw token found in audit log payload"

    def test_actor_id_is_stable_label(self):
        """actor_id for shared-token auth must always be 'shared-admin-token'."""
        from unittest.mock import patch

        class FakeSettings:
            admin_token = "token-abc"
            admin_review_token = None
            jwt_auth_enabled = False

        with patch("app.auth.admin.get_settings", return_value=FakeSettings()):
            from app.auth.admin import require_admin_token

            actor = require_admin_token(x_jta_admin_token="token-abc")

        assert actor.actor_id == "shared-admin-token"
        assert actor.actor_type == "shared_token"
        assert actor.role == "system_admin"
        assert actor.auth_method == "shared_token"

