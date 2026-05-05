export type EventItem = {
  event_id: string;
  court_id: number;
  judge_id: number | null;
  case_id: number;
  primary_location_id: number;
  event_type: string;
  event_subtype: string | null;
  decision_result: string | null;
  decision_date: string | null;
  posted_date: string | null;
  title: string;
  summary: string;
  repeat_offender_indicator: boolean;
  repeat_offender_indicators: string[];
  verification_status: string | null;
  source_excerpt: string | null;
  is_mappable: boolean;
  location_status: "mapped" | "court_location_pending";
  verified_flag: boolean;
  source_quality: string;
  review_status: string;
  court?: { id: number; name: string; courtlistener_id: string; region: string | null } | null;
  judge?: { id: number; name: string } | null;
  defendants: { id: number; anonymized_id: string; display_label: string }[];
  sources: { id: number; source_id: string; source_type: string; title: string; url: string; source_quality: string; verified_flag: boolean; review_status: string }[];
  outcomes: { id: number; outcome_type: string; outcome_date: string | null; summary: string }[];
  outcome_status: string | null;
};

export type MapFeature = {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: {
    record_type: "court_event";
    event_id: string;
    judge_id: number | null;
    judge_name: string;
    court_id: number | null;
    court_name: string | null;
    location_id: number;
    location_name: string;
    title: string;
    event_type: string;
    event_date: string | null;
    case_id: number | null;
    case_name: string | null;
    case_number: string | null;
    decision_date: string | null;
    court: string | null;
    judge: string | null;
    repeat_offender_indicator: boolean;
    verified_flag: boolean;
    review_status: string;
    location_status: "mapped";
    is_mappable: true;
    source_quality: string;
    defendants: string[];
    source_count: number;
    has_news: boolean;
    has_incident_links: boolean;
    disclaimer: string;
  };
};

export type FeatureCollection = {
  type: "FeatureCollection";
  features: MapFeature[];
  returned_count: number;
  truncated: boolean;
  filters_applied: Record<string, unknown>;
  disclaimer: string;
};

export type CrimeIncidentFeature = {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: {
    record_type: "reported_incident";
    incident_id: number;
    incident_type: string;
    incident_category: string;
    reported_at: string | null;
    occurred_at: string | null;
    city: string | null;
    province_state: string | null;
    country: string | null;
    area_label: string | null;
    precision_level: string;
    source_name: string;
    source_url: string | null;
    verification_status: string;
    review_status: string;
    source_count: number;
    has_news: boolean;
    has_court_links: boolean;
    is_aggregate: boolean;
    disclaimer: string;
  };
};

export type SourceLink = {
  label: string;
  url: string;
  source_type: string;
  supports_claim: string;
  retrieved_at: string | null;
  snapshot_hash?: string;
  is_context_only?: boolean;
};

export type RelatedCourtRecord = {
  event_id: string;
  case_name: string | null;
  judge_name: string | null;
  decision_type: string;
  date: string | null;
  relationship_status: string;
  url: string | null;
};

export type RelatedIncident = {
  incident_id: number;
  category: string;
  date: string | null;
  city: string | null;
  relationship_status: string;
};

export type RecordAudit = {
  review_status: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  last_updated: string | null;
};

export type RecordDetail = {
  record_type: "court_event" | "reported_incident";
  id: string | number;
  title?: string;
  event_type?: string;
  event_subtype?: string | null;
  date: string | null;
  court_name?: string | null;
  court_location?: string | null;
  judge_name?: string | null;
  case_name?: string | null;
  docket_number?: string | null;
  category?: string;
  incident_type?: string;
  city?: string | null;
  state_province?: string | null;
  country?: string | null;
  area_label?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  precision_level?: string;
  summary: string;
  source_links: SourceLink[];
  news_articles: SourceLink[];
  related_court_records: RelatedCourtRecord[];
  related_reported_incidents: RelatedIncident[];
  audit: RecordAudit;
  disclaimer: string;
  news_context_note: string;
  // Badge display properties
  source_tier?: string;
  source_quality?: string;
  review_status?: string;
  confidence?: number;
  warnings?: string[];
  evidence_count?: number;
  source_count?: number;
  verification_status?: string;
};

export type MapDotRecord = {
  id: string | number;
  record_type: "court_event" | "reported_incident";
  latitude: number;
  longitude: number;
  title: string;
  date: string | null;
  city: string | null;
  state_province?: string | null;
  source_count: number;
  has_news: boolean;
  disclaimer: string;
};

export type SourcePanelItem = {
  source_name: string;
  source_type: string;
  source_url: string | null;
  retrieved_at: string | null;
  published_at: string | null;
  quoted_excerpt: string | null;
  verification_status: string;
  trust_reason: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_status: string;
};

export type SourcePanelData = {
  entity_type: string;
  entity_id: string | number;
  review_status: string;
  sources: SourcePanelItem[];
};

export type CrimeIncidentFeatureCollection = {
  type: "FeatureCollection";
  features: CrimeIncidentFeature[];
  returned_count: number;
  truncated: boolean;
  filters_applied: Record<string, unknown>;
  disclaimer: string;
};

const publicBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const serverBase = process.env.BACKEND_INTERNAL_URL || publicBase;

export function apiBase(isServer = typeof window === "undefined") {
  return isServer ? serverBase : publicBase;
}

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase()}${path}`, { cache: "no-store", ...init });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export type ChatCitation = {
  evidence_id: number;
  relationship_type: string;
  evidence_type: string;
  evidence_source: string;
  excerpt: string | null;
  confidence: number;
};

export type ChatResponse = {
  question: string;
  answer: string;
  citations: ChatCitation[];
  disclaimer: string;
  incident_found: boolean;
};

export async function fetchCrimeIncidents(
  filters?: Record<string, string>,
): Promise<CrimeIncidentFeatureCollection> {
  const params = filters ? "?" + new URLSearchParams(filters).toString() : "";
  return fetchJson<CrimeIncidentFeatureCollection>(`/api/map/crime-incidents${params}`);
}

export async function chatAboutEvidence(
  question: string,
  opts?: { incident_id?: number; case_id?: number },
): Promise<ChatResponse> {
  return fetchJson<ChatResponse>("/api/chat/evidence", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, ...opts }),
  });
}

// ── Real-data types ──────────────────────────────────────────────────────────

export type JudgeSummary = {
  id: number;
  name: string;
  court_id: number | null;
  cl_person_id: string | null;
  public_event_count: number;
};

export type CaseItem = {
  id: number;
  court_id: number;
  docket_number: string;
  caption: string;
  case_type: string;
  filed_date: string | null;
  terminated_date: string | null;
};

export type SourceItem = {
  id: number;
  source_id: string;
  source_type: string;
  title: string;
  url: string;
  source_quality: string;
  verified_flag: boolean;
  review_status: string;
};

export type AdminSourceItem = {
  id: number;
  source_key: string;
  source_name: string;
  source_type: string;
  country: string | null;
  province_state: string | null;
  city: string | null;
  source_tier: import("./sourceContracts").SourceTier | string;
  is_active: boolean;
  rate_limit_rpm: number | null;
  health_score: number;
  last_successful_fetch: string | null;
  last_ingested_at: string | null;
  admin_notes: string | null;
  auto_publish_enabled: boolean;
  requires_manual_review: boolean;
  created_at: string;
  updated_at: string;
  // Canada-first metadata
  jurisdiction: string | null;
  category: string | null;
  priority: number;
  enabled_default: boolean;
  public_record_authority: import("./sourceContracts").PublicRecordAuthority | string;
  base_url: string | null;
  allowed_domains: string | null;
  refresh_interval_minutes: number | null;
  parser: string | null;
  creates: string | null;
  public_publish_default: boolean;
  terms_url: string | null;
};

export type SourceRunResult = {
  source_key: string;
  records_fetched: number;
  records_skipped: number;
  created_records: number;
  review_items: number;
  errors: string[];
  success: boolean;
};

export type DefendantItem = {
  id: number;
  anonymized_id: string;
  display_label: string;
  warning: string;
};

export type AdminReviewItem = {
  entity_type: string;
  entity_id: string | number;
  database_id: number;
  title: string | null;
  source_type: string | null;
  review_status: string;
  public_visibility: boolean;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
  correction_note: string | null;
  dispute_note: string | null;
};

export type AdminReviewQueue = {
  items: AdminReviewItem[];
  total_count: number;
};

// ── Fetch helpers ────────────────────────────────────────────────────────────

export async function fetchJudges(): Promise<JudgeSummary[]> {
  return fetchJson<JudgeSummary[]>("/api/judges");
}

export async function fetchJudge(id: number | string): Promise<JudgeSummary> {
  return fetchJson<JudgeSummary>(`/api/judges/${id}`);
}

export async function fetchJudgeEvents(id: number | string): Promise<EventItem[]> {
  return fetchJson<EventItem[]>(`/api/judges/${id}/events`);
}

export async function fetchCases(): Promise<CaseItem[]> {
  return fetchJson<CaseItem[]>("/api/cases");
}

export async function fetchCase(id: number | string): Promise<CaseItem> {
  return fetchJson<CaseItem>(`/api/cases/${id}`);
}

export async function fetchCaseTimeline(id: number | string): Promise<EventItem[]> {
  return fetchJson<EventItem[]>(`/api/cases/${id}/timeline`);
}

export async function fetchDefendant(id: number | string): Promise<DefendantItem> {
  return fetchJson<DefendantItem>(`/api/defendants/${id}`);
}

export async function fetchDefendantTimeline(id: number | string): Promise<EventItem[]> {
  return fetchJson<EventItem[]>(`/api/defendants/${id}/timeline`);
}

export async function fetchEventsList(
  params?: Record<string, string>,
): Promise<EventItem[]> {
  const q = params ? "?" + new URLSearchParams(params).toString() : "";
  return fetchJson<EventItem[]>(`/api/events${q}`);
}

export async function fetchSources(): Promise<SourceItem[]> {
  return fetchJson<SourceItem[]>("/api/sources");
}

export async function fetchAdminSourcesList(token: string): Promise<AdminSourceItem[]> {
  return fetchJson<AdminSourceItem[]>("/api/admin/sources", {
    headers: { "x-jta-admin-token": token },
  });
}

export async function triggerSourceRun(
  token: string,
  sourceKey: string,
): Promise<SourceRunResult> {
  return fetchJson<SourceRunResult>(`/api/admin/sources/${sourceKey}/run`, {
    method: "POST",
    headers: { "x-jta-admin-token": token },
  });
}

export async function fetchAdminReviewQueue(
  token: string,
  params?: { entity_type?: string; review_status?: string; limit?: number },
): Promise<AdminReviewQueue> {
  const entries = Object.entries(params ?? {}).filter(([, v]) => v != null) as [
    string,
    string,
  ][];
  const q = entries.length
    ? "?" + new URLSearchParams(Object.fromEntries(entries.map(([k, v]) => [k, String(v)]))).toString()
    : "";
  return fetchJson<AdminReviewQueue>(`/api/admin/review-queue${q}`, {
    headers: { "x-jta-admin-token": token },
  });
}
