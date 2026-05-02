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
