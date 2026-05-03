"use client";

import Link from "next/link";
import { notFound } from "next/navigation";
import { MOCK_INCIDENTS, MOCK_CASES } from "@/lib/mock-data";
import { PageHeader } from "@/components/layout/PageHeader";
import { SectionCard } from "@/components/shared/SectionCard";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Button } from "@/components/ui/button";
import { ArrowLeft, MapPin, Gavel } from "lucide-react";

export default function DefendantPage({ params }: { params: { id: string } }) {
  const linkedIncidents = MOCK_INCIDENTS.filter((i) =>
    i.linkedDefendants.includes(params.id)
  );
  const linkedCases = MOCK_CASES.filter((c) =>
    c.linkedDefendants.includes(params.id)
  );

  if (linkedIncidents.length === 0 && linkedCases.length === 0) notFound();

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/defendants">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Defendants
          </Link>
        </Button>
      </div>

      <PageHeader
        title={params.id}
        subtitle="Defendant — privacy-redacted identifier"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SectionCard title={`Linked Incidents (${linkedIncidents.length})`}>
          {linkedIncidents.length === 0 ? (
            <p className="text-sm text-muted-foreground">No linked incidents.</p>
          ) : (
            <div className="space-y-3">
              {linkedIncidents.map((incident) => (
                <div key={incident.id} className="space-y-1">
                  <div className="flex items-center gap-2">
                    <MapPin className="h-3 w-3 text-muted-foreground" />
                    <span className="text-sm font-medium line-clamp-1">{incident.title}</span>
                  </div>
                  <div className="flex items-center gap-2 pl-5">
                    <StatusBadge status={incident.status} />
                    <span className="text-xs text-muted-foreground">{incident.location.city}, {incident.location.province}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard title={`Linked Cases (${linkedCases.length})`}>
          {linkedCases.length === 0 ? (
            <p className="text-sm text-muted-foreground">No linked cases.</p>
          ) : (
            <div className="space-y-3">
              {linkedCases.map((c) => (
                <div key={c.id} className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Gavel className="h-3 w-3 text-muted-foreground" />
                    <Link href={`/cases/${c.id}`} className="text-sm font-medium hover:underline text-primary line-clamp-1">
                      {c.title}
                    </Link>
                  </div>
                  <div className="flex items-center gap-2 pl-5">
                    <StatusBadge status={c.status} />
                    <span className="text-xs text-muted-foreground">{c.caseNumber}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </div>
    </div>
  );
}
