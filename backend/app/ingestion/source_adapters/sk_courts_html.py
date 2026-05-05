"""Adapter for Saskatchewan Courts HTML decision pages.

Handles source keys: ``sk_courts_qb_decisions``, ``sk_courts_ca_decisions``,
                     ``sk_legislature_hansard`` (reused by ``__init__`` registry)
Parser key: ``sk_courts_html``
Creates: ``ReviewItem`` records only (court decisions require human review before publish)
Authority: ``official_court_record``
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from bs4 import BeautifulSoup

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


class SKCourtsHtmlAdapter(CanadianSourceAdapter):
    """Scrape Saskatchewan Courts decision index and produce ReviewItem candidates.

    The Saskatchewan Courts website lists Queen's Bench and Court of Appeal
    decisions as HTML pages.  This adapter fetches the index, extracts decision
    links and metadata, and creates ``ReviewItem`` records for human review.

    All records require manual review (``requires_manual_review: true``) before
    any defendant or judge associations are persisted publicly.

    .. note::
        Skeleton implementation.  The ``_parse_index_page()`` method must be
        completed with the actual CSS selectors from the live courts website
        once scraping is permitted and tested.  Check ``robots.txt`` and terms
        of service before deploying.
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

    def _parse_index_page(self, html: str) -> list[dict[str, Any]]:
        """Extract decision links from the court decision index page.

        TODO: Replace with actual CSS selectors once the live page structure
        is confirmed.  Each returned dict should have ``url``, ``headline``,
        and optionally ``date`` and ``neutral_citation``.
        """
        soup = BeautifulSoup(html, "html.parser")
        items: list[dict[str, Any]] = []
        # Placeholder: look for <a> tags that look like decision links
        for link in soup.find_all("a", href=True):
            href = str(link["href"])
            if "decision" in href.lower() or "judgment" in href.lower():
                items.append(
                    {
                        "url": (
                            href
                            if href.startswith("http")
                            else self._base_url.rstrip("/") + "/" + href.lstrip("/")
                        ),
                        "headline": link.get_text(strip=True),
                    }
                )
        return items

    def fetch(self) -> list[dict[str, Any]]:
        violation = check_domain_allowed(self._base_url, self._allowed_domains_json)
        if violation:
            logger.warning(
                "Domain check failed for %s: %s", self._source_key, violation.detail
            )
            return []
        try:
            with httpx.Client(
                timeout=30, headers={"User-Agent": "JudgeTracker-Research/1.0"}
            ) as client:
                resp = client.get(self._base_url)
                resp.raise_for_status()
            return self._parse_index_page(resp.text)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to fetch %s: %s", self._source_key, exc)
            return []

    def parse(self, raw: list[dict[str, Any]]) -> list[ParsedRecord]:
        records: list[ParsedRecord] = []
        for item in raw:
            url = item.get("url", "")
            violation = check_record_type_allowed(
                _RECORD_TYPE,
                _PUBLIC_RECORD_AUTHORITY,
                f'["{_RECORD_TYPE}"]',
            )
            if violation:
                continue
            url_violation = check_domain_allowed(url, self._allowed_domains_json)
            if url_violation:
                continue
            records.append(
                ParsedRecord(
                    source_key=self._source_key,
                    record_type=_RECORD_TYPE,
                    external_id=url or None,
                    payload={
                        "headline": item.get("headline"),
                        "url": url,
                        "neutral_citation": item.get("neutral_citation"),
                        "date": item.get("date"),
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
                        extracted_text=None,
                        confidence_score=0.0,
                        payload=p.payload,
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unhandled error in %s adapter", self._source_key)
            result.errors.append(str(exc))
        return result
