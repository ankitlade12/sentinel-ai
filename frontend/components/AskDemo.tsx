"use client";

import { useRef, useState } from "react";
import { Bot, MessageSquare, Send } from "lucide-react";
import type { SentinelVerdict } from "@/types/generated";
import { askStream, type StreamEvent } from "@/lib/api";
import { Button, Card, CardContent, CardHeader, CardTitle, Spinner } from "@/components/ui/primitives";
import { VerdictView } from "@/components/VerdictView";

const SAMPLES = [
  "When do I have to renew my green card?",
  "What are your office hours?",
  "What's the income limit for SNAP for a family of three?",
  "Does the clinic charge a fee for a consultation?",
  "How long until I can apply for citizenship?",
];

export function AskDemo() {
  const [question, setQuestion] = useState("");
  const [running, setRunning] = useState(false);
  const [casaDraft, setCasaDraft] = useState<string | null>(null);
  const [activities, setActivities] = useState<string[]>([]);
  const [verdict, setVerdict] = useState<SentinelVerdict | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  function pushActivity(line: string) {
    setActivities((prev) => [...prev, line]);
  }

  function handleEvent(e: StreamEvent) {
    const d = e.data as Record<string, any>;
    switch (e.event) {
      case "casa_drafted":
        setCasaDraft(d.answer);
        break;
      case "agent_activity":
        pushActivity(d.summary);
        break;
      case "plan_written":
        pushActivity(`Plan → ${d.plan.summary}`);
        break;
      case "claim_extracted":
        pushActivity(`Claim: “${d.claim.text}”`);
        break;
      case "grounding_checked":
        pushActivity(`Grounding ${d.result.claim_id}: ${d.result.status}`);
        break;
      case "eval_scored":
        pushActivity(`Eval ${d.result.kind}: ${d.result.label} (${d.result.score.toFixed(2)})`);
        break;
      case "verdict_decided":
        setVerdict(d.verdict);
        break;
      case "error":
        setError(d.message ?? "stream error");
        break;
    }
  }

  async function run(q: string) {
    if (!q.trim() || running) return;
    setRunning(true);
    setCasaDraft(null);
    setActivities([]);
    setVerdict(null);
    setError(null);
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    try {
      await askStream(q, handleEvent, abortRef.current.signal);
    } catch (err) {
      setError(String(err));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-5">
      {/* Ask box */}
      <Card>
        <CardContent className="p-4">
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              run(question);
            }}
          >
            <input
              className="flex-1 rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/30"
              placeholder="Ask the CASA legal-aid bot a question…"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
            <Button type="submit" disabled={running}>
              {running ? <Spinner /> : <Send className="h-4 w-4" />}
              Ask
            </Button>
          </form>
          <div className="mt-3 flex flex-wrap gap-2">
            {SAMPLES.map((s) => (
              <button
                key={s}
                className="rounded-full border px-3 py-1 text-xs text-muted-foreground hover:bg-muted"
                onClick={() => {
                  setQuestion(s);
                  run(s);
                }}
                disabled={running}
              >
                {s}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {error && (
        <Card className="border-quarantine/40">
          <CardContent className="p-4 text-sm text-quarantine">{error}</CardContent>
        </Card>
      )}

      {/* CASA draft — the confident, possibly-wrong answer */}
      {casaDraft && (
        <Card className="animate-in border-amber-300/60">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-amber-700">
              <Bot className="h-4 w-4" /> CASA bot answered — instantly, confidently
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{casaDraft}</p>
          </CardContent>
        </Card>
      )}

      {/* Live agent narration */}
      {running && activities.length > 0 && (
        <Card className="animate-in">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4" /> Sentinel is checking…
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1.5 text-sm text-muted-foreground">
              {activities.map((a, i) => (
                <li key={i} className="animate-in">
                  • {a}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Final verdict */}
      {verdict && <VerdictView verdict={verdict} />}
    </div>
  );
}
