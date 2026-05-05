"""Adapter for Saskatoon Open Data crime CSV exports.

Handles source key: ``saskatoon_open_data_crime``
Parser key: ``saskatoon_csv``
Creates: ``CrimeIncident`` records
Data source: https://opendata-saskatoon.opendata.arcgis.com/
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any

import httpx

from app.ingestion.adapters import CanadianSourceAdapter, IngestionResult, ParsedRecord
from app.ingestion.source_rules import check_domain_allowed, check_record_type_allowed

logger = logging.getLogger(__name__)

_RECORD_TYPE = "CrimeIncident"


class SaskatoonCsvAdapter(CanadianSourceAdapter):
    """Fetch and parse Saskatoon Open Data crime CSV.

    The City of Saskatoon publishes crime incident data as a downloadable CSV
    through its ArcGIS Open Data portal.  This adapter downloads the CSV,
    maps each row to a ``CrimeIncident`` payload, and applies source safety
    rules before returning an :class:`IngestionResult`.

    .. note::
        This is a skeleton implementation.  The ``fetch()`` and ``parse()``
        methods require the actual column mapping from the live dataset before
        they will produce correct data.  Columns must be validated against the
        published schema at ``base_url`` during integration testing.
    """

    def __init__(
        self,
        source_key: str,
        base_url: str,
        allowed_domains_json: str | None = None,
        public_record_authority: str | None = None,
    ) -> None:
        self._source_key = source_key
        self._base_url = base_url
        self._allowed_domains_json = allowed_domains_json or "[]"
        self._public_record_authority = public_record_authority

    # ── SourceAdapter interface ──────────────────────────────────────────────

    def fetch(self) -> list[dict[str, Any]]:
        """Download the CSV and return rows as dicts.

        TODO: Confirm the exact download URL from the ArcGIS Open Data portal
        and the correct ``?outFields=*&f=csv`` query parameters.
        """
        # Validate domain before making request
        violation = check_domain_allowed(self._base_url, self._allowed_domains_json)
        if violation:
            logger.warning(
                "Domain check failed for %s: %s", self._source_key, violation.detail
            )
            return []

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(self._base_url)
                resp.raise_for_status()
            reader = csv.DictReader(io.StringIO(resp.text))
            return list(reader)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to fetch %s: %s", self._source_key, exc)
            return []

    def parse(self, raw: list[dict[str, Any]]) -> list[ParsedRecord]:
        """Map CSV rows to ParsedRecord instances.

        TODO: Replace placeholder column names with actual column headers
        from the Saskatoon Open Data schema once confirmed.
        """
        records: list[ParsedRecord] = []
        for row in raw:
            # Rule-gate the record type
            violation = check_record_type_allowed(
                _RECORD_TYPE,
                "official_open_data",
                f'["{_RECORD_TYPE}"]',
            )
            if violation:
                logger.warning("Record type gate failed: %s", violation.detail)
                continue

            records.append(
                ParsedRecord(
                    source_key=self._source_key,
                    record_type=_RECORD_TYPE,
                    external_id=row.get("incident_number") or row.get("OBJECTID"),
                    payload={
                        # TODO: map actual columns when schema is confirmed
                        "raw": dict(row),
                        "source_key": self._source_key,
                    },
                    source_url=self._base_url,
                )
            )
        return records

    def run(self) -> IngestionResult:
        result = IngestionResult(source_key=self._source_key)
        try:
            raw = self.fetch()
            result.records_fetched = len(raw)
            parsed = self.parse(raw)
            result.records_skipped = len(raw) - len(parsed)
            for p in parsed:
                from app.ingestion.adapters import (
                    CreatedRecord,
                )  # local to avoid circular

                result.created_records.append(
                    CreatedRecord(
                        source_key=p.source_key,
                        record_type=p.record_type,
                        external_id=p.external_id,
                        payload=p.payload,
                        source_url=p.source_url,
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unhandled error in %s adapter", self._source_key)
            result.errors.append(str(exc))
        return result
