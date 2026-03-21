import { cn } from "@/lib/utils";
import { useState, useEffect, useRef } from "react";
import { ChevronUp, ChevronDown, Terminal } from "lucide-react";

interface LogEntry {
  time: string;
  msg: string;
  type?: "info" | "success" | "error" | "warn";
}

export function SimTerminalDrawer({ logs, label, id }: { logs: LogEntry[]; label?: string; id?: string }) {
  const [open, setOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const last = logs[logs.length - 1];

  useEffect(() => {
    if (open && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs.length, open]);

  if (logs.length === 0) return null;

  return (
    <div className={cn(
      "fixed bottom-0 left-[var(--sidebar-width,240px)] right-0 z-40 transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]",
      open ? "h-56" : "h-9"
    )} data-testid="sim-terminal-drawer">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 h-9 bg-[#0d0d12] border-t border-white/[0.06] text-[11px] font-mono cursor-pointer hover:bg-[#151520] transition-colors"
        data-testid="sim-terminal-toggle"
      >
        <div className="flex items-center gap-2 text-zinc-500 min-w-0">
          <Terminal className="w-3 h-3 shrink-0" />
          <span className="uppercase tracking-widest text-zinc-600 shrink-0">{label || "System Log"}</span>
          {last && !open && (
            <span className={cn(
              "truncate",
              last.type === "success" ? "text-emerald-400" : last.type === "error" ? "text-red-400" : "text-zinc-500"
            )}>
              {last.type === "success" && "✓ "}{last.msg}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {id && <span className="text-zinc-600">{id}</span>}
          {open ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
        </div>
      </button>

      {open && (
        <div ref={scrollRef} className="h-[calc(100%-2.25rem)] overflow-y-auto bg-[#08080c] px-4 py-2 font-mono text-[11px] space-y-px scroll-smooth">
          {logs.map((l, i) => (
            <div key={i} className="flex gap-3 leading-relaxed">
              <span className="text-zinc-600 shrink-0 select-none">{l.time}</span>
              <span className={cn(
                l.type === "success" ? "text-emerald-400" :
                l.type === "error" ? "text-red-400" :
                l.type === "warn" ? "text-amber-400" :
                "text-zinc-400"
              )}>{l.msg}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
