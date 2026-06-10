"use client";

import { useEffect, useState } from "react";
import { Inbox, RefreshCw } from "lucide-react";
import type { ReviewActionType, SentinelVerdict } from "@/types/generated";
import { listQuarantine, resolveQuarantine } from "@/lib/api";
import { Button, Card, CardContent, Spinner } from "@/components/ui/primitives";
import { VerdictView } from "@/components/VerdictView";
import { cn } from "@/lib/utils";

export function QuarantineQueue() {
  const [items, setItems] = useState<SentinelVerdict[]>([]);
  const [selected, setSelected] = useState<SentinelVerdict | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const data = await listQuarantine();
      setItems(data);
      setSelected((prev) => data.find((d) => d.id === prev?.id) ?? data[0] ?? null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function act(action: ReviewActionType) {
    if (!selected) return;
    setBusy(true);
    try {
      await resolveQuarantine(selected.id, {
        action,
        staff_id: "director",
        staff_note: action === "release" ? "Reviewed and approved" : "Reviewed",
      });
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4 md:grid-cols-[320px_1fr]">
      {/* Queue list */}
      <Card className="h-fit">
        <div className="flex items-center justify-between border-b p-3">
          <span className="flex items-center gap-2 text-sm font-semibold">
            <Inbox className="h-4 w-4" /> Review queue ({items.length})
          </span>
          <button onClick={refresh} className="text-muted-foreground hover:text-foreground">
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
          </button>
        </div>
        <div className="max-h-[70vh] divide-y overflow-auto">
          {items.length === 0 && !loading && (
            <p className="p-4 text-sm text-muted-foreground">
              Nothing waiting. When Sentinel holds an answer, it lands here.
            </p>
          )}
          {items.map((v) => (
            <button
              key={v.id}
              onClick={() => setSelected(v)}
              className={cn(
                "block w-full px-4 py-3 text-left hover:bg-muted",
                selected?.id === v.id && "bg-muted",
              )}
            >
              <div className="text-sm font-medium">{v.topic}</div>
              <div className="line-clamp-2 text-xs text-muted-foreground">{v.question}</div>
            </button>
          ))}
        </div>
      </Card>

      {/* Detail */}
      <div>
        {selected ? (
          <div className="space-y-4">
            <Card>
              <CardContent className="flex flex-wrap items-center gap-2 p-3">
                <span className="text-sm text-muted-foreground">Director action:</span>
                <Button variant="default" disabled={busy} onClick={() => act("release")}>
                  {busy ? <Spinner /> : null} Approve &amp; release
                </Button>
                <Button variant="outline" disabled={busy} onClick={() => act("correct")}>
                  Mark corrected
                </Button>
                <Button variant="ghost" disabled={busy} onClick={() => act("dismiss")}>
                  Dismiss
                </Button>
              </CardContent>
            </Card>
            <VerdictView verdict={selected} />
          </div>
        ) : (
          <Card>
            <CardContent className="p-8 text-center text-sm text-muted-foreground">
              Select an item to see the claim and the contradicting source side by side.
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
