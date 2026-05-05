"use client";

/**
 * MapV2Workspace — client component that owns fetch state and wires all
 * MapLibre components together for the /map-v2 route.
 *
 * Isolation guarantee: this file and all imports under components/maplibre/
 * are the only new code paths. The existing /map route is not touched.
 *
 * Language note: all user-visible copy in this component describes factual
 * public data only. No language implies guilt, culpability, or misconduct.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useJudgeMap } from "@/components/maplibre/JudgeMap";
import { fetchCrimeIncidents, fetchJson } from "@/lib/api";
import type { CrimeIncidentFeatureCollection, FeatureCollection } from "@/lib/api";
import JudgeMapClient from "@/components/maplibre/JudgeMapClient";
import JudgeClusterLayer from "@/components/maplibre/JudgeClusterLayer";
import JudgeMapControls from "@/components/maplibre/JudgeMapControls";
import JudgeMapLegend from "@/components/maplibre/JudgeMapLegend";
import JudgeMapPopup from "@/components/maplibre/JudgeMapPopup";
import JudgeRelationshipArcs from "@/components/maplibre/JudgeRelationshipArcs";
import JudgeMapDrawerBridge from "@/components/maplibre/JudgeMapDrawerBridge";
import type { JudgeMapRecord } from "@/components/maplibre/types";

type LoadState = "idle" | "loading" | "error";

/**
 * Attaches moveend/zoomend listeners to the MapLibre instance (via context)
 * and calls onBoundsChange with a debounced "west,south,east,north" bbox string.
 * Must be rendered inside a JudgeMap tree to access MapLibreContext.
 */
function BoundsTracker({ onBoundsChange }: { onBoundsChange: (bbox: string) => void }) {
  const map = useJudgeMap();
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!map) return;
    const update = () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        const b = map.getBounds();
        const bbox = [
          b.getWest().toFixed(4),
          b.getSouth().toFixed(4),
          b.getEast().toFixed(4),
          b.getNorth().toFixed(4),
        ].join(",");
        onBoundsChange(bbox);
      }, 300);
    };
    map.on("moveend", update);
    map.on("zoomend", update);
    return () => {
      map.off("moveend", update);
      map.off("zoomend", update);
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [map, onBoundsChange]);

  return null;
}

export default function MapV2Workspace() {
  const [incidents, setIncidents] = useState<CrimeIncidentFeatureCollection | null>(null);
  const [events, setEvents] = useState<FeatureCollection | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [selectedRecord, setSelectedRecord] = useState<JudgeMapRecord | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [bbox, setBbox] = useState<string | null>(null);

  useEffect(() => {
    setLoadState("loading");
    const bboxParams = bbox ? { bbox } : undefined;
    const eventsUrl = bbox ? `/api/map/events?bbox=${bbox}` : "/api/map/events";
    Promise.all([
      fetchCrimeIncidents(bboxParams),
      fetchJson<FeatureCollection>(eventsUrl),
    ])
      .then(([inc, evt]) => {
        setIncidents(inc);
        setEvents(evt);
        setLoadState("idle");
      })
      .catch(() => setLoadState("error"));
  }, [bbox]);

  const handleSelect = useCallback((record: JudgeMapRecord) => {
    setSelectedRecord(record);
    setDrawerOpen(false); // show popup first; user clicks "View full record"
  }, []);

  const handleOpenDrawer = useCallback(() => {
    setDrawerOpen(true);
  }, []);

  const handleClosePopup = useCallback(() => {
    setSelectedRecord(null);
    setDrawerOpen(false);
  }, []);

  const handleCloseDrawer = useCallback(() => {
    setDrawerOpen(false);
  }, []);

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Route header */}
      <div className="shrink-0 flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-white">
        <div>
          <h1 className="text-sm font-semibold text-gray-800">
            Public Records Map{" "}
            <span className="ml-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-indigo-100 text-indigo-600 align-middle">
              v2 · MapLibre
            </span>
          </h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Showing publicly reviewed court events and reported incidents
          </p>
        </div>
        {loadState === "loading" && (
          <span className="text-xs text-gray-400 animate-pulse">Loading records…</span>
        )}
        {loadState === "error" && (
          <span className="text-xs text-red-500">Failed to load records — check API</span>
        )}
        {loadState === "idle" && (incidents || events) && (
          <span className="text-xs text-gray-500">
            {(incidents?.returned_count ?? 0) + (events?.features.length ?? 0)} records
          </span>
        )}
      </div>

      {/* Map + sidebar */}
      <div className="flex flex-1 overflow-hidden">
        {/* Map */}
        <div className="relative flex-1">
          <JudgeMapClient className="w-full h-full">
            <BoundsTracker onBoundsChange={setBbox} />
            <JudgeClusterLayer
              incidents={incidents}
              events={events}
              onSelectRecord={handleSelect}
            />
            <JudgeMapControls />
            <JudgeMapLegend />
            <JudgeRelationshipArcs />
            {selectedRecord && !drawerOpen && (
              <JudgeMapPopup
                record={selectedRecord}
                onOpenDrawer={handleOpenDrawer}
                onClose={handleClosePopup}
              />
            )}
          </JudgeMapClient>
        </div>

        {/* Detail drawer sidebar */}
        {drawerOpen && selectedRecord && (
          <div className="w-96 shrink-0 overflow-y-auto border-l border-gray-200 bg-white">
            <JudgeMapDrawerBridge
              record={selectedRecord}
              onClose={handleCloseDrawer}
            />
          </div>
        )}
      </div>
    </div>
  );
}
