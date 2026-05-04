import { PageHeader } from "@/components/layout/PageHeader";
import { SectionCard } from "@/components/shared/SectionCard";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, CheckCircle } from "lucide-react";
import { fetchAdminSourcesList } from "@/lib/api";

export default async function AdminSourcesPage() {
  const token = process.env.JTA_ADMIN_REVIEW_TOKEN ?? "";
  const sources = await fetchAdminSourcesList(token).catch(() => []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Source Registry"
        subtitle={`${sources.length} registered sources`}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sources.map((source) => (
          <SectionCard key={source.id} title={source.title}>
            <div className="space-y-3">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant="outline" className="text-xs">{source.source_type}</Badge>
                <Badge variant="secondary" className="text-xs">{source.source_quality}</Badge>
                {source.verified_flag && (
                  <span className="flex items-center gap-1 text-xs text-green-600">
                    <CheckCircle className="h-3 w-3" /> Verified
                  </span>
                )}
              </div>

              <div className="flex items-center justify-between pt-1">
                <Badge variant="outline" className="text-xs">{source.review_status}</Badge>
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

      {sources.length === 0 && (
        <p className="text-sm text-muted-foreground">No sources found.</p>
      )}
    </div>
  );
}
