"use client";

import { useState } from "react";
import { MOCK_ADMIN_REVIEW_ITEMS } from "@/lib/mock-data";
import { type AdminReviewItem } from "@/lib/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { SectionCard } from "@/components/shared/SectionCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CheckCircle, XCircle, Clock } from "lucide-react";

function ReviewStatusBadge({ status }: { status: AdminReviewItem["status"] }) {
  if (status === "approved") return <Badge className="bg-green-100 text-green-700 border-green-200">Approved</Badge>;
  if (status === "rejected") return <Badge className="bg-red-100 text-red-700 border-red-200">Rejected</Badge>;
  if (status === "needs_info") return <Badge variant="outline">Needs Info</Badge>;
  return <Badge variant="secondary">Pending</Badge>;
}

function PriorityBadge({ priority }: { priority: AdminReviewItem["priority"] }) {
  if (priority === "high") return <Badge variant="destructive">High</Badge>;
  if (priority === "medium") return <Badge variant="outline">Medium</Badge>;
  return <Badge variant="secondary">Low</Badge>;
}

export default function AdminReviewPage() {
  const [items, setItems] = useState<AdminReviewItem[]>(MOCK_ADMIN_REVIEW_ITEMS);

  function decide(id: string, decision: "approved" | "rejected") {
    setItems((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, status: decision } : item
      )
    );
  }

  const pending = items.filter((i) => i.status === "pending" || i.status === "needs_info");
  const resolved = items.filter((i) => i.status === "approved" || i.status === "rejected");

  return (
    <div className="space-y-6">
      <PageHeader
        title="Review Queue"
        subtitle={`${pending.length} items pending review`}
      />

      {pending.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Pending</h2>
          {pending.map((item) => (
            <SectionCard key={item.id} title={item.title}>
              <div className="space-y-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <div className="flex items-center gap-1 text-sm text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    <span>{item.type} &middot; submitted {item.submittedAt}</span>
                  </div>
                  <PriorityBadge priority={item.priority} />
                </div>
                {item.notes && <p className="text-sm text-muted-foreground">{item.notes}</p>}
                <div className="flex items-center gap-2 pt-1">
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-green-600 border-green-200 hover:bg-green-50"
                    onClick={() => decide(item.id, "approved")}
                  >
                    <CheckCircle className="h-3 w-3 mr-1" />
                    Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-red-600 border-red-200 hover:bg-red-50"
                    onClick={() => decide(item.id, "rejected")}
                  >
                    <XCircle className="h-3 w-3 mr-1" />
                    Reject
                  </Button>
                </div>
              </div>
            </SectionCard>
          ))}
        </div>
      )}

      {resolved.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Resolved</h2>
          {resolved.map((item) => (
            <SectionCard key={item.id} title={item.title}>
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">{item.type} &middot; {item.submittedAt}</p>
                <ReviewStatusBadge status={item.status} />
              </div>
            </SectionCard>
          ))}
        </div>
      )}

      {items.length === 0 && (
        <p className="text-sm text-muted-foreground">No review items found.</p>
      )}
    </div>
  );
}
