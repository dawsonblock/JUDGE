"""Tests for memory rebuild orchestration in app.memory.rebuild."""

import pytest
from unittest.mock import MagicMock, patch

from app.memory.rebuild import run_rebuild
from app.models.entities import CanonicalEntity, MemoryRebuildRun


class TestRunRebuild:
    def _make_db(self):
        return MagicMock()

    def test_rejects_unknown_scope(self):
        db = self._make_db()
        with pytest.raises(ValueError, match="Unknown rebuild scope"):
            run_rebuild("bogus_scope", db)

    def test_entity_scope_requires_entity_id(self):
        db = self._make_db()
        with pytest.raises(ValueError, match="entity_id is required"):
            run_rebuild("entity", db, entity_id=None)

    def test_entity_scope_missing_entity_raises(self):
        db = self._make_db()
        db.get.return_value = None
        with pytest.raises(ValueError, match="does not exist"):
            run_rebuild("entity", db, entity_id=999)

    def test_full_scope_with_no_entities_returns_completed_run(self):
        db = self._make_db()

        q = MagicMock()
        q.filter.return_value.all.return_value = []
        db.query.return_value = q

        result = run_rebuild("full", db)

        assert result.status == "completed"
        assert result.entities_processed == 0

    def test_full_scope_skips_entity_without_snapshot(self):
        db = self._make_db()

        entity = MagicMock(spec=CanonicalEntity)
        entity.id = 1
        entity.entity_type = "judge"
        entity.canonical_name = "Test Judge"

        q = MagicMock()
        q.filter.return_value.all.return_value = [entity]
        db.query.return_value = q

        with patch(
            "app.memory.rebuild._get_latest_snapshot_for_entity", return_value=None
        ):
            result = run_rebuild("full", db)

        assert result.status == "completed"
        assert result.entities_processed == 1
        assert result.claims_created == 0

    def test_full_scope_exception_marks_run_as_failed(self):
        db = self._make_db()

        db.query.side_effect = RuntimeError("db exploded")

        result = run_rebuild("full", db)

        assert result.status == "failed"
        assert result.error_message is not None

    def test_entity_scope_processes_single_entity(self):
        db = self._make_db()

        entity = MagicMock(spec=CanonicalEntity)
        entity.id = 7
        entity.entity_type = "judge"
        entity.canonical_name = "Alice"
        db.get.return_value = entity

        with patch(
            "app.memory.rebuild._get_latest_snapshot_for_entity", return_value=None
        ):
            result = run_rebuild("entity", db, entity_id=7)

        assert result.status == "completed"
        assert result.entities_processed == 1


class TestUpsertClaims:
    """Tests for _upsert_claims claim-refresh behaviour."""

    def _make_snapshot(self):
        snap = MagicMock()
        snap.id = 1
        snap.content_hash = "a" * 64
        snap.extracted_text = "The judge ruled on the case."
        return snap

    def _make_db(self, existing_claim, existing_link=None):
        from app.models.entities import MemoryClaim, MemoryEvidenceLink

        def mock_query(model):
            q = MagicMock()
            if model is MemoryClaim:
                q.filter.return_value.first.return_value = existing_claim
            else:
                q.filter.return_value.first.return_value = existing_link
            return q

        db = MagicMock()
        db.query.side_effect = mock_query
        return db

    def test_upsert_claims_updates_last_seen_at_on_existing(self):
        """Re-encountering a non-hard-rejected claim refreshes last_seen_at and reactivates it."""
        from app.memory.rebuild import _upsert_claims
        from app.models.entities import MemoryClaim

        existing = MagicMock(spec=MemoryClaim)
        existing.id = 42
        existing.invalidation_reason = None
        existing.is_active = False
        existing.last_seen_at = None

        db = self._make_db(existing_claim=existing)
        extracted = [
            {"claim_type": "appointment", "claim_value": "district", "confidence": 0.9}
        ]
        _upsert_claims(db, entity_id=1, extracted=extracted, snapshot=self._make_snapshot())

        assert existing.last_seen_at is not None
        assert existing.status == "active"
        assert existing.is_active is True

    def test_upsert_claims_hard_rejected_claim_is_not_reactivated(self):
        """A manually-rejected claim must not be reactivated when re-encountered."""
        from app.memory.rebuild import _upsert_claims
        from app.models.entities import MemoryClaim

        existing = MagicMock(spec=MemoryClaim)
        existing.id = 99
        existing.invalidation_reason = "manual_reject"
        existing.is_active = False
        existing.status = "rejected"
        existing.last_seen_at = None

        db = self._make_db(existing_claim=existing)
        extracted = [
            {"claim_type": "appointment", "claim_value": "district", "confidence": 0.9}
        ]
        _upsert_claims(db, entity_id=1, extracted=extracted, snapshot=self._make_snapshot())

        # Hard-rejected claim must remain deactivated
        assert existing.is_active is False
        assert existing.status == "rejected"
