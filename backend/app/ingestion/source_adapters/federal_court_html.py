"""Adapter for the Federal Court of Canada decisions HTML site.

Handles source key: ``federal_court_canada``
Parser key: ``federal_court_html``
Creates: ``ReviewItem`` records only
Authority: ``official_court_record``

Decision index: https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/nav.do
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


class FederalCourtHtmlAdapter(CanadianSourceAdapter):
    """Scrape Federal Court of Canada decision index for ReviewItem candidates.

    The Federal Court publishes decisions through a bilingual web interface.
    This adapter fetches the English decision index, extracts case links and
    metadata, and produces ``ReviewItem`` records for human review.

    All records require manual review (``requires_manual_review: true``).

    .. note::
        Skeleton implementation.  CSS selectors must be validated against the
        live Federal Court website before production use.  Check the site's
        robots.txt and terms of service.  The ``base_url`` from
        ``SourceRegistry`` should point to the English decision index.
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
        self._allowed_domains_json = (
            allowed_domains_json or '["decisions.fct-cf.gc.ca", "fct-cf.gc.ca"]'
        )
        self._public_record_authority = public_record_authority

    def _parse_index(self, html: str) -> list[dict[str, Any]]:
        """Extract decision entries from the Federal Court index HTML.

        TODO: Replace placeholder selectors with actual Federal Court HTML
        structure once confirmed.
        """
        soup = BeautifulSoup(html, "html.parser")
        items: list[dict[str, Any]] = []
        # Placeholder: look for table rows or list items with case references
        for row in soup.select("table tr"):
            cells = row.find_all("td")
            if not cells:
                continue
            link_tag = row.find("a", href=True)
            if not link_tag:
                continue
            href = str(link_tag["href"])
            full_url = (
                href
                if href.startswith("http")
                else "https://decisions.fct-cf.gc.ca" + href
            )
            items.append(
                {
                    "url": full_url,
                    "headline": link_tag.get_text(strip=True),
                    "date": cells[-1].get_text(strip=True) if len(cells) > 1 else None,
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
            return self._parse_index(resp.text)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to fetch %s: %s", self._source_key, exc)
            return []

    def parse(self, raw: list[dict[str, Any]]) -> list[ParsedRecord]:
        records: list[ParsedRecord] = []
        for item in raw:
            url = item.get("url", "")
            violation = check_record_type_allowed(
                _RECORD_TYPE,
                self._public_record_authority,
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
