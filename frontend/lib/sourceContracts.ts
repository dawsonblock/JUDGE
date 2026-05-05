/**
 * Canonical authority and tier types for the source registry UI.
 *
 * `PublicRecordAuthority` must stay in sync with the `public_record_authority`
 * column values written by the database seed / YAML loader.
 *
 * `SourceTier` must stay in sync with the `source_tier` column values.
 */

// ---------------------------------------------------------------------------
// Authority
// ---------------------------------------------------------------------------

export type PublicRecordAuthority =
  | "official_open_data"
  | "official_statistics"
  | "official_government"
  | "official_legislation"
  | "official_court_record"
  | "news_context"
  | "unknown";

/** Tailwind colour classes keyed by authority.  Exhaustive — add here when adding to the DB. */
export const AUTHORITY_COLOURS: Record<PublicRecordAuthority, string> = {
  official_open_data: "bg-blue-100 text-blue-800",
  official_statistics: "bg-indigo-100 text-indigo-800",
  official_government: "bg-violet-100 text-violet-800",
  official_legislation: "bg-purple-100 text-purple-800",
  official_court_record: "bg-cyan-100 text-cyan-800",
  news_context: "bg-amber-100 text-amber-800",
  unknown: "bg-gray-100 text-gray-600",
};

/** Human-readable labels for authority values. */
export const AUTHORITY_LABELS: Record<PublicRecordAuthority, string> = {
  official_open_data: "Official Open Data",
  official_statistics: "Official Statistics",
  official_government: "Official Government",
  official_legislation: "Official Legislation",
  official_court_record: "Official Court Record",
  news_context: "News Context",
  unknown: "Unknown",
};

/**
 * Returns the Tailwind colour string for `authority`, falling back to
 * `unknown` when the value is not one of the canonical set.
 */
export function authorityColour(authority: string): string {
  return (
    AUTHORITY_COLOURS[authority as PublicRecordAuthority] ??
    AUTHORITY_COLOURS.unknown
  );
}

// ---------------------------------------------------------------------------
// Tier
// ---------------------------------------------------------------------------

export type SourceTier =
  | "court_record"
  | "official_police_open_data"
  | "official_government_statistics"
  | "verified_news_context"
  | "news_only_context";

export const SOURCE_TIER_COLOURS: Record<SourceTier, string> = {
  court_record: "bg-cyan-100 text-cyan-800",
  official_police_open_data: "bg-blue-100 text-blue-800",
  official_government_statistics: "bg-indigo-100 text-indigo-800",
  verified_news_context: "bg-amber-100 text-amber-800",
  news_only_context: "bg-gray-100 text-gray-600",
};

export const SOURCE_TIER_LABELS: Record<SourceTier, string> = {
  court_record: "Court Record",
  official_police_open_data: "Official Police Open Data",
  official_government_statistics: "Official Government Statistics",
  verified_news_context: "Verified News Context",
  news_only_context: "News Only Context",
};

/**
 * Returns the Tailwind colour string for `tier`, falling back to
 * `news_only_context` when the value is not one of the canonical set.
 */
export function tierColour(tier: string): string {
  return (
    SOURCE_TIER_COLOURS[tier as SourceTier] ??
    SOURCE_TIER_COLOURS.news_only_context
  );
}
