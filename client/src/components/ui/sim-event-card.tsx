import { cn } from "@/lib/utils";

interface SimEventCardProps {
  agentName: string;
  agentType: string;
  action: string;
  description: string;
  timestamp: string;
  sentiment?: "positive" | "neutral" | "negative";
  index?: number;
  impact?: string;
  chainedFrom?: string;
}

const TYPE_COLORS: Record<string, string> = {
  Founder: "#f59e0b",
  founder: "#f59e0b",
  Investor: "#4f7df9",
  investor: "#4f7df9",
  Customer: "#34d399",
  customer: "#34d399",
  Team: "#a78bfa",
  team: "#a78bfa",
  Market: "#f97316",
  market: "#f97316",
};

export function SimEventCard({ agentName, agentType, action, description, timestamp, sentiment, index = 0, impact, chainedFrom }: SimEventCardProps) {
  const dotColor = TYPE_COLORS[agentType] || "#6b7280";

  return (
    <div
      className={cn(
        "fc-animate-fade-up px-4 py-3 border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors",
        chainedFrom && "border-l-2 border-l-white/[0.08] ml-4"
      )}
      style={{ animationDelay: `${index * 60}ms` }}
      data-testid={`sim-event-${index}`}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold text-white/80 shrink-0"
          style={{ backgroundColor: `${dotColor}22`, border: `1px solid ${dotColor}44` }}
        >
          {agentName.charAt(0)}
        </div>
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-sm font-medium text-zinc-200 truncate">{agentName}</span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/[0.05] text-zinc-500 shrink-0">{agentType}</span>
          {chainedFrom && (
            <span className="text-[10px] text-zinc-600 shrink-0">&larr; {chainedFrom}</span>
          )}
        </div>
        <span className="text-[10px] text-zinc-600 ml-auto shrink-0 font-mono">{timestamp}</span>
      </div>
      <p className={cn(
        "text-sm leading-relaxed pl-9",
        sentiment === "positive" ? "text-zinc-300" :
        sentiment === "negative" ? "text-zinc-400" :
        "text-zinc-400"
      )}>
        {description}
      </p>
      {action && action !== 'event' && (
        <p className="text-[10px] text-zinc-500 pl-9 mt-1 flex items-center gap-1">
          <span className="opacity-50">&rarr;</span> {action}
        </p>
      )}
      {impact && impact !== 'Indirect system effect' && (
        <p className="text-[10px] text-zinc-600 pl-9 mt-0.5 flex items-center gap-1">
          <span className="opacity-50">&rarr;</span> {impact}
        </p>
      )}
    </div>
  );
}
