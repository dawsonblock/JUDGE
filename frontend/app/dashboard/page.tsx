"use client";

import Link from "next/link";
import { Map, Scale, FileText, Users, TrendingUp, AlertCircle } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { MetricCard, SectionCard } from "@/components/shared/SectionCard";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Button } from "@/components/ui/button";
import { MOCK_INCIDENTS, MOCK_JUDGES, MOCK_CASES } from "@/lib/mock-data";

function computeStats() {
  const statusCounts: Record<string, number> = {};
  for (const inc of MOCK_INCIDENTS) {
    statusCounts[inc.status] = (statusCounts[inc.status] ?? 0) + 1;
  }
  const avgConf =
    MOCK_INCIDENTS.filter((i) => i.confidence === "medium").length /
    (MOCK_INCIDENTS.length || 1);
  return { statusCounts, avgConf };
}

export default function DashboardPage() {
  const { statusCounts, avgConf } = computeStats();
  const recent = MOCK_INCIDENTS.slice(0, 5);

  return (
    <div className="space-y-8">
      <PageHeader
        title="JUDGE Atlas Dashboard"
        subtitle="Judicial accountability — tracking reported incidents across Canada"
        action={
          <Button asChild>
            <Link href="/map">Open Crime Map</Link>
          </Button>
        }
      />

      {/* Metric row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <MetricCard
          label="Total Incidents"
          value={MOCK_INCIDENTS.length}
          icon={<AlertCircle className="h-5 w-5" />}
        />
        <MetricCard
          label="Active Cases"
          value={MOCK_CASES.filter((c) => c.status === "before_court").length}
          icon={<FileText className="h-5 w-5" />}
        />
        <MetricCard
          label="Judge Profiles"
          value={MOCK_JUDGES.length}
          icon={<Scale className="h-5 w-5" />}
        />
        <MetricCard
          label="Avg. Confidence"
          value={`${Math.round(avgConf * 100)}%`}
          icon={<TrendingUp className="h-5 w-5" />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent incidents */}
        <SectionCard
          title="Recent Incidents"
          action={
            <Button variant="ghost" size="sm" asChild>
              <Link href="/map">View all on map →</Link>
            </Button>
          }
        >
          <div className="divide-y divide-slate-100">
            {recent.map((inc) => (
              <div key={inc.id} className="py-3 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-900 truncate">{inc.title}</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {inc.location.city}, {inc.location.province}
                  </p>
                </div>
                <StatusBadge status={inc.status} />
              </div>
            ))}
          </div>
        </SectionCard>

        {/* Status breakdown */}
        <SectionCard title="Incidents by Status">
          <div className="space-y-2">
            {Object.entries(statusCounts).map(([status, count]) => (
              <div key={status} className="flex items-center justify-between text-sm py-1.5">
                <StatusBadge status={status as any} />
                <span className="font-medium text-slate-900">{count}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { href: "/map", label: "Crime Map", icon: Map, desc: "Interactive map" },
          { href: "/judges", label: "Judges", icon: Scale, desc: "Judicial profiles" },
          { href: "/cases", label: "Cases", icon: FileText, desc: "Court cases" },
          { href: "/sources", label: "Sources", icon: Users, desc: "Evidence sources" },
        ].map(({ href, label, icon: Icon, desc }) => (
          <Link
            key={href}
            href={href}
            className="flex flex-col items-center gap-2 p-4 rounded-lg border border-slate-200 bg-white hover:shadow-sm hover:border-slate-300 transition-all text-center"
          >
            <div className="h-10 w-10 rounded-full bg-slate-100 flex items-center justify-center">
              <Icon className="h-5 w-5 text-slate-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-900">{label}</p>
              <p className="text-xs text-slate-400">{desc}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
