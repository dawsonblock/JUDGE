"""Adapter for Canada's Laws-Justice.gc.ca legislation site.

Handles source key: ``canada_justice_laws``
Parser key: ``laws_justice_html``
Creates: ``ReviewItem`` records only
Authority: ``official_legislation``

Source: https://laws-lois.justice.gc.ca/

Note: Legislation records are informational and do not directly identify
individuals.  These ReviewItem records are used to track relevant statute
changes affecting criminal justice.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.ingestion.adapters import (
    CreatedReviewItem,
    IngestionResult,
    ParsedRecord,
    SourceAdapter,
)
from app.ingestion.source_rules import check_domain_allowed, check_record_type_allowed

logger = logging.getLogger(__name__)

_RECORD_TYPE = "ReviewItem"
_PUBLIC_RECORD_AUTHORITY = "official_legislation"


class LawsJusticeHtmlAdapter(SourceAdapter):
    """Fetch recent amendments from laws-lois.justice.gc.ca.

    Monitors the Justice Laws website for newly published or amended statutes
    relevant to criminal justice (Criminal Code, Youth Criminal Justice Act, etc.)
    and creates ``ReviewItem`` records for editorial review.

    .. note::
        Skeleton implementation.  The ``_parse_recently_amended()`` method
        requires the actual page structure from laws-lois.justice.gc.ca to
        be validated.  The ``base_url`` from ``SourceRegistry`` should point
        to the "recently amended" or "table of contents" page for the target
        acts (e.g. https://laws-lois.justice.gc.ca/eng/acts/C-46/).
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
            allowed_domains_json or '["laws-lois.justice.gc.ca", "justice.gc.ca"]'
        )

    def _parse_recently_amended(self, html: str) -> list[dict[str, Any]]:
        """Extract recently amended acts or provisions from HTML.

        TODO: Validate against actual laws-lois.justice.gc.ca page structure.
        """
        soup = BeautifulSoup(html, "html.parser")
        items: list[dict[str, Any]] = []
        for link in soup.select("a[href]"):
            href = str(link["href"])
            text = link.get_text(strip=True)
            # Filter for section / act links (rough heuristic)
            if not text or len(text) < 3:
                continue
            full_url = (
                href
                if href.startswith("http")
                else "https://laws-lois.justice.gc.ca" + href
            )
            items.append({"url": full_url, "headline": text})
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
            return self._parse_recently_amended(resp.text)
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
                    payload={"headline": item.get("headline"), "url": url},
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
