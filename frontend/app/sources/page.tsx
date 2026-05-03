import { PageHeader } from "@/components/layout/PageHeader";
import { SectionCard } from "@/components/shared/SectionCard";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import { EvidenceTypeBadge } from "@/components/shared/EvidenceTypeBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import { MOCK_EVIDENCE_SOURCES } from "@/lib/mock-data";
import { ExternalLink } from "lucide-react";

export default function SourcesPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Evidence Sources"
        subtitle="Tracked publications, court records, and documents supporting incident data."
      />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {MOCK_EVIDENCE_SOURCES.map((source) => (
          <SectionCard
            key={source.id}
            title={source.name}
            action={
              source.url ? (
                <a href={source.url} target="_blank" rel="noopener noreferrer"
                  className="text-slate-400 hover:text-blue-500 shrink-0">
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              ) : undefined
            }
          >
            <div className="space-y-2">
              <div className="flex flex-wrap gap-1.5">
                <EvidenceTypeBadge type={source.type} />
                <ConfidenceBadge confidence={source.confidence} />
              </div>
              {source.publishedAt && (
                <p className="text-xs text-slate-400">
                  {new Date(source.publishedAt).toLocaleDateString("en-CA")}
                </p>
              )}
              {source.summary && (
                <p className="text-xs text-slate-600 italic line-clamp-2">&ldquo;{source.summary}&rdquo;</p>
              )}
            </div>
          </SectionCard>
        ))}
      </div>
      {MOCK_EVIDENCE_SOURCES.length === 0 && (
        <EmptyState title="No Sources" description="No evidence sources have been added yet." />
      )}
    </div>
  );
}
