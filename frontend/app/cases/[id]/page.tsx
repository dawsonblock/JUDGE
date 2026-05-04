import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchCase, fetchCaseTimeline } from "@/lib/api";
import { PageHeader } from "@/components/layout/PageHeader";
import { SectionCard } from "@/components/shared/SectionCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Scale, Calendar, FileText } from "lucide-react";

export default async function CasePage({ params }: { params: { id: string } }) {
  const [courtCase, events] = await Promise.all([
    fetchCase(params.id).catch(() => null),
    fetchCaseTimeline(params.id).catch(() => []),
  ]);
  if (!courtCase) notFound();

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/cases">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Cases
          </Link>
        </Button>
      </div>

      <PageHeader
        title={courtCase.caption}
        subtitle={`${courtCase.docket_number} · Court #${courtCase.court_id}`}
        action={
          courtCase.case_type ? (
            <Badge variant="outline">{courtCase.case_type}</Badge>
          ) : undefined
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SectionCard title="Case Information">
          <dl className="space-y-3 text-sm">
            <div className="flex gap-2">
              <FileText className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
              <div>
                <dt className="text-muted-foreground">Docket Number</dt>
                <dd className="font-medium">{courtCase.docket_number}</dd>
              </div>
            </div>
            <div className="flex gap-2">
              <Scale className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
              <div>
                <dt className="text-muted-foreground">Court</dt>
                <dd className="font-medium">Court #{courtCase.court_id}</dd>
              </div>
            </div>
            {courtCase.filed_date && (
              <div className="flex gap-2">
                <Calendar className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
                <div>
                  <dt className="text-muted-foreground">Filed</dt>
                  <dd className="font-medium">{courtCase.filed_date}</dd>
                </div>
              </div>
            )}
            {courtCase.terminated_date && (
              <div className="flex gap-2">
                <Calendar className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
                <div>
                  <dt className="text-muted-foreground">Terminated</dt>
                  <dd className="font-medium">{courtCase.terminated_date}</dd>
                </div>
              </div>
            )}
          </dl>
        </SectionCard>

        <SectionCard title="Case Type">
          <p className="text-sm text-muted-foreground">
            {courtCase.case_type ?? "Not specified"}
          </p>
        </SectionCard>
      </div>

      <SectionCard title={`Event Timeline (${events.length})`}>
        {events.length === 0 ? (
          <p className="text-sm text-muted-foreground">No public events on record.</p>
        ) : (
          <ul className="space-y-3">
            {events.map((ev) => (
              <li key={ev.id} className="text-sm border-l-2 border-slate-200 pl-3">
                <p className="font-medium text-slate-800">{ev.event_type}</p>
                {ev.decision_date && (
                  <p className="text-xs text-slate-500">{ev.decision_date}</p>
                )}
                {ev.notes && (
                  <p className="text-xs text-slate-600 mt-0.5 line-clamp-2">{ev.notes}</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}

