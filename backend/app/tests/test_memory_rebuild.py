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
