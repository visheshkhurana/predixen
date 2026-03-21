import { cn } from "@/lib/utils";

interface SimStatusBadgeProps {
  status: "ready" | "running" | "complete" | "error" | "pending";
  label?: string;
}

const CONFIG = {
  ready: { color: "#34d399", defaultLabel: "Ready" },
  running: { color: "#f59e0b", defaultLabel: "Running" },
  complete: { color: "#4f7df9", defaultLabel: "Complete" },
  error: { color: "#ef4444", defaultLabel: "Error" },
  pending: { color: "#55556a", defaultLabel: "Pending" },
};

export function SimStatusBadge({ status, label }: SimStatusBadgeProps) {
  const c = CONFIG[status];
  return (
    <span
      className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border"
      style={{
        color: c.color,
        borderColor: `${c.color}33`,
        backgroundColor: `${c.color}14`,
      }}
      data-testid="sim-status-badge"
    >
      <span
        className={cn("w-1.5 h-1.5 rounded-full", status === "running" && "fc-animate-status-pulse")}
        style={{ backgroundColor: c.color }}
      />
      {label || c.defaultLabel}
    </span>
  );
}
