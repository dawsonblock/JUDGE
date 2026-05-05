"""Tests for IngestionResult data structures and ADAPTER_REGISTRY completeness."""

from __future__ import annotations

import pytest

from app.ingestion.adapters import IngestionResult, CreatedRecord, CreatedReviewItem
from app.ingestion.source_adapters import ADAPTER_REGISTRY
from app.ingestion.source_adapters.ckan_api import CKANApiAdapter
from app.ingestion.source_adapters.saskatoon_csv import SaskatoonCsvAdapter

# ── IngestionResult ──────────────────────────────────────────────────────────


class TestIngestionResult:
    def test_success_when_no_errors(self) -> None:
        result = IngestionResult(
            source_key="test",
            records_fetched=5,
            records_skipped=0,
            created_records=[],
            review_items=[],
            errors=[],
        )
        assert result.success is True

    def test_failure_when_errors_present(self) -> None:
        result = IngestionResult(
            source_key="test",
            records_fetched=0,
            records_skipped=0,
            created_records=[],
            review_items=[],
            errors=["Something went wrong"],
        )
        assert result.success is False

    def test_counts_consistent(self) -> None:
        records = [
            CreatedRecord(
                source_key="test",
                record_type="CrimeIncident",
                external_id="1",
                payload={},
            )
        ]
        result = IngestionResult(
            source_key="test",
            records_fetched=3,
            records_skipped=2,
            created_records=records,
            review_items=[],
            errors=[],
        )
        assert len(result.created_records) == 1
        assert result.records_skipped == 2

    def test_review_item_stored(self) -> None:
        item = CreatedReviewItem(
            source_key="test", headline=None, url=None, extracted_text=None
        )
        result = IngestionResult(
            source_key="test",
            records_fetched=1,
            records_skipped=0,
            created_records=[],
            review_items=[item],
            errors=[],
        )
        assert result.success is True
        assert len(result.review_items) == 1


# ── ADAPTER_REGISTRY completeness ────────────────────────────────────────────

EXPECTED_PARSER_KEYS = {
    "saskatoon_csv",
    "saskatoon_police_csv",
    "crawlee_police_release",
    "sk_courts_html",
    "statscan_table",
    "canlii_api",
    "federal_court_html",
    "scc_lexum_api",
    "crawlee_gov_news",
    "sk_legislature_html",
    "laws_justice_html",
    "ckan_api",
}


class TestAdapterRegistry:
    def test_all_expected_keys_present(self) -> None:
        missing = EXPECTED_PARSER_KEYS - set(ADAPTER_REGISTRY)
        assert not missing, f"Missing adapter keys: {missing}"

    def test_all_registered_adapters_have_run_method(self) -> None:
        for key, cls in ADAPTER_REGISTRY.items():
            assert hasattr(cls, "run"), f"Adapter {key} ({cls.__name__}) missing run()"

    def test_all_registered_adapters_have_fetch_method(self) -> None:
        for key, cls in ADAPTER_REGISTRY.items():
            assert hasattr(
                cls, "fetch"
            ), f"Adapter {key} ({cls.__name__}) missing fetch()"

    def test_all_registered_adapters_have_parse_method(self) -> None:
        for key, cls in ADAPTER_REGISTRY.items():
            assert hasattr(
                cls, "parse"
            ), f"Adapter {key} ({cls.__name__}) missing parse()"


# ── CKANApiAdapter unit checks ───────────────────────────────────────────────


class TestCKANApiAdapterUnit:
    def test_fetch_returns_empty_when_no_resource_id(self) -> None:
        adapter = CKANApiAdapter(
            source_key="test_ckan",
            base_url="https://opendata.saskatoon.ca",
            allowed_domains_json='["opendata.saskatoon.ca"]',
            public_record_authority="official_open_data",
        )
        # No resource_id configured → fetch should return []
        rows = adapter.fetch()
        assert rows == []

    def test_parse_empty_rows_returns_empty(self) -> None:
        adapter = CKANApiAdapter(
            source_key="test_ckan",
            base_url="https://opendata.saskatoon.ca",
            allowed_domains_json='["opendata.saskatoon.ca"]',
            public_record_authority="official_open_data",
        )
        parsed = adapter.parse([])
        assert parsed == []


# ── SaskatoonCsvAdapter unit checks ─────────────────────────────────────────


class TestSaskatoonCsvAdapterUnit:
    def test_fetch_blocks_on_domain_violation(self) -> None:
        adapter = SaskatoonCsvAdapter(
            source_key="test_csv",
            base_url="https://malicious.example.com",
            allowed_domains_json='["opendata.saskatoon.ca"]',
            public_record_authority="official_open_data",
        )
        rows = adapter.fetch()
        assert rows == []

    def test_parse_empty_rows_returns_empty(self) -> None:
        adapter = SaskatoonCsvAdapter(
            source_key="test_csv",
            base_url="https://opendata.saskatoon.ca",
            allowed_domains_json='["opendata.saskatoon.ca"]',
            public_record_authority="official_open_data",
        )
        parsed = adapter.parse([])
        assert parsed == []
