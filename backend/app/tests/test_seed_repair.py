"""Tests for repair_canada_first_defaults (source_registry seed) and TIER_HOLD enforcement."""

from __future__ import annotations

import pytest

from app.db.session import SessionLocal
from app.models.entities import CrimeIncident, SourceRegistry
from app.seed.source_registry import repair_canada_first_defaults, seed_source_registry

# ---------------------------------------------------------------------------
# TestRepairCanadaFirstDefaults
# ---------------------------------------------------------------------------


class TestRepairCanadaFirstDefaults:
    def test_no_deviations_after_fresh_seed(self):
        """After seeding + a live repair pass, dry_run=True must report zero further deviations.

        seed_source_registry is idempotent (skips existing rows), so previous tests may
        have left rows with stale field values.  Run a live repair first to normalise them,
        then verify that a second (dry-run) pass finds nothing — i.e., repair is idempotent.
        """
        with SessionLocal() as db:
            seed_source_registry(db)
            # Normalise any pre-existing stale rows from earlier test runs.
            repair_canada_first_defaults(db, dry_run=False)
            # Second pass must be clean (idempotency assertion).
            changes = repair_canada_first_defaults(db, dry_run=True)
        assert isinstance(changes, list)
        assert changes == []

    def test_dry_run_does_not_commit_changes(self):
        """dry_run=True must detect deviations but not fix them in the DB."""
        with SessionLocal() as db:
            seed_source_registry(db)
            row = db.query(SourceRegistry).filter_by(source_key="statscan").first()
            if row is None:
                pytest.skip("statscan row not seeded")
            # Introduce a deviation in a field that _REPAIR_FIELDS will catch.
            row.source_tier = "wrong_tier"
            db.commit()

        with SessionLocal() as db:
            changes = repair_canada_first_defaults(db, dry_run=True)

        assert any("statscan" in c for c in changes), "Expected deviation not detected"

        # DB must be unchanged (dry_run did not commit)
        with SessionLocal() as db:
            row = db.query(SourceRegistry).filter_by(source_key="statscan").first()
            if row is not None:
                assert row.source_tier == "wrong_tier"  # still deviated

    def test_live_run_corrects_deviated_fields(self):
        """dry_run=False must repair deviated fields in the DB."""
        with SessionLocal() as db:
            seed_source_registry(db)
            row = db.query(SourceRegistry).filter_by(source_key="statscan").first()
            if row is None:
                pytest.skip("statscan row not seeded")
            row.source_tier = "wrong_tier"
            db.commit()

        with SessionLocal() as db:
            changes = repair_canada_first_defaults(db, dry_run=False)

        assert any("statscan" in c for c in changes)

        with SessionLocal() as db:
            row = db.query(SourceRegistry).filter_by(source_key="statscan").first()
            assert row is not None
            # Spec value restored
            assert row.source_tier == "official_government_statistics"

    def test_operational_flags_not_reset_by_repair(self):
        """requires_manual_review and auto_publish_enabled are excluded from _REPAIR_FIELDS;
        admin-set values must survive a live repair pass."""
        with SessionLocal() as db:
            seed_source_registry(db)
            row = db.query(SourceRegistry).filter_by(source_key="statscan").first()
            if row is None:
                pytest.skip("statscan row not seeded")
            # Override operational flags (not in _REPAIR_FIELDS)
            row.requires_manual_review = False
            row.auto_publish_enabled = True
            db.commit()

        with SessionLocal() as db:
            repair_canada_first_defaults(db, dry_run=False)

        with SessionLocal() as db:
            row = db.query(SourceRegistry).filter_by(source_key="statscan").first()
            assert row is not None
            # Operational flags must survive repair unchanged
            assert row.requires_manual_review is False
            assert row.auto_publish_enabled is True

    def test_is_active_not_reset_by_repair(self):
        """is_active is excluded from _REPAIR_FIELDS; admin-set value must survive repair."""
        with SessionLocal() as db:
            seed_source_registry(db)
            row = db.query(SourceRegistry).filter_by(source_key="toronto_crime").first()
            if row is None:
                pytest.skip("toronto_crime row not seeded")
            row.is_active = True  # admin-enabled; spec has is_active=False
            db.commit()

        with SessionLocal() as db:
            repair_canada_first_defaults(db, dry_run=False)

        with SessionLocal() as db:
            row = db.query(SourceRegistry).filter_by(source_key="toronto_crime").first()
            assert row is not None
            assert row.is_active is True  # must survive repair


# ---------------------------------------------------------------------------
# TestHoldEnforcement
# ---------------------------------------------------------------------------


class TestHoldEnforcement:
    """Verify TIER_HOLD unconditionally revokes public visibility on existing records."""

    def test_hold_revokes_auto_published_existing_record(self):
        """An existing incident with is_public=True must be demoted when tier==TIER_HOLD."""
        from datetime import datetime, timezone

        from app.ingestion.crime_sources.base import CrimeIncidentRecord
        from app.ingestion.crime_sources.persistence import persist_crime_incident
        from app.models.entities import CrimeIncident, SourceRegistry

        src_key = "hold_enf_test_src"
        src_name = "hold_enf_test_sname"
        ext_id = "HOLD-ENF-001"

        with SessionLocal() as db:
            # Registry row: holds (auto_publish_enabled=False, requires_manual_review=True)
            reg = db.query(SourceRegistry).filter_by(source_key=src_key).first()
            if reg is None:
                db.add(
                    SourceRegistry(
                        source_key=src_key,
                        source_name=src_name,
                        source_tier="official_police_open_data",
                        is_active=True,
                        auto_publish_enabled=False,
                        requires_manual_review=True,
                    )
                )
                db.commit()

            # Plant an existing incident marked as auto-published
            existing = (
                db.query(CrimeIncident)
                .filter_by(source_name=src_name, external_id=ext_id)
                .first()
            )
            if existing is None:
                db.add(
                    CrimeIncident(
                        source_name=src_name,
                        external_id=ext_id,
                        incident_type="Assault",
                        incident_category="violent",
                        precision_level="city_centroid",
                        verification_status="reported",
                        is_public=True,
                        review_status="official_police_open_data_report",
                        is_aggregate=False,
                    )
                )
            else:
                existing.is_public = True
                existing.review_status = "official_police_open_data_report"
            db.commit()

            # Re-ingest via persist; source is held by registry
            record = CrimeIncidentRecord(
                source_id=ext_id,
                external_id=ext_id,
                incident_type="Assault",
                incident_category="violent",
                reported_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                city="Saskatoon",
                province_state="SK",
                country="Canada",
                public_area_label="Central",
                latitude_public=52.1,
                longitude_public=-106.6,
                precision_level="city_centroid",
                source_url="https://example.test/hold-enf",
                source_name=src_name,
                verification_status="reported",
                data_last_seen_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
                is_public=True,
            )
            result = persist_crime_incident(db, record, source_key=src_key)
            db.flush()

        # Unconditional hold block must revoke visibility and demote status
        assert result.is_public is False
        assert result.review_status == "pending_review"
