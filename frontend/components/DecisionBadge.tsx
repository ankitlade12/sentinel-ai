import { CheckCircle2, ShieldAlert, Wrench } from "lucide-react";
import type { Decision } from "@/types/generated";
import { Badge } from "@/components/ui/primitives";

const MAP: Record<Decision, { tone: "allow" | "repair" | "quarantine"; label: string; Icon: typeof CheckCircle2 }> = {
  allow: { tone: "allow", label: "Allowed", Icon: CheckCircle2 },
  repair_allow: { tone: "repair", label: "Corrected & cited", Icon: Wrench },
  quarantine: { tone: "quarantine", label: "Held for review", Icon: ShieldAlert },
};

export function DecisionBadge({ decision }: { decision: Decision }) {
  const { tone, label, Icon } = MAP[decision];
  return (
    <Badge tone={tone} className="px-3 py-1 text-[0.8rem]">
      <Icon className="h-3.5 w-3.5" />
      {label}
    </Badge>
  );
}
