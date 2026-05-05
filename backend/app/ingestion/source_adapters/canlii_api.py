"""Adapter for CanLII (Canadian Legal Information Institute) API.

Handles source key: ``canlii_sk``
Parser key: ``canlii_api``
Creates: ``ReviewItem`` records only
Authority: ``official_court_record``

CanLII API docs: https://developer.canlii.org/
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.ingestion.adapters import (
    CanadianSourceAdapter,
    CreatedReviewItem,
    IngestionResult,
    ParsedRecord,
)
from app.ingestion.source_rules import check_domain_allowed, check_record_type_allowed

logger = logging.getLogger(__name__)

_RECORD_TYPE = "ReviewItem"
_PUBLIC_RECORD_AUTHORITY = "official_court_record"
_CANLII_API_BASE = "https://api.canlii.org/v1"

# CanLII database ID for Saskatchewan courts
_SK_QB_DB = "skqb"
_SK_CA_DB = "skca"


class CanLIIApiAdapter(CanadianSourceAdapter):
    """Fetch Saskatchewan court decisions from the CanLII API.

    CanLII provides a REST API for searching and retrieving Canadian legal
    decisions.  This adapter queries the Saskatchewan Queen's Bench and Court
    of Appeal databases and creates ``ReviewItem`` records for each decision
    discovered since the last run.

    All records require manual review before any judge/defendant associations
    are published.

    .. note::
        Skeleton implementation.  Requires a CanLII API key stored in the
        environment (``CANLII_API_KEY``).  The ``base_url`` from
        ``SourceRegistry`` should be ``https://api.canlii.org/v1``.
        Pagination logic and incremental-fetch (lastModified filtering) must
        be implemented before production use.
    """

    def __init__(
        self,
        source_key: str,
        base_url: str,
        api_key: str | None = None,
        allowed_domains_json: str | None = None,
        public_record_authority: str | None = None,
    ) -> None:
        self._source_key = source_key
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._allowed_domains_json = (
            allowed_domains_json or '["api.canlii.org", "canlii.org"]'
        )
        self._public_record_authority = public_record_authority

    def _fetch_database(self, database_id: str) -> list[dict[str, Any]]:
        """Fetch recent cases from a single CanLII database."""
        url = f"{self._base_url}/caseBrowse/en/{database_id}/"
        params: dict[str, Any] = {"resultCount": 100}
        if self._api_key:
            params["api_key"] = self._api_key

        url_violation = check_domain_allowed(url, self._allowed_domains_json)
        if url_violation:
            logger.warning(
                "Domain blocked for %s (%s): %s",
                self._source_key,
                database_id,
                url_violation.detail,
            )
            return []

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
            data = resp.json()
            return data.get("cases", [])
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "CanLII fetch failed for %s/%s: %s", self._source_key, database_id, exc
            )
            return []

    def fetch(self) -> list[dict[str, Any]]:
        if not self._api_key:
            logger.warning(
                "No CANLII_API_KEY configured; %s will return no results",
                self._source_key,
            )
            return []
        results: list[dict[str, Any]] = []
        for db in (_SK_QB_DB, _SK_CA_DB):
            for case in self._fetch_database(db):
                case["_db_id"] = db
                results.append(case)
        return results

    def parse(self, raw: list[dict[str, Any]]) -> list[ParsedRecord]:
        records: list[ParsedRecord] = []
        for case in raw:
            violation = check_record_type_allowed(
                _RECORD_TYPE,
                _PUBLIC_RECORD_AUTHORITY,
                f'["{_RECORD_TYPE}"]',
            )
            if violation:
                continue
            case_url = case.get("url") or ""
            records.append(
                ParsedRecord(
                    source_key=self._source_key,
                    record_type=_RECORD_TYPE,
                    external_id=(
                        case.get("caseId", {}).get("en")
                        if isinstance(case.get("caseId"), dict)
                        else case.get("caseId")
                    ),
                    payload={
                        "headline": case.get("title"),
                        "url": case_url,
                        "decision_date": case.get("decisionDate"),
                        "citation": case.get("citation"),
                        "database_id": case.get("_db_id"),
                    },
                    source_url=case_url or self._base_url,
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
                result.review_items.append(
                    CreatedReviewItem(
                        source_key=p.source_key,
                        headline=p.payload.get("headline"),
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
