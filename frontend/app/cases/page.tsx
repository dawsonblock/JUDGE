import { PageHeader } from "@/components/layout/PageHeader";
import { CaseCard } from "@/components/cases/CaseCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { MOCK_CASES } from "@/lib/mock-data";

export default function CasesPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Court Cases"
        subtitle="Active and historical cases in the Canadian judicial system."
      />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {MOCK_CASES.map((c) => (
          <CaseCard key={c.id} courtCase={c} />
        ))}
      </div>
      {MOCK_CASES.length === 0 && (
        <EmptyState title="No Cases" description="No court cases have been tracked yet." />
      )}
    </div>
  );
}
