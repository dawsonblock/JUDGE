"use client";

import Link from "next/link";
import { notFound } from "next/navigation";
import { CASE_MAP, JUDGE_MAP } from "@/lib/mock-data";
import { PageHeader } from "@/components/layout/PageHeader";
import { SectionCard } from "@/components/shared/SectionCard";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { EvidenceTypeBadge } from "@/components/shared/EvidenceTypeBadge";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, Scale, Calendar, User, FileText } from "lucide-react";

export default function CasePage({ params }: { params: { id: string } }) {
  const courtCase = CASE_MAP[params.id];
  if (!courtCase) notFound();

  const judges = courtCase.linkedJudges.map((jid) => JUDGE_MAP[jid]).filter(Boolean);
  const sources = courtCase.evidenceSources;

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
        title={courtCase.title}
        subtitle={`${courtCase.caseNumber} · ${courtCase.court}`}
        action={<StatusBadge status={courtCase.status} />}
      />

      <Tabs defaultValue="details">
        <TabsList>
          <TabsTrigger value="details">Details</TabsTrigger>
          <TabsTrigger value="evidence">Evidence ({sources.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="details" className="mt-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SectionCard title="Case Information">
              <dl className="space-y-3 text-sm">
                <div className="flex gap-2">
                  <FileText className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
                  <div>
                    <dt className="text-muted-foreground">Case Number</dt>
                    <dd className="font-medium">{courtCase.caseNumber}</dd>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Scale className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
                  <div>
                    <dt className="text-muted-foreground">Court</dt>
                    <dd className="font-medium">{courtCase.court}</dd>
                  </div>
                </div>
                {courtCase.filedAt && (
                  <div className="flex gap-2">
                    <Calendar className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
                    <div>
                      <dt className="text-muted-foreground">Filing Date</dt>
                      <dd className="font-medium">{courtCase.filedAt}</dd>
                    </div>
                  </div>
                )}
                {judges.length > 0 && (
                  <div className="flex gap-2">
                    <User className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
                    <div>
                      <dt className="text-muted-foreground">Presiding Judge{judges.length > 1 ? "s" : ""}</dt>
                      <dd className="font-medium flex flex-wrap gap-1">
                        {judges.map((j) => j && (
                          <Link key={j.id} href={`/judges/${j.id}`} className="hover:underline text-primary">
                            {j.name}
                          </Link>
                        ))}
                      </dd>
                    </div>
                  </div>
                )}
              </dl>
            </SectionCard>

            <SectionCard title="Charges">
              <div className="space-y-2">
                {courtCase.charges.map((charge, i) => (
                  <div key={i} className="text-sm p-2 rounded bg-muted/50">
                    {charge}
                  </div>
                ))}
              </div>
            </SectionCard>
          </div>

          {courtCase.linkedDefendants.length > 0 && (
            <SectionCard title="Defendants">
              <div className="flex flex-wrap gap-2">
                {courtCase.linkedDefendants.map((id) => (
                  <Badge key={id} variant="outline">
                    <Link href={`/defendants/${id}`} className="hover:underline">{id}</Link>
                  </Badge>
                ))}
              </div>
            </SectionCard>
          )}
        </TabsContent>

        <TabsContent value="evidence" className="mt-4 space-y-3">
          {sources.length === 0 ? (
            <p className="text-sm text-muted-foreground">No evidence sources linked.</p>
          ) : (
            sources.map((src) => (
              <SectionCard key={src.id} title={src.name}>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <EvidenceTypeBadge type={src.type} />
                    <ConfidenceBadge confidence={src.confidence} />
                  </div>
                  {src.summary && (
                    <p className="text-sm text-muted-foreground line-clamp-2">{src.summary}</p>
                  )}
                  {src.url && (
                    <a
                      href={src.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-primary hover:underline"
                    >
                      View source &rarr;
                    </a>
                  )}
                </div>
              </SectionCard>
            ))
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
