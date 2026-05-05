"""Adapter for Saskatoon Police Service open-data crime CSV.

Handles source key: ``saskatoon_police_open_data``
Parser key: ``saskatoon_police_csv``
Creates: ``CrimeIncident`` records
Data source: https://www.saskatoonpolice.ca/open-data
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any

import httpx

from app.ingestion.adapters import (
    CanadianSourceAdapter,
    CreatedRecord,
    IngestionResult,
    ParsedRecord,
)
from app.ingestion.source_rules import check_domain_allowed, check_record_type_allowed

logger = logging.getLogger(__name__)

_RECORD_TYPE = "CrimeIncident"


class SaskatoonPoliceCsvAdapter(CanadianSourceAdapter):
    """Fetch and parse the Saskatoon Police Service open-data crime CSV.

    The Saskatoon Police Service publishes crime statistics on its open-data
    portal.  This adapter downloads the CSV, maps rows to ``CrimeIncident``
    payloads, and enforces source safety rules.

    .. note::
        Skeleton implementation.  Column names must be verified against the
        live dataset before production use.  The ``base_url`` comes from
        ``SourceRegistry.base_url`` for the ``saskatoon_police_open_data``
        source key.
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

    def fetch(self) -> list[dict[str, Any]]:
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
        """Map CSV rows to ParsedRecord.

        TODO: Replace placeholder column names with actual headers from the
        Saskatoon Police Service open-data CSV schema.
        """
        records: list[ParsedRecord] = []
        for row in raw:
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
                    external_id=row.get("Offence Number") or row.get("incident_id"),
                    payload={"raw": dict(row), "source_key": self._source_key},
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
