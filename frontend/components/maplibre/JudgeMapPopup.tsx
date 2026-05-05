"use client";

/**
 * JudgeMapPopup.tsx — React sidebar panel shown when a map record is selected.
 *
 * Renders the record title, type badge, date, city, source count, and a
 * "View full record" button to open MapRecordDrawer.
 *
 * Language note: all display text describes factual public data only;
 * this component must never imply guilt, culpability, or misconduct.
 */

import type { JudgeMapRecord } from "./types";
import { MAP_DISCLAIMER } from "./constants";

type Props = {
  record: JudgeMapRecord;
  onOpenDrawer: () => void;
  onClose: () => void;
};

const TYPE_LABEL: Record<string, string> = {
  court_event: "Court Event",
  reported_incident: "Reported Incident",
};

function fmt(dateStr: string | null): string {
  if (!dateStr) return "Date not recorded";
  const d = new Date(dateStr);
  return isNaN(d.getTime()) ? dateStr : d.toLocaleDateString("en-CA", { dateStyle: "medium" });
}

export default function JudgeMapPopup({ record, onOpenDrawer, onClose }: Props) {
  const typeLabel = TYPE_LABEL[record.record_type] ?? record.record_type;
  const location = [record.city, record.state_province].filter(Boolean).join(", ") || "Location on file";

  return (
    <div className="absolute top-4 left-4 z-10 w-72 rounded-lg border border-gray-200 bg-white shadow-lg">
      {/* Header */}
      <div className="flex items-start justify-between gap-2 p-3 border-b border-gray-100">
        <div className="flex-1 min-w-0">
          <span
            className={
              record.record_type === "court_event"
                ? "inline-block mb-1 px-2 py-0.5 text-xs font-medium rounded bg-blue-100 text-blue-700"
                : "inline-block mb-1 px-2 py-0.5 text-xs font-medium rounded bg-amber-100 text-amber-700"
            }
          >
            {typeLabel}
          </span>
          <p className="text-sm font-semibold text-gray-900 leading-snug line-clamp-2">
            {record.title}
          </p>
        </div>
        <button
          onClick={onClose}
          className="shrink-0 mt-0.5 p-1 rounded hover:bg-gray-100 text-gray-500"
          aria-label="Close preview"
        >
          ✕
        </button>
      </div>

      {/* Meta */}
      <div className="p-3 space-y-1 text-xs text-gray-600">
        <p>
          <span className="font-medium">Date:</span> {fmt(record.date)}
        </p>
        <p>
          <span className="font-medium">Location:</span> {location}
        </p>
        <p>
          <span className="font-medium">Sources:</span> {record.source_count}
          {record.has_news && (
            <span className="ml-2 px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">
              + news context
            </span>
          )}
        </p>
      </div>

      {/* Disclaimer */}
      <p className="px-3 pb-2 text-[10px] text-gray-400 leading-tight">{MAP_DISCLAIMER}</p>

      {/* Action */}
      <div className="px-3 pb-3">
        <button
          onClick={onOpenDrawer}
          className="w-full rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 transition-colors"
        >
          View full record
        </button>
      </div>
    </div>
  );
}
