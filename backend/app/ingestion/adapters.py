from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass
class RawRecord:
    source_name: str
    payload: dict[str, Any]


@dataclass
class ParsedRecord:
    source_name: str
    docket_id: str | None = None
    docket_number: str | None = None
    court_code: str | None = None
    court_name: str | None = None
    caption: str | None = None
    date_filed: date | None = None
    date_terminated: date | None = None
    judge_name: str | None = None
    docket_text: str | None = None
    # Docket entry fields for per-entry event creation
    docket_entry_id: str | None = None
    recap_document_id: str | None = None
    entry_number: int | None = None
    entry_date: date | None = None
    entry_description: str | None = None
    document_links: list[str] = field(default_factory=list)
    parties: list[dict[str, Any]] = field(default_factory=list)
    source_url: str | None = None
    source_api_url: str | None = None
    # Fields required by Canadian source adapters
    source_key: str | None = None
    record_type: str | None = None
    external_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    source_public_url: str | None = None
    source_quality: str = "court_record"
    raw: dict[str, Any] = field(default_factory=dict)


# ── Ingestion result types ────────────────────────────────────────────────────


@dataclass
class CreatedRecord:
    """Represents a structured record (e.g. CrimeIncident) created by an adapter."""

    source_key: str
    record_type: str  # e.g. "CrimeIncident"
    external_id: str | None  # stable identifier from the source (for dedup)
    payload: dict[str, Any]  # raw field mapping pre-ORM hydration
    source_url: str | None = None


@dataclass
class CreatedReviewItem:
    """Represents a candidate item queued for human review."""

    source_key: str
    headline: str | None
    url: str | None
    extracted_text: str | None
    confidence_score: float = 0.0
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestionResult:
    """Summary of one adapter run.

    The caller (e.g. a Celery task or the ``/run`` endpoint) should persist
    these lists and pass the result to ``update_source_health``.
    """

    source_key: str
    records_fetched: int = 0
    records_skipped: int = 0
    created_records: list[CreatedRecord] = field(default_factory=list)
    review_items: list[CreatedReviewItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    raw_snapshot_bytes: bytes | None = None
    content_type: str = "application/octet-stream"
    fetch_http_status: int | None = None
    fetch_content_type: str | None = None
    fetch_url: str | None = None

    @property
    def success(self) -> bool:
        return not self.errors


# ── Adapter ABC ───────────────────────────────────────────────────────────────


class SourceAdapter(ABC):
    @abstractmethod
    def fetch(self, since: datetime) -> list[RawRecord]:
        raise NotImplementedError

    @abstractmethod
    def parse(self, raw: RawRecord) -> ParsedRecord:
        raise NotImplementedError

    def parse_many(self, raw: RawRecord) -> list[ParsedRecord]:
        """Parse a raw record into multiple parsed records (one per docket entry).

        Default implementation returns a single record from parse().
        Subclasses can override to emit multiple records per docket.
        """
        return [self.parse(raw)]


class CourtOpinionRSSAdapter(SourceAdapter):
    """Placeholder for official opinion/order feeds."""

    def fetch(self, since: datetime) -> list[RawRecord]:
        return []

    def parse(self, raw: RawRecord) -> ParsedRecord:
        return ParsedRecord(source_name="court_opinion_rss", raw=raw.payload)


class NewsAdapter(SourceAdapter):
    """Placeholder only. News is secondary context and never a primary legal record."""

    def fetch(self, since: datetime) -> list[RawRecord]:
        return []

    def parse(self, raw: RawRecord) -> ParsedRecord:
        return ParsedRecord(
            source_name="news", source_quality="secondary_context", raw=raw.payload
        )


# ── Canadian Source Adapter ABC ───────────────────────────────────────────────


class CanadianSourceAdapter(ABC):
    """Base class for all Canadian / Saskatchewan source adapters.

    Unlike the CourtListener-era ``SourceAdapter``, these adapters operate on
    lists of plain row dicts rather than ``RawRecord`` objects, and the
    ``run()`` method is part of the public contract so callers can invoke it
    uniformly through the factory.
    """

    @abstractmethod
    def fetch(self) -> list[dict[str, Any]]:
        """Fetch raw records from the source. Returns a list of raw row dicts."""
        raise NotImplementedError

    @abstractmethod
    def parse(self, raw: list[dict[str, Any]]) -> list[ParsedRecord]:
        """Transform raw rows into :class:`ParsedRecord` objects."""
        raise NotImplementedError

    @abstractmethod
    def run(self) -> IngestionResult:
        """Execute a full fetch → parse → persist cycle and return an
        :class:`IngestionResult`.  Implementations must populate
        ``created_records`` or ``review_items`` as appropriate for their
        source type.
        """
        raise NotImplementedError
