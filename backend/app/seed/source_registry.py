"""Seed the source_registry table with known ingestion sources.

Idempotent: skips any row whose source_key already exists.
Fail-closed: all sources default to is_active=False.

Dev override: set JTA_CANADA_FIRST_DEV_ENABLE_SASKATOON=true *and*
APP_ENV=development to activate the saskatoon_crime pipeline locally.

Run standalone:
    python -m app.seed.source_registry
"""
from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import SourceRegistry

# Activate saskatoon_crime only in explicit dev mode
_SASKATOON_ACTIVE: bool = (
    os.environ.get("JTA_CANADA_FIRST_DEV_ENABLE_SASKATOON", "").lower() in ("1", "true", "yes")
    and os.environ.get("APP_ENV", "production").lower() == "development"
)

_SOURCES: list[dict] = [
    # --- Canadian municipal (Phase 1) ---
    {
        "source_key": "saskatoon_crime",
        "source_name": "saskatoon_police",
        "country": "Canada",
        "province_state": "SK",
        "city": "Saskatoon",
        "source_type": "crime_incident",
        "source_tier": "official_police_open_data",
        "fetch_method": "upload",
        "update_cadence": "manual",
        "fields_supported": "incident_type,reported_date,neighbourhood",
        "precision_level": "city_centroid",
        "auto_publish_enabled": False,
        "requires_manual_review": True,
        "is_active": _SASKATOON_ACTIVE,
    },
    {
        "source_key": "toronto_crime",
        "source_name": "toronto_police",
        "country": "Canada",
        "province_state": "ON",
        "city": "Toronto",
        "source_type": "crime_incident",
        "source_tier": "official_police_open_data",
        "fetch_method": "upload",
        "update_cadence": "manual",
        "fields_supported": "incident_type,reported_date,neighbourhood",
        "precision_level": "city_centroid",
        "auto_publish_enabled": False,
        "requires_manual_review": True,
        "is_active": False,
    },
    # --- Canadian federal/national ---
    {
        "source_key": "statscan",
        "source_name": "statistics_canada",
        "country": "Canada",
        "source_type": "aggregate_stats",
        "source_tier": "official_government_statistics",
        "fetch_method": "http",
        "update_cadence": "annual",
        "fields_supported": "crime_rate,incident_type,province",
        "precision_level": "province_centroid",
        "auto_publish_enabled": False,
        "requires_manual_review": True,
        "is_active": False,
    },
    # --- Canadian web monitor ---
    {
        "source_key": "web_monitor_saskatoon_police_news",
        "source_name": "saskatoon_police_news",
        "country": "Canada",
        "province_state": "SK",
        "city": "Saskatoon",
        "source_type": "news_monitor",
        "source_tier": "news_only_context",
        "fetch_method": "http",
        "update_cadence": "daily",
        "precision_level": "city_centroid",
        "auto_publish_enabled": False,
        "requires_manual_review": True,
        "is_active": False,
    },
    # --- US sources (disabled; kept for registry completeness) ---
    {
        "source_key": "courtlistener",
        "source_name": "courtlistener",
        "country": "USA",
        "source_type": "court_record",
        "source_tier": "court_record",
        "fetch_method": "http",
        "update_cadence": "daily",
        "precision_level": "address",
        "auto_publish_enabled": False,
        "requires_manual_review": True,
        "is_active": False,
    },
    {
        "source_key": "courtlistener_bulk",
        "source_name": "courtlistener_bulk",
        "country": "USA",
        "source_type": "court_record",
        "source_tier": "court_record",
        "fetch_method": "http",
        "update_cadence": "manual",
        "precision_level": "address",
        "auto_publish_enabled": False,
        "requires_manual_review": True,
        "is_active": False,
    },
    {
        "source_key": "fbi_crime",
        "source_name": "fbi_ucr",
        "country": "USA",
        "source_type": "aggregate_stats",
        "source_tier": "official_government_statistics",
        "fetch_method": "http",
        "update_cadence": "annual",
        "precision_level": "national",
        "auto_publish_enabled": False,
        "requires_manual_review": True,
        "is_active": False,
    },
    {
        "source_key": "chicago_crime",
        "source_name": "chicago_police",
        "country": "USA",
        "province_state": "IL",
        "city": "Chicago",
        "source_type": "crime_incident",
        "source_tier": "official_police_open_data",
        "fetch_method": "http",
        "update_cadence": "daily",
        "precision_level": "block_level",
        "auto_publish_enabled": False,
        "requires_manual_review": True,
        "is_active": False,
    },
    {
        "source_key": "la_crime",
        "source_name": "lapd",
        "country": "USA",
        "province_state": "CA",
        "city": "Los Angeles",
        "source_type": "crime_incident",
        "source_tier": "official_police_open_data",
        "fetch_method": "http",
        "update_cadence": "daily",
        "precision_level": "block_level",
        "auto_publish_enabled": False,
        "requires_manual_review": True,
        "is_active": False,
    },
    {
        "source_key": "gdelt",
        "source_name": "gdelt",
        "country": "Global",
        "source_type": "news_monitor",
        "source_tier": "news_only_context",
        "fetch_method": "http",
        "update_cadence": "daily",
        "precision_level": "city_centroid",
        "auto_publish_enabled": False,
        "requires_manual_review": True,
        "is_active": False,
    },
]


def seed_source_registry(db: Session) -> None:
    """Insert source registry rows that do not yet exist (idempotent)."""
    for spec in _SOURCES:
        existing = db.scalar(
            select(SourceRegistry).where(SourceRegistry.source_key == spec["source_key"])
        )
        if existing is not None:
            continue
        db.add(SourceRegistry(**spec))
    db.commit()


if __name__ == "__main__":
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        seed_source_registry(db)
    print("source_registry seeded")
