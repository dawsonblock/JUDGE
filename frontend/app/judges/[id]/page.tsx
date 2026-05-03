"use client";

import Link from "next/link";
import { notFound } from "next/navigation";
import { JUDGE_MAP, MOCK_CASES } from "@/lib/mock-data";
import { PageHeader } from "@/components/layout/PageHeader";
import { SectionCard } from "@/components/shared/SectionCard";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, Scale, Calendar, MapPin } from "lucide-react";

export default function JudgePage({ params }: { params: { id: string } }) {
  const judge = JUDGE_MAP[params.id];
  if (!judge) notFound();

  const linkedCases = MOCK_CASES.filter((c) => c.linkedJudges.includes(judge.id));

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/judges">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Judges
          </Link>
        </Button>
      </div>

      <PageHeader
        title={judge.name}
        subtitle={judge.court}
        action={
          <Badge variant={judge.status === "active" ? "default" : "secondary"} className="capitalize">
            {judge.status}
          </Badge>
        }
      />

      <Tabs defaultValue="profile">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="cases">Cases ({linkedCases.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="mt-4 space-y-4">
          <SectionCard title="Court Details">
            <dl className="space-y-3 text-sm">
              <div className="flex gap-2">
                <Scale className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
                <div>
                  <dt className="text-muted-foreground">Court</dt>
                  <dd className="font-medium">{judge.court}</dd>
                </div>
              </div>
              <div className="flex gap-2">
                <MapPin className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
                <div>
                  <dt className="text-muted-foreground">Jurisdiction</dt>
                  <dd className="font-medium">{judge.jurisdiction}</dd>
                </div>
              </div>
              {judge.appointedAt && (
                <div className="flex gap-2">
                  <Calendar className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
                  <div>
                    <dt className="text-muted-foreground">Appointed</dt>
                    <dd className="font-medium">{judge.appointedAt}</dd>
                  </div>
                </div>
              )}
            </dl>
          </SectionCard>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <SectionCard title="Alleged Misconduct">
              <p className="text-2xl font-bold">{judge.allegedMisconductCount}</p>
              <p className="text-sm text-muted-foreground">reported incidents</p>
            </SectionCard>
            <SectionCard title="Sources">
              <p className="text-2xl font-bold">{judge.sourceCount}</p>
              <p className="text-sm text-muted-foreground">linked sources</p>
            </SectionCard>
          </div>

          {judge.notes && (
            <SectionCard title="Notes">
              <p className="text-sm text-muted-foreground">{judge.notes}</p>
            </SectionCard>
          )}
        </TabsContent>

        <TabsContent value="cases" className="mt-4 space-y-3">
          {linkedCases.length === 0 ? (
            <p className="text-sm text-muted-foreground">No linked cases in mock data.</p>
          ) : (
            linkedCases.map((c) => (
              <SectionCard key={c.id} title={c.title}>
                <div className="flex items-center justify-between">
                  <div className="space-y-1 text-sm">
                    <p className="text-muted-foreground">{c.caseNumber} &middot; {c.court}</p>
                    {c.filedAt && (
                      <p className="text-muted-foreground">Filed {c.filedAt}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge status={c.status} />
                    <Button variant="outline" size="sm" asChild>
                      <Link href={`/cases/${c.id}`}>View</Link>
                    </Button>
                  </div>
                </div>
              </SectionCard>
            ))
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
