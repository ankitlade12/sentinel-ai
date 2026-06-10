"use client";

import { useEffect, useState } from "react";
import { CalendarClock, FileWarning, ShieldCheck, TrendingUp } from "lucide-react";
import type { CorpusDoc, TrustReport } from "@/types/generated";
import { getCorpus, getTrustReport } from "@/lib/api";
import { Badge, Card, CardContent, CardHeader, CardTitle, Spinner } from "@/components/ui/primitives";

function daysAgo(iso: string): number {
  const then = new Date(iso).getTime();
  return Math.floor((Date.now() - then) / 86_400_000);
}

function Stat({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className={`text-3xl font-semibold ${tone}`}>{value}</div>
        <div className="text-xs text-muted-foreground">{label}</div>
      </CardContent>
    </Card>
  );
}

export function TrustReportView() {
  const [report, setReport] = useState<TrustReport | null>(null);
  const [docs, setDocs] = useState<CorpusDoc[]>([]);

  useEffect(() => {
    getTrustReport().then(setReport).catch(() => setReport(null));
    getCorpus().then(setDocs).catch(() => setDocs([]));
  }, []);

  if (!report) {
    return (
      <div className="flex items-center gap-2 p-8 text-sm text-muted-foreground">
        <Spinner /> Generating the weekly Trust Report…
      </div>
    );
  }

  const caught = report.what_was_caught ?? [];
  const gaps = report.corpus_gaps ?? [];

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{report.org_name}</CardTitle>
          <p className="text-xs text-muted-foreground">Week of {report.week_of}</p>
        </CardHeader>
        <CardContent>
          <p className="text-lg font-medium">{report.headline}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Sentinel cleared {report.cleared} automatically, corrected {report.corrected} with
            citations, and held {report.held} for your team&apos;s review.
          </p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-3 gap-3">
        <Stat label="Cleared" value={report.cleared ?? 0} tone="text-allow" />
        <Stat label="Corrected & cited" value={report.corrected ?? 0} tone="text-[hsl(30_90%_40%)]" />
        <Stat label="Held for review" value={report.held ?? 0} tone="text-quarantine" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4" /> What was caught
          </CardTitle>
        </CardHeader>
        <CardContent>
          {caught.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nothing held this period.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {caught.map((b, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-quarantine">•</span>
                  {b}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4" /> Trend
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p>{report.trend}</p>
          <div className="flex flex-wrap gap-2">
            {report.riskiest_topic && <Badge tone="quarantine">Riskiest: {report.riskiest_topic}</Badge>}
            {report.safest_topic && <Badge tone="allow">Safest: {report.safest_topic}</Badge>}
            {gaps.map((g) => (
              <Badge key={g} tone="outline">
                <FileWarning className="h-3 w-3" /> gap: {g}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Corpus freshness — corpus-gap analysis */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CalendarClock className="h-4 w-4" /> Your trusted sources
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="divide-y text-sm">
            {docs.map((d) => {
              const age = daysAgo(d.last_verified);
              return (
                <li key={d.id} className="flex items-center justify-between py-2">
                  <span>{d.title}</span>
                  <span className={age > 90 ? "text-quarantine" : "text-muted-foreground"}>
                    verified {age}d ago
                  </span>
                </li>
              );
            })}
          </ul>
        </CardContent>
      </Card>

      <p className="px-1 text-xs italic text-muted-foreground">{report.disclaimer}</p>
    </div>
  );
}
