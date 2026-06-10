/** Typed client for the Sentinel backend. All calls are same-origin /api/*;
 *  Next.js proxies them to FastAPI (see next.config.mjs). */

import type {
  CasaAnswer,
  CorpusDoc,
  ReviewAction,
  SentinelVerdict,
  TrustReport,
} from "@/types/generated";

export interface AskResponse {
  draft: CasaAnswer;
  verdict: SentinelVerdict;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export async function ask(question: string): Promise<AskResponse> {
  const res = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  return json<AskResponse>(res);
}

export async function listQuarantine(): Promise<SentinelVerdict[]> {
  return json(await fetch("/api/quarantine"));
}

export async function listVerdicts(limit = 50): Promise<SentinelVerdict[]> {
  return json(await fetch(`/api/verdicts?limit=${limit}`));
}

export async function getTrustReport(): Promise<TrustReport> {
  return json(await fetch("/api/report"));
}

export async function getCorpus(): Promise<CorpusDoc[]> {
  return json(await fetch("/api/corpus"));
}

export async function resolveQuarantine(
  id: string,
  action: ReviewAction,
): Promise<SentinelVerdict> {
  const res = await fetch(`/api/quarantine/${id}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(action),
  });
  return json<SentinelVerdict>(res);
}

export interface StreamEvent {
  event: string;
  data: unknown;
}

/** Consume the POST Server-Sent-Events stream from /api/ask/stream,
 *  invoking `onEvent` for each named event as the agent works. */
export async function askStream(
  question: string,
  onEvent: (e: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch("/api/ask/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });
  if (!res.body) throw new Error("no response body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      let event = "message";
      const dataLines: string[] = [];
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      }
      if (dataLines.length === 0) continue;
      try {
        onEvent({ event, data: JSON.parse(dataLines.join("\n")) });
      } catch {
        /* ignore keep-alive / non-JSON frames */
      }
    }
  }
}
