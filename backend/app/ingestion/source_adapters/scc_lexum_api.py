"""Adapter for Supreme Court of Canada decisions via the Lexum/SCC API.

Handles source key: ``scc_decisions``
Parser key: ``scc_lexum_api``
Creates: ``ReviewItem`` records only
Authority: ``official_court_record``

SCC decisions: https://decisions.scc-csc.ca/
Lexum SCC search API: https://lexum.com/ (API key required for bulk access)
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.ingestion.adapters import (
    CreatedReviewItem,
    IngestionResult,
    ParsedRecord,
    SourceAdapter,
)
from app.ingestion.source_rules import check_domain_allowed, check_record_type_allowed

logger = logging.getLogger(__name__)

_RECORD_TYPE = "ReviewItem"
_PUBLIC_RECORD_AUTHORITY = "official_court_record"

# Public SCC decision RSS/Atom feed (no API key needed for recent decisions)
_SCC_RSS_URL = "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/rss.do"


class SCCLexumApiAdapter(SourceAdapter):
    """Fetch Supreme Court of Canada decisions and produce ReviewItem candidates.

    The SCC publishes decisions through decisions.scc-csc.ca.  This adapter
    uses the site's RSS feed for recent decisions and, where a Lexum API key
    is available, the full search API for historical data.

    All records require manual review before publication.

    .. note::
        Skeleton implementation.  The RSS parsing uses :mod:`xml.etree.ElementTree`
        to avoid external dependencies.  For historical back-fill, integrate the
        Lexum API with an API key stored in ``LEXUM_API_KEY`` environment variable.
        The ``base_url`` from ``SourceRegistry`` may point to either the RSS feed
        or the Lexum API endpoint depending on configuration.
    """

    def __init__(
        self,
        source_key: str,
        base_url: str,
        api_key: str | None = None,
        allowed_domains_json: str | None = None,
    ) -> None:
        self._source_key = source_key
        self._base_url = base_url
        self._api_key = api_key
        self._allowed_domains_json = (
            allowed_domains_json
            or '["decisions.scc-csc.ca", "scc-csc.ca", "lexum.com"]'
        )

    def _fetch_rss(self) -> list[dict[str, Any]]:
        """Fetch and parse the SCC RSS feed for recent decisions."""
        import xml.etree.ElementTree as ET  # stdlib — safe

        url = _SCC_RSS_URL
        url_violation = check_domain_allowed(url, self._allowed_domains_json)
        if url_violation:
            logger.warning(
                "RSS URL blocked for %s: %s", self._source_key, url_violation.detail
            )
            return []
        try:
            with httpx.Client(
                timeout=30, headers={"User-Agent": "JudgeTracker-Research/1.0"}
            ) as client:
                resp = client.get(url)
                resp.raise_for_status()
            root = ET.fromstring(resp.text)
            items: list[dict[str, Any]] = []
            for item in root.iter("item"):
                entry: dict[str, Any] = {}
                for child in item:
                    tag = child.tag.split("}")[-1]  # strip namespace
                    entry[tag] = child.text
                items.append(entry)
            return items
        except Exception as exc:  # noqa: BLE001
            logger.error("SCC RSS fetch failed for %s: %s", self._source_key, exc)
            return []

    def fetch(self) -> list[dict[str, Any]]:
        if self._api_key:
            # TODO: Implement Lexum API call with self._api_key for bulk/historical
            logger.info(
                "Lexum API key present for %s; bulk fetch not yet implemented — using RSS",
                self._source_key,
            )
        return self._fetch_rss()

    def parse(self, raw: list[dict[str, Any]]) -> list[ParsedRecord]:
        records: list[ParsedRecord] = []
        for item in raw:
            violation = check_record_type_allowed(
                _RECORD_TYPE,
                _PUBLIC_RECORD_AUTHORITY,
                f'["{_RECORD_TYPE}"]',
            )
            if violation:
                continue
            url = item.get("link") or ""
            records.append(
                ParsedRecord(
                    source_key=self._source_key,
                    record_type=_RECORD_TYPE,
                    external_id=url or None,
                    payload={
                        "headline": item.get("title"),
                        "url": url,
                        "published_at": item.get("pubDate"),
                        "description": item.get("description"),
                    },
                    source_url=url,
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
                        extracted_text=p.payload.get("description"),
                        confidence_score=0.0,
                        payload=p.payload,
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unhandled error in %s adapter", self._source_key)
            result.errors.append(str(exc))
        return result
