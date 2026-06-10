"use client";

import { useState } from "react";
import { FileText, Inbox, ShieldCheck, Sparkles } from "lucide-react";
import { AskDemo } from "@/components/AskDemo";
import { QuarantineQueue } from "@/components/QuarantineQueue";
import { TrustReportView } from "@/components/TrustReportView";
import { cn } from "@/lib/utils";

type Tab = "demo" | "queue" | "report";

const TABS: { id: Tab; label: string; Icon: typeof Sparkles }[] = [
  { id: "demo", label: "Live demo", Icon: Sparkles },
  { id: "queue", label: "Review queue", Icon: Inbox },
  { id: "report", label: "Trust Report", Icon: FileText },
];

export default function Home() {
  const [tab, setTab] = useState<Tab>("demo");

  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      {/* Header */}
      <header className="mb-6 flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <ShieldCheck className="h-5 w-5" />
          </span>
          <div>
            <h1 className="text-lg font-semibold leading-tight">Sentinel</h1>
            <p className="text-xs text-muted-foreground">
              Riverside Community Legal Aid · the safety layer for everyone else
            </p>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <nav className="mb-5 flex gap-1 rounded-lg border bg-card p-1">
        {TABS.map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={cn(
              "flex flex-1 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              tab === id ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted",
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </nav>

      <main>
        {tab === "demo" && <AskDemo />}
        {tab === "queue" && <QuarantineQueue />}
        {tab === "report" && <TrustReportView />}
      </main>

      <footer className="mt-10 border-t pt-4 text-center text-xs text-muted-foreground">
        Enterprises buy AI safety. Communities deserve it. · Every decision is an Arize&nbsp;Phoenix trace.
      </footer>
    </div>
  );
}
