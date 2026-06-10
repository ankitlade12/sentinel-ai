"use client";

import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  FileText,
  HelpCircle,
  Scale,
} from "lucide-react";
import type {
  EvalResult,
  GroundingResult,
  GroundingStatus,
  SentinelVerdict,
} from "@/types/generated";
import { Badge, Card, CardContent, CardHeader, CardTitle } from "@/components/ui/primitives";
import { DecisionBadge } from "@/components/DecisionBadge";
import { cn } from "@/lib/utils";

const STATUS: Record<GroundingStatus, { tone: "allow" | "quarantine" | "repair"; label: string; Icon: typeof CheckCircle2 }> = {
  supported: { tone: "allow", label: "Supported", Icon: CheckCircle2 },
  contradicted: { tone: "quarantine", label: "Contradicted", Icon: AlertTriangle },
  not_found: { tone: "repair", label: "Not in corpus", Icon: HelpCircle },
};

function TriageChips({ verdict }: { verdict: SentinelVerdict }) {
  const t = verdict.plan.triage;
  return (
    <div className="flex flex-wrap gap-2">
      <Badge tone="outline">Stakes: {t.stakes}</Badge>
      <Badge tone="outline">{t.specificity.replace("_", " ")}</Badge>
      <Badge tone="outline">{t.coverage.replace("_", " ")}</Badge>
      <Badge tone={verdict.plan.path === "full" ? "primary" : "default"}>{verdict.plan.path} path</Badge>
    </div>
  );
}

function GroundingRow({ g }: { g: GroundingResult }) {
  const s = STATUS[g.status];
  const top = g.passages?.[0];
  return (
    <div className={cn("grid gap-px overflow-hidden rounded-md border md:grid-cols-2", g.status !== "supported" && "border-quarantine/40")}>
      <div className="bg-card p-3">
        <div className="mb-1 flex items-center gap-2">
          <Badge tone={s.tone}>
            <s.Icon className="h-3 w-3" />
            {s.label}
          </Badge>
          <span className="text-xs text-muted-foreground">the assistant's claim</span>
        </div>
        <p className="text-sm">{g.claim_text}</p>
      </div>
      <div className="bg-muted/40 p-3">
        <div className="mb-1 flex items-center gap-2 text-xs text-muted-foreground">
          <FileText className="h-3 w-3" />
          {top ? `${top.doc_title} · verified ${top.last_verified}` : "your clinic's trusted sources"}
        </div>
        <p className="text-sm text-foreground/90">{top?.text ?? g.explanation}</p>
        {g.corrected_text && (
          <p className="mt-2 text-sm font-medium text-allow">→ {g.corrected_text}</p>
        )}
      </div>
    </div>
  );
}

function EvalBadge({ e }: { e: EvalResult }) {
  return (
    <Badge tone={e.passed ? "allow" : "quarantine"}>
      {e.kind.replace("_", " ")}: {e.label} ({e.score.toFixed(2)})
    </Badge>
  );
}

export function VerdictView({ verdict }: { verdict: SentinelVerdict }) {
  const checked = verdict.grounding ?? [];
  return (
    <div className="space-y-4">
      {/* Decision header */}
      <Card className="animate-in">
        <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
          <div className="flex items-center gap-3">
            <DecisionBadge decision={verdict.decision} />
            <span className="text-sm font-medium">{verdict.topic}</span>
          </div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span>{verdict.latency_ms} ms</span>
            {verdict.trace_url ? (
              <a className="inline-flex items-center gap-1 text-primary hover:underline" href={verdict.trace_url} target="_blank" rel="noreferrer">
                <ExternalLink className="h-3 w-3" /> Phoenix trace
              </a>
            ) : (
              <span className="inline-flex items-center gap-1">
                <ExternalLink className="h-3 w-3" /> trace logged
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* What the user actually sees */}
      <Card className="animate-in border-primary/20">
        <CardHeader>
          <CardTitle className="text-muted-foreground">What the user receives</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="whitespace-pre-wrap text-sm leading-relaxed">{verdict.delivered_answer}</p>
        </CardContent>
      </Card>

      {/* The written plan */}
      <Card className="animate-in">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Scale className="h-4 w-4" /> The agent's plan
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <TriageChips verdict={verdict} />
          <p className="rounded-md bg-muted/60 p-3 text-sm italic">{verdict.plan.summary}</p>
        </CardContent>
      </Card>

      {/* Side-by-side grounding — the money screen */}
      {checked.length > 0 && (
        <Card className="animate-in">
          <CardHeader>
            <CardTitle>Claim-by-claim grounding against the trusted corpus</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {checked.map((g) => (
              <GroundingRow key={g.claim_id} g={g} />
            ))}
          </CardContent>
        </Card>
      )}

      {/* Evals + rationale */}
      <Card className="animate-in">
        <CardHeader>
          <CardTitle>Evaluations &amp; reasoning</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {(verdict.evals ?? []).length > 0 && (
            <div className="flex flex-wrap gap-2">
              {(verdict.evals ?? []).map((e) => (
                <EvalBadge key={e.kind} e={e} />
              ))}
            </div>
          )}
          <p className="text-sm text-muted-foreground">{verdict.rationale}</p>
          {verdict.requires_human_review && (
            <p className="text-xs font-medium text-quarantine">
              ⚑ High-stakes — human review is required before this can be released.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
