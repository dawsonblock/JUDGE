"use client";

import { MOCK_EVIDENCE_SOURCES } from "@/lib/mock-data";
import { PageHeader } from "@/components/layout/PageHeader";
import { SectionCard } from "@/components/shared/SectionCard";
import { EvidenceTypeBadge } from "@/components/shared/EvidenceTypeBadge";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import { Badge } from "@/components/ui/badge";
import { ExternalLink } from "lucide-react";

export default function AdminSourcesPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Source Registry"
        subtitle={`${MOCK_EVIDENCE_SOURCES.length} registered sources`}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {MOCK_EVIDENCE_SOURCES.map((source) => (
          <SectionCard key={source.id} title={source.name}>
            <div className="space-y-3">
              <div className="flex items-center gap-2 flex-wrap">
                <EvidenceTypeBadge type={source.type} />
                <ConfidenceBadge confidence={source.confidence} />
                {source.verified && (
                  <Badge className="bg-green-100 text-green-700 border-green-200 text-xs">Verified</Badge>
                )}
              </div>

              {source.summary && (
                <p className="text-xs text-muted-foreground line-clamp-2">{source.summary}</p>
              )}

              <div className="flex items-center justify-between pt-1">
                {source.publishedAt && (
                  <Badge variant="outline" className="text-xs">{source.publishedAt}</Badge>
                )}
                {source.url && (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-xs text-blue-600 hover:underline"
                  >
                    View source
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
            </div>
          </SectionCard>
        ))}
      </div>
    </div>
  );
}
