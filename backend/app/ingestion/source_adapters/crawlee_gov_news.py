"""Adapter for Saskatchewan government news pages via Crawlee.

Handles source key: ``sk_justice_ministry``
Parser key: ``crawlee_gov_news``
Creates: ``ReviewItem`` records only (news context)
Authority: ``news_context``
"""

from __future__ import annotations

import logging
from typing import Any

from app.ingestion.adapters import (
    CanadianSourceAdapter,
    CreatedReviewItem,
    IngestionResult,
    ParsedRecord,
)
from app.ingestion.source_rules import check_domain_allowed, check_record_type_allowed

logger = logging.getLogger(__name__)

_RECORD_TYPE = "ReviewItem"


class CrawleeGovNewsAdapter(CanadianSourceAdapter):
    """Crawl Saskatchewan government news pages and produce ReviewItem candidates.

    Government ministry news pages (e.g. Justice and Attorney General) are
    scraped using Crawlee.  Each news release or announcement creates a
    ``ReviewItem`` for human review.  No auto-publish; all items require
    manual review.

    .. note::
        Skeleton implementation.  Wire up the Crawlee runner from
        ``app.ingestion.web_monitor.crawlee_runner`` when integrating.
        The ``fetch()`` method returns an empty list until the crawler
        is properly configured with the ``base_url`` and appropriate link
        extraction rules.
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
        """Return crawled government news article dicts.

        Each dict should have:
          - ``url``: canonical article URL
          - ``headline``: article headline
          - ``text``: extracted body text
          - ``published_at``: ISO date string (optional)

        TODO: Implement using Crawlee playwright or httpx crawler, integrating
        with the existing ``web_monitor`` infrastructure.
        """
        violation = check_domain_allowed(self._base_url, self._allowed_domains_json)
        if violation:
            logger.warning(
                "Domain check failed for %s: %s", self._source_key, violation.detail
            )
            return []

        raise NotImplementedError(
            f"CrawleeGovNewsAdapter is a stub. Disable source '{self._source_key}'"
            " or implement the Crawlee crawler before use."
        )

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
                        "extracted_text": item.get("text"),
                        "published_at": item.get("published_at"),
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
                        extracted_text=p.payload.get("extracted_text"),
                        confidence_score=0.0,
                        payload=p.payload,
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unhandled error in %s adapter", self._source_key)
            result.errors.append(str(exc))
        return result
