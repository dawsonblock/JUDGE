"""Adapter for CKAN Open Data portals (Canada Open Data, Saskatoon Open Data Portal).

Handles source keys: ``canada_open_data_crime``, ``saskatoon_open_data_portal``
Parser key: ``ckan_api``
Creates: varies — ``CrimeIncident`` for crime datasets, ``ReviewItem`` for others
Authority: ``official_statistics`` / ``official_open_data``

CKAN API docs: https://docs.ckan.org/en/stable/api/
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.ingestion.adapters import (
    CanadianSourceAdapter,
    CreatedRecord,
    CreatedReviewItem,
    IngestionResult,
    ParsedRecord,
)
from app.ingestion.source_rules import check_domain_allowed, check_record_type_allowed

logger = logging.getLogger(__name__)


_RECORD_TYPE_MAP: dict[str, str] = {
    # Maps source_key prefix → default record type
    "canada_open_data_crime": "CrimeIncident",
    "saskatoon_open_data_portal": "ReviewItem",
}


class CKANApiAdapter(CanadianSourceAdapter):
    """Fetch records from a CKAN-based open data portal.

    Both open.canada.ca and the Saskatoon Open Data Portal run CKAN.  This
    adapter uses the CKAN datastore API to download tabular data from a
    specific resource (identified by the resource ID embedded in ``base_url``
    or passed as ``resource_id``).

    For crime-statistic datasets the records are mapped to ``CrimeIncident``.
    For general civic datasets the records are mapped to ``ReviewItem``.

    .. note::
        Skeleton implementation.  The ``resource_id`` must be extracted from
        the ``base_url`` or ``SourceRegistry`` metadata before production use.
        Pagination via ``offset`` / ``limit`` is not yet implemented.
    """

    def __init__(
        self,
        source_key: str,
        base_url: str,
        resource_id: str | None = None,
        allowed_domains_json: str | None = None,
        public_record_authority: str = "official_statistics",
    ) -> None:
        self._source_key = source_key
        self._base_url = base_url.rstrip("/")
        self._resource_id = resource_id
        self._allowed_domains_json = allowed_domains_json or "[]"
        self._public_record_authority = public_record_authority
        self._record_type = _RECORD_TYPE_MAP.get(source_key, "ReviewItem")

    def _ckan_api_url(self) -> str:
        """Construct CKAN datastore_search API URL."""
        if self._resource_id:
            return f"{self._base_url}/api/3/action/datastore_search?resource_id={self._resource_id}&limit=100"
        return f"{self._base_url}/api/3/action/datastore_search"

    def fetch(self) -> list[dict[str, Any]]:
        api_url = self._ckan_api_url()
        violation = check_domain_allowed(api_url, self._allowed_domains_json)
        if violation:
            logger.warning(
                "Domain check failed for %s: %s", self._source_key, violation.detail
            )
            return []
        if not self._resource_id:
            logger.warning(
                "No resource_id configured for %s; cannot fetch data", self._source_key
            )
            return []
        try:
            with httpx.Client(
                timeout=60, headers={"User-Agent": "JudgeTracker-Research/1.0"}
            ) as client:
                resp = client.get(api_url)
                resp.raise_for_status()
            data = resp.json()
            if data.get("success") and "result" in data:
                return data["result"].get("records", [])
            return []
        except Exception as exc:  # noqa: BLE001
            logger.error("CKAN API fetch failed for %s: %s", self._source_key, exc)
            return []

    def parse(self, raw: list[dict[str, Any]]) -> list[ParsedRecord]:
        records: list[ParsedRecord] = []
        for row in raw:
            violation = check_record_type_allowed(
                self._record_type,
                self._public_record_authority,
                f'["{self._record_type}"]',
            )
            if violation:
                continue
            external_id = str(row.get("_id") or row.get("id") or "")
            records.append(
                ParsedRecord(
                    source_key=self._source_key,
                    record_type=self._record_type,
                    external_id=external_id or None,
                    payload={"source_key": self._source_key, "raw": dict(row)},
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
                if p.record_type == "CrimeIncident":
                    result.created_records.append(
                        CreatedRecord(
                            source_key=p.source_key,
                            record_type=p.record_type,
                            external_id=p.external_id,
                            payload=p.payload,
                            source_url=p.source_url,
                        )
                    )
                else:
                    result.review_items.append(
                        CreatedReviewItem(
                            source_key=p.source_key,
                            headline=None,
                            url=p.source_url,
                            extracted_text=None,
                            confidence_score=0.0,
                            payload=p.payload,
                        )
                    )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unhandled error in %s adapter", self._source_key)
            result.errors.append(str(exc))
        return result
