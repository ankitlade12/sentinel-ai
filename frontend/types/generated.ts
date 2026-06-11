// AUTO-GENERATED from backend Pydantic models by scripts/generate_typescript_types.py
// Do not edit by hand — run `make types`.

export interface AgentActivity {
  activity_type: string;
  summary: string;
  detail?: Record<string, unknown>;
}

export interface AskRequest {
  question: string;
  org_id?: string;
  conversation_id?: string | null;
  include_draft?: boolean;
}

export interface CasaAnswer {
  answer: string;
  topic_hint?: string;
  model?: string;
  generated_at: string;
}

export interface CasaDrafted {
  answer: string;
  topic_hint?: string;
}

export interface CasaRequest {
  question: string;
  conversation_id?: string | null;
}

export interface Claim {
  id: string;
  text: string;
  claim_type: ClaimType;
  subject: string;
  checkable: boolean;
}

export interface ClaimExtracted {
  claim: Claim;
}

export interface ClaimExtraction {
  claims: Claim[];
  summary: string;
}

export type ClaimType = "date" | "deadline" | "amount" | "form_number" | "eligibility" | "legal_rule" | "procedure" | "contact" | "other";

export interface CorpusDoc {
  id: string;
  title: string;
  topic: string;
  source_url?: string | null;
  last_verified: string;
  path: string;
}

export type Coverage = "in_corpus" | "out_of_corpus";

export type Decision = "allow" | "repair_allow" | "quarantine";

export interface DoneSignal {
  verdict_id: string;
  decision: Decision;
}

export type EvalKind = "hallucination" | "qa_correctness" | "toxicity";

export interface EvalResult {
  kind: EvalKind;
  label: string;
  score: number;
  explanation: string;
  evaluator?: string;
  passed: boolean;
}

export interface EvalScored {
  result: EvalResult;
}

export interface GroundingChecked {
  result: GroundingResult;
}

export interface GroundingResult {
  claim_id: string;
  claim_text: string;
  status: GroundingStatus;
  confidence: number;
  passages?: SourcePassage[];
  explanation: string;
  corrected_text?: string | null;
}

export type GroundingStatus = "supported" | "contradicted" | "not_found";

export interface PlanStep {
  tool: string;
  why: string;
}

export interface PlanWritten {
  plan: SentinelPlan;
}

export interface ReviewAction {
  action: ReviewActionType;
  staff_id?: string;
  staff_note?: string | null;
  corrected_answer?: string | null;
}

export type ReviewActionType = "release" | "correct" | "dismiss";

export type ReviewStatus = "pending" | "released" | "corrected" | "dismissed";

export interface SentinelPlan {
  triage: TriageVerdict;
  path: "light" | "full";
  steps: PlanStep[];
  summary: string;
}

export interface SentinelVerdict {
  id: string;
  org_id?: string;
  created_at: string;
  question: string;
  draft_answer: string;
  topic: string;
  plan: SentinelPlan;
  claims?: Claim[];
  grounding?: GroundingResult[];
  evals?: EvalResult[];
  decision: Decision;
  delivered_answer: string;
  user_message?: string | null;
  corrected_answer?: string | null;
  rationale: string;
  failed_claim_ids?: string[];
  requires_human_review?: boolean;
  trace_id?: string | null;
  trace_url?: string | null;
  latency_ms?: number;
  policy_snapshot?: Record<string, number>;
  review_status?: ReviewStatus;
  staff_note?: string | null;
  resolved_at?: string | null;
}

export interface SourcePassage {
  doc_id: string;
  doc_title: string;
  source_url?: string | null;
  page?: string | null;
  last_verified?: string | null;
  text: string;
  score: number;
}

export type Specificity = "general_info" | "specific_claim";

export type StakesLevel = "low" | "medium" | "high";

export interface StreamError {
  code: string;
  message: string;
  recoverable?: boolean;
}

export interface TopicStat {
  topic: string;
  answered?: number;
  cleared?: number;
  corrected?: number;
  held?: number;
}

export interface TriageReady {
  triage: TriageVerdict;
}

export interface TriageVerdict {
  topic: string;
  stakes: StakesLevel;
  specificity: Specificity;
  coverage: Coverage;
  coverage_score: number;
  risk_signals?: string[];
  reasoning: string;
}

export interface TrustReport {
  org_name?: string;
  week_of: string;
  generated_at: string;
  total_answered?: number;
  cleared?: number;
  corrected?: number;
  held?: number;
  reviewed?: number;
  headline: string;
  what_was_caught?: string[];
  trend: string;
  riskiest_topic?: string;
  safest_topic?: string;
  corpus_gaps?: string[];
  topic_stats?: TopicStat[];
  disclaimer?: string;
}

export interface VerdictDecided {
  verdict: SentinelVerdict;
}
