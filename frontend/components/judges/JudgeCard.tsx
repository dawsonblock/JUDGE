"use client";

import Link from "next/link";
import { MapPin, Scale, Calendar } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { JudgeProfile } from "@/lib/types";

interface JudgeCardProps {
  judge: JudgeProfile;
}

export function JudgeCard({ judge }: JudgeCardProps) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="font-semibold text-slate-900">{judge.name}</h3>
            <p className="text-sm text-slate-500 mt-0.5">{judge.title}</p>
          </div>
          {judge.isActive ? (
            <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200 text-xs shrink-0">
              Active
            </Badge>
          ) : (
            <Badge variant="outline" className="bg-slate-50 text-slate-500 text-xs shrink-0">
              Inactive
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-2 text-xs text-slate-600">
          <div className="flex items-center gap-1.5">
            <Scale className="h-3 w-3 text-slate-400" />
            <span>{judge.court}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <MapPin className="h-3 w-3 text-slate-400" />
            <span>{judge.jurisdiction}</span>
          </div>
          {judge.appointedDate && (
            <div className="flex items-center gap-1.5">
              <Calendar className="h-3 w-3 text-slate-400" />
              <span>Appointed {new Date(judge.appointedDate).getFullYear()}</span>
            </div>
          )}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400">Cases:</span>
            <span className="font-medium text-slate-900">{judge.caseIds.length}</span>
          </div>
        </div>

        {judge.specializations.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {judge.specializations.map((s) => (
              <Badge key={s} variant="secondary" className="text-xs capitalize">
                {s.replace(/_/g, " ")}
              </Badge>
            ))}
          </div>
        )}

        <Link
          href={`/judges/${judge.id}`}
          className="block text-xs text-blue-600 hover:underline mt-1"
        >
          View full profile →
        </Link>
      </CardContent>
    </Card>
  );
}
