/**
 * types.ts — JudgeMapRecord shared type + adapters from lib/api shapes.
 *
 * Language note: all copy that appears on screen must describe factual records
 * from public judicial/incident data. Do not imply guilt, culpability, or
 * misconduct of any named person.
 */

import type { MapFeature, CrimeIncidentFeature, MapDotRecord } from "@/lib/api";

/** Unified map record consumed by all MapLibre components. */
export type JudgeMapRecord = {
  id: string | number;
  record_type: "court_event" | "reported_incident";
  /** [longitude, latitude] — MapLibre coordinate order */
  coordinates: [number, number];
  title: string;
  date: string | null;
  city: string | null;
  state_province: string | null;
  source_count: number;
  has_news: boolean;
  has_links: boolean;
  disclaimer: string;
};

/** Adapt a court-event GeoJSON feature to JudgeMapRecord. */
export function courtEventToMapRecord(f: MapFeature): JudgeMapRecord {
  const p = f.properties;
  return {
    id: p.event_id,
    record_type: "court_event",
    coordinates: f.geometry.coordinates as [number, number],
    title: p.title,
    date: p.event_date ?? p.decision_date ?? null,
    city: p.location_name ?? null,
    state_province: null,
    source_count: p.source_count,
    has_news: p.has_news,
    has_links: p.has_incident_links,
    disclaimer: p.disclaimer,
  };
}

/** Adapt a crime-incident GeoJSON feature to JudgeMapRecord. */
export function crimeIncidentToMapRecord(f: CrimeIncidentFeature): JudgeMapRecord {
  const p = f.properties;
  return {
    id: p.incident_id,
    record_type: "reported_incident",
    coordinates: f.geometry.coordinates as [number, number],
    title: `${p.incident_category}: ${p.incident_type}`,
    date: p.reported_at ?? p.occurred_at ?? null,
    city: p.city ?? null,
    state_province: p.province_state ?? null,
    source_count: p.source_count,
    has_news: p.has_news,
    has_links: p.has_court_links,
    disclaimer: p.disclaimer,
  };
}

/** Adapt JudgeMapRecord to MapDotRecord for use with MapRecordDrawer. */
export function judgeMapRecordToMapDotRecord(r: JudgeMapRecord): MapDotRecord {
  return {
    id: r.id,
    record_type: r.record_type,
    latitude: r.coordinates[1],
    longitude: r.coordinates[0],
    title: r.title,
    date: r.date,
    city: r.city,
    state_province: r.state_province,
    source_count: r.source_count,
    has_news: r.has_news,
    disclaimer: r.disclaimer,
  };
}
