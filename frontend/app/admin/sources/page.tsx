import { PageHeader } from "@/components/layout/PageHeader";
import { fetchAdminSourcesList, AdminSourceItem } from "@/lib/api";
import { SourceControlCard } from "@/components/SourceControlCard";


export default async function AdminSourcesPage() {
  const sources = await fetchAdminSourcesList(
    process.env.JTA_ADMIN_TOKEN ?? "",
  ).catch(() => [] as AdminSourceItem[]);

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
          <SourceControlCard key={source.id} source={source} />
        ))}
      </div>

      {sources.length === 0 && (
        <p className="text-sm text-muted-foreground">No sources found.</p>
      )}
    </div>
  );
}

