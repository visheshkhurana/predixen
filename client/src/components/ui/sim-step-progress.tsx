import { cn } from "@/lib/utils";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";

interface SimStep {
  id: string;
  label: string;
  summary?: string;
  status: "complete" | "active" | "pending";
}

export function SimStepProgress({ steps }: { steps: SimStep[] }) {
  return (
    <div className="flex items-center gap-0.5 px-4 py-2.5 border-b border-white/[0.06] bg-[#111118]/60 backdrop-blur-sm overflow-x-auto" data-testid="sim-step-progress">
      {steps.map((step, i) => (
        <div key={step.id} className="flex items-center gap-0.5 shrink-0">
          <div className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-300",
            step.status === "complete" && "text-emerald-400",
            step.status === "active" && "text-blue-400 bg-blue-500/10 border border-blue-500/20",
            step.status === "pending" && "text-zinc-500",
          )}>
            {step.status === "complete" && <CheckCircle2 className="w-3.5 h-3.5" />}
            {step.status === "active" && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            {step.status === "pending" && <Circle className="w-3.5 h-3.5 opacity-40" />}
            <span>{step.label}</span>
            {step.summary && step.status === "complete" && (
              <span className="text-[10px] text-zinc-500 font-mono ml-1">{step.summary}</span>
            )}
          </div>
          {i < steps.length - 1 && (
            <div className={cn(
              "w-6 h-px mx-0.5 transition-colors duration-500",
              step.status === "complete" ? "bg-emerald-400/50" : "bg-white/[0.06]"
            )} />
          )}
        </div>
      ))}
    </div>
  );
}
