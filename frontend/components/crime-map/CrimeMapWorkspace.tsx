"use client";

import { useState, useMemo } from "react";
import type { CrimeIncident, MapFilterState } from "@/lib/types";
import { MOCK_INCIDENTS } from "@/lib/mock-data";
import { MapFilters } from "@/components/map/MapFilters";
import { MapCanvasClient } from "@/components/map/MapCanvasClient";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { PageHeader } from "@/components/layout/PageHeader";
import { SectionCard } from "@/components/shared/SectionCard";

const DEFAULT_FILTERS: MapFilterState = {
  searchQuery: "",
  category: "all",
  status: "all",
  province: "all",
  dateFrom: null,
  dateTo: null,
  courtLinkedOnly: false,
  verifiedOnly: false,
  hideSensitive: false,
};

function applyFilters(incidents: CrimeIncident[], filters: MapFilterState): CrimeIncident[] {
  return incidents.filter((inc) => {
    if (filters.searchQuery) {
      const q = filters.searchQuery.toLowerCase();
      if (
        !inc.title.toLowerCase().includes(q) &&
        !inc.location.city.toLowerCase().includes(q) &&
        !inc.location.province.toLowerCase().includes(q)
      ) return false;
    }
    if (filters.category !== "all" && inc.category !== filters.category) return false;
    if (filters.status !== "all" && inc.status !== filters.status) return false;
    if (filters.province !== "all" && inc.location.province !== filters.province) return false;
    if (filters.courtLinkedOnly && !inc.caseId) return false;
    if (filters.verifiedOnly && inc.confidenceScore < 0.7) return false;
    return true;
  });
}

export function CrimeMapWorkspace() {
  const [filters, setFilters] = useState<MapFilterState>(DEFAULT_FILTERS);
  const [selectedIncident, setSelectedIncident] = useState<CrimeIncident | null>(null);

  const filtered = useMemo(() => applyFilters(MOCK_INCIDENTS, filters), [filters]);

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <div className="shrink-0 px-4 pt-4">
        <PageHeader title="Crime Map" subtitle="Interactive map of tracked incidents across Canada" />
      </div>
      <div className="flex flex-1 min-h-0 gap-0">
        {/* Filter sidebar */}
        <aside className="w-72 shrink-0 overflow-y-auto border-r border-slate-200 bg-white">
          <MapFilters filters={filters} onChange={setFilters} resultCount={filtered.length} />
        </aside>

        {/* Map area */}
        <div className="flex-1 relative">
          <MapCanvasClient
            incidents={filtered}
            selectedId={selectedIncident?.id}
            onSelect={setSelectedIncident}
          />
        </div>

        {/* Detail panel */}
        <aside className="w-80 shrink-0 overflow-y-auto border-l border-slate-200 bg-white">
          {selectedIncident ? (
            <div className="p-4 space-y-4">
              <div className="flex items-start justify-between gap-2">
                <h2 className="font-semibold text-slate-900 text-sm leading-snug">
                  {selectedIncident.title}
                </h2>
                <button
                  onClick={() => setSelectedIncident(null)}
                  className="text-slate-400 hover:text-slate-600 text-xs shrink-0"
                >
                  ✕
                </button>
              </div>
              <StatusBadge status={selectedIncident.status} />
              <SectionCard title="Location">
                <p className="text-sm text-slate-600">
                  {selectedIncident.location.city}, {selectedIncident.location.province}
                </p>
              </SectionCard>
              <SectionCard title="Description">
                <p className="text-sm text-slate-600">{selectedIncident.description}</p>
              </SectionCard>
              <SectionCard title="Details">
                <dl className="text-sm space-y-1">
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Category</dt>
                    <dd className="text-slate-900 capitalize">{selectedIncident.category.replace(/_/g, " ")}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Confidence</dt>
                    <dd className="text-slate-900">{Math.round(selectedIncident.confidenceScore * 100)}%</dd>
                  </div>
                  {selectedIncident.incidentDate && (
                    <div className="flex justify-between">
                      <dt className="text-slate-500">Date</dt>
                      <dd className="text-slate-900">{new Date(selectedIncident.incidentDate).toLocaleDateString()}</dd>
                    </div>
                  )}
                </dl>
              </SectionCard>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center p-8 text-center">
              <p className="text-slate-400 text-sm">Select an incident on the map to view details</p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
