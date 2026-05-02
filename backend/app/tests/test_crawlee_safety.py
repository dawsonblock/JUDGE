"""Test that Crawlee-generated review items have correct safety defaults."""
import pytest
from datetime import datetime, timezone
from app.models.entities import ReviewItem, SourceSnapshot, IngestionRun
from app.ingestion.web_monitor.crawlee_runner import CrawleeRunner
from app.ingestion.web_monitor.source_targets import SASKATOON_POLICE_NEWS_TARGET


def test_crawlee_review_items_safety_defaults(db_session):
    """Test that Crawlee review items have correct safety defaults.
    
    All Crawlee-created review items must have:
    - status="pending" (never auto-publish)
    - public_visibility absent or False
    - confidence <= 0.5 (hard cap)
    - publish_recommendation="review_required"
    """
    # Create mock ingestion run
    run = IngestionRun(
        source_name="test_crawlee",
        started_at=datetime.now(timezone.utc),
        status="running",
    )
    db_session.add(run)
    db_session.flush()
    
    # Create mock snapshot
    snapshot = SourceSnapshot(
        source_url="https://saskatoonpolice.ca/test",
        fetched_at=datetime.now(timezone.utc),
        raw_content=b"test content",
        raw_content_hash="test_hash",
        extracted_text="extracted test",
        http_status=200,
        content_type="text/html",
        error_message=None,
        ingestion_run_id=run.id,
    )
    db_session.add(snapshot)
    db_session.flush()
    
    # Create runner
    runner = CrawleeRunner(SASKATOON_POLICE_NEWS_TARGET, db_session)
    
    # Create mock extracted candidate
    from app.ingestion.web_monitor.extractors import ExtractedCandidate
    
    candidate = ExtractedCandidate(
        candidate_type="crime_incident",
        title="Test Incident",
        summary="A test incident summary",
        source_url="https://saskatoonpolice.ca/test",
        location_text="Saskatoon, SK",
        published_at=datetime.now(timezone.utc),
        confidence=0.8,  # Should be capped to 0.5
        entities=[],
        warnings=["contains_address"],
    )
    
    # Create review item via runner
    review_item = runner._create_review_item(candidate, snapshot, run.id)
    db_session.add(review_item)
    db_session.flush()
    
    # Assert safety defaults
    assert review_item.status == "pending", "All crawled items must be pending review"
    assert review_item.public_visibility != True, "Crawled items must not be public by default"
    assert review_item.confidence <= 0.5, f"Confidence must be capped at 0.5, got {review_item.confidence}"
    assert review_item.publish_recommendation == "review_required", "Must require human review"
    assert review_item.privacy_status == "needs_review", "Address warning triggers privacy review"
    assert review_item.source_snapshot_id == snapshot.id, "Must link to source snapshot"


def test_crawlee_review_item_confidence_capped(db_session):
    """Test that high confidence scores are capped to 0.5."""
    run = IngestionRun(
        source_name="test_confidence",
        started_at=datetime.now(timezone.utc),
        status="running",
    )
    db_session.add(run)
    db_session.flush()
    
    snapshot = SourceSnapshot(
        source_url="https://example.com/test",
        fetched_at=datetime.now(timezone.utc),
        raw_content=b"test",
        raw_content_hash="hash",
        extracted_text="extracted",
        http_status=200,
        content_type="text/html",
        ingestion_run_id=run.id,
    )
    db_session.add(snapshot)
    db_session.flush()
    
    runner = CrawleeRunner(SASKATOON_POLICE_NEWS_TARGET, db_session)
    
    from app.ingestion.web_monitor.extractors import ExtractedCandidate
    
    # Test with very high confidence
    candidate = ExtractedCandidate(
        candidate_type="court_event",
        title="High Confidence Event",
        summary="Test",
        source_url="https://example.com/test",
        location_text="Test Location",
        published_at=datetime.now(timezone.utc),
        confidence=0.99,  # Extremely high
        entities=[],
        warnings=[],
    )
    
    review_item = runner._create_review_item(candidate, snapshot, run.id)
    
    assert review_item.confidence == 0.5, "Confidence must be capped at 0.5, regardless of input"
