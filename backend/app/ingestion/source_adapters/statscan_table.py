"""Adapter for Statistics Canada crime statistics tables.

Handles source keys: ``statscan_ccjs_crime_sk``, ``statscan_ucr_national``
Parser key: ``statscan_table``
Creates: ``CrimeIncident`` records
Authority: ``official_statistics``

Data source: https://www150.statcan.gc.ca/ (CANSIM / NDM tables)
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.ingestion.adapters import (
    CreatedRecord,
    IngestionResult,
    ParsedRecord,
    SourceAdapter,
)
from app.ingestion.source_rules import check_domain_allowed, check_record_type_allowed

logger = logging.getLogger(__name__)

_RECORD_TYPE = "CrimeIncident"
_PUBLIC_RECORD_AUTHORITY = "official_statistics"

# Statistics Canada JSON API base for CANSIM table data
_STATSCAN_API_BASE = (
    "https://www150.statcan.gc.ca/t1/tbl1/en/dtbl!downloadTbl/csvDownload"
)


class StatscanTableAdapter(SourceAdapter):
    """Fetch Statistics Canada CANSIM table data and produce CrimeIncident records.

    Statistics Canada publishes crime statistics through its CANSIM table
    service.  This adapter fetches data as JSON or CSV (depending on the
    table's available formats) and maps aggregate rows to ``CrimeIncident``
    records with appropriate metadata indicating they are aggregate statistics,
    not individual incident records.

    .. note::
        Skeleton implementation.  The exact API endpoint and response schema
        must be verified against the live CANSIM API documentation.  Some
        tables require the product ID appended to the download URL.
        ``base_url`` from ``SourceRegistry`` should hold the full download URL
        for the specific table.
    """

    def __init__(
        self,
        source_key: str,
        base_url: str,
        allowed_domains_json: str | None = None,
    ) -> None:
        self._source_key = source_key
        self._base_url = base_url
        self._allowed_domains_json = (
            allowed_domains_json or '["www150.statcan.gc.ca", "statcan.gc.ca"]'
        )

    def fetch(self) -> list[dict[str, Any]]:
        violation = check_domain_allowed(self._base_url, self._allowed_domains_json)
        if violation:
            logger.warning(
                "Domain check failed for %s: %s", self._source_key, violation.detail
            )
            return []
        try:
            with httpx.Client(
                timeout=60, headers={"User-Agent": "JudgeTracker-Research/1.0"}
            ) as client:
                resp = client.get(self._base_url)
                resp.raise_for_status()
            # Attempt JSON parse; fall back to CSV stub
            try:
                data = resp.json()
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "rows" in data:
                    return data["rows"]
                return [data]
            except Exception:
                # CSV fallback — return raw text for parse() to handle
                return [{"_raw_csv": resp.text}]
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to fetch %s: %s", self._source_key, exc)
            return []

    def parse(self, raw: list[dict[str, Any]]) -> list[ParsedRecord]:
        """Map Statistics Canada rows to CrimeIncident records.

        TODO: Replace placeholder field mapping with actual CANSIM schema
        column names for tables 35-10-0177-01 (CCJS) and 35-10-0069-01 (UCR).
        """
        records: list[ParsedRecord] = []
        for row in raw:
            if "_raw_csv" in row:
                # CSV not yet parsed — skip until CSV parsing is implemented
                logger.info(
                    "CSV data from %s requires CSV parser integration; skipping",
                    self._source_key,
                )
                continue
            violation = check_record_type_allowed(
                _RECORD_TYPE,
                _PUBLIC_RECORD_AUTHORITY,
                f'["{_RECORD_TYPE}"]',
            )
            if violation:
                continue
            # Use a composite key as external_id for deduplication
            external_id = (
                "_".join(
                    str(row.get(k, ""))
                    for k in ("REF_DATE", "GEO", "Statistics", "UOM")
                )
                or None
            )
            records.append(
                ParsedRecord(
                    source_key=self._source_key,
                    record_type=_RECORD_TYPE,
                    external_id=external_id,
                    payload={
                        "aggregate": True,
                        "source_key": self._source_key,
                        "raw": dict(row),
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
