"use client";

import Link from "next/link";
import { Calendar, FileText, User } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { CourtCase } from "@/lib/types";
import { StatusBadge } from "@/components/shared/StatusBadge";

interface CaseCardProps {
  courtCase: CourtCase;
}

export function CaseCard({ courtCase }: CaseCardProps) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="font-semibold text-slate-900 text-sm leading-snug">{courtCase.title}</h3>
            <p className="text-xs text-slate-400 mt-0.5 font-mono">{courtCase.caseNumber}</p>
          </div>
          <StatusBadge status={courtCase.status} />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-2 text-xs text-slate-600">
          <div className="flex items-center gap-1.5">
            <FileText className="h-3 w-3 text-slate-400" />
            <span>{courtCase.court}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Calendar className="h-3 w-3 text-slate-400" />
            <span>{new Date(courtCase.filingDate).toLocaleDateString("en-CA")}</span>
          </div>
          {courtCase.judgeId && (
            <div className="flex items-center gap-1.5 col-span-2">
              <User className="h-3 w-3 text-slate-400" />
              <span>Judge: {courtCase.judgeId}</span>
            </div>
          )}
        </div>

        {courtCase.charges.length > 0 && (
          <div>
            <p className="text-xs text-slate-500 mb-1">Charges</p>
            <p className="text-xs text-slate-700 leading-relaxed line-clamp-2">
              {courtCase.charges.join(" · ")}
            </p>
          </div>
        )}

        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400">
            {courtCase.evidenceSources.length} evidence source{courtCase.evidenceSources.length !== 1 ? "s" : ""}
          </span>
          <Link href={`/cases/${courtCase.id}`} className="text-blue-600 hover:underline">
            View case →
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
