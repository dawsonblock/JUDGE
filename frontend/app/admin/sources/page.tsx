import { PageHeader } from "@/components/layout/PageHeader";
import { SectionCard } from "@/components/shared/SectionCard";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, CheckCircle, XCircle, Clock, ShieldCheck } from "lucide-react";
import { fetchAdminSourcesList, AdminSourceItem } from "@/lib/api";

function AuthorityBadge({ authority }: { authority: string }) {
  const colour: Record<string, string> = {
    official_open_data: "bg-blue-100 text-blue-800",
    official_statistics: "bg-indigo-100 text-indigo-800",
    official_government: "bg-violet-100 text-violet-800",
    official_legislation: "bg-purple-100 text-purple-800",
    official_court_record: "bg-cyan-100 text-cyan-800",
    news_context: "bg-amber-100 text-amber-800",
    unknown: "bg-gray-100 text-gray-600",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${colour[authority] ?? colour.unknown}`}
    >
      <ShieldCheck className="h-3 w-3" />
      {authority.replace(/_/g, " ")}
    </span>
  );
}

function SourceCard({ source }: { source: AdminSourceItem }) {
  const creates: string[] = source.creates ? JSON.parse(source.creates) : [];
  const location = [source.city, source.province_state, source.country]
    .filter(Boolean)
    .join(", ");

  return (
    <SectionCard title={source.source_name}>
      <div className="space-y-3 text-sm">
        {/* Status row */}
        <div className="flex items-center gap-2 flex-wrap">
          {source.is_active ? (
            <span className="flex items-center gap-1 text-green-700 font-medium">
              <CheckCircle className="h-3.5 w-3.5" /> Active
            </span>
          ) : (
            <span className="flex items-center gap-1 text-gray-400">
              <XCircle className="h-3.5 w-3.5" /> Disabled
            </span>
          )}
          <Badge variant="outline" className="text-xs">{source.source_type}</Badge>
          {source.category && (
            <Badge variant="secondary" className="text-xs">{source.category}</Badge>
          )}
        </div>

        {/* Authority */}
        <AuthorityBadge authority={source.public_record_authority} />

        {/* Location / jurisdiction */}
        {location && (
          <p className="text-xs text-muted-foreground">{location}</p>
        )}
        {source.jurisdiction && (
          <p className="text-xs text-muted-foreground">Jurisdiction: {source.jurisdiction}</p>
        )}

        {/* Creates */}
        {creates.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {creates.map((t) => (
              <Badge key={t} variant="outline" className="text-xs">{t}</Badge>
            ))}
          </div>
        )}

        {/* Parser / priority */}
        <div className="flex gap-3 text-xs text-muted-foreground">
          {source.parser && <span>Parser: <code className="font-mono">{source.parser}</code></span>}
          <span>Priority: {source.priority}</span>
        </div>

        {/* Review gate notice */}
        {source.requires_manual_review && (
          <p className="text-xs text-amber-700 font-medium">Requires manual review before publish</p>
        )}

        {/* Last fetched / health */}
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          {source.last_ingested_at
            ? `Last ingested: ${new Date(source.last_ingested_at).toLocaleDateString()}`
            : "Never ingested"}
          {" · "}
          Health: {Math.round(source.health_score * 100)}%
        </div>

        {/* Links */}
        <div className="flex gap-3 pt-1 flex-wrap">
          {source.base_url && (
            <a
              href={source.base_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-blue-600 hover:underline"
            >
              Source <ExternalLink className="h-3 w-3" />
            </a>
          )}
          {source.terms_url && (
            <a
              href={source.terms_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-blue-600 hover:underline"
            >
              Terms <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>

        {/* Admin notes */}
        {source.admin_notes && (
          <p className="text-xs text-muted-foreground italic">{source.admin_notes}</p>
        )}
      </div>
    </SectionCard>
  );
}

export default async function AdminSourcesPage() {
  const token = process.env.JTA_ADMIN_TOKEN ?? "";
  const sources = await fetchAdminSourcesList(token).catch(() => [] as AdminSourceItem[]);

  const activeSources = sources.filter((s) => s.is_active);
  const byAuthority = sources.reduce<Record<string, number>>((acc, s) => {
    acc[s.public_record_authority] = (acc[s.public_record_authority] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <PageHeader
        title="Source Registry"
        subtitle={`${sources.length} registered · ${activeSources.length} active`}
      />

      {/* Summary bar */}
      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
        {Object.entries(byAuthority).sort(([, a], [, b]) => b - a).map(([auth, count]) => (
          <span key={auth} className="rounded border px-2 py-0.5">
            {auth.replace(/_/g, " ")}: {count}
          </span>
        ))}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sources.map((source) => (
          <SourceCard key={source.id} source={source} />
        ))}
      </div>

      {sources.length === 0 && (
        <p className="text-sm text-muted-foreground">No sources found.</p>
      )}
    </div>
  );
}

