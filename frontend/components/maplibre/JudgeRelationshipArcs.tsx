"use client";

// FEATURE NOT ENABLED: relationship arc data endpoint not yet implemented.

/**
 * JudgeRelationshipArcs.tsx — STUB.
 *
 * This component is intentionally a no-op until a backend endpoint exists that
 * returns relationship arc data meeting the following criteria:
 *
 *   1. Only records where `review_status === "approved"` are included.
 *   2. Only records where `evidence_count > 0` are included.
 *   3. Arc labels use neutral, factual language only (e.g. "linked case", not
 *      "co-conspirator" or similar language implying guilt or misconduct).
 *   4. The endpoint is paginated to avoid rendering thousands of arcs at once.
 *
 * Backend endpoint to implement (example):
 *   GET /api/map/relationship-arcs?bbox=...
 *   Response: { type: "FeatureCollection", features: ArcFeature[] }
 *
 * Once implemented, replace this stub with:
 *   - A `useEffect` that loads arc data via useJudgeMap()
 *   - A MapLibre `line` layer rendered on the SOURCE_ID.EVENTS source
 *   - Tooltip labels using record.relationship_label (must be pre-approved copy)
 *
 * Do NOT remove this stub until all four criteria above are met.
 */

export default function JudgeRelationshipArcs() {
  return null;
}
