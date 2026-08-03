import { useMemo } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Database } from "lucide-react";
import { NumberTicker } from "@/components/ui/motion-primitives";
import { Tilt3D } from "./Tilt3D";

const CONNECTORS = ["Stripe", "QuickBooks", "Mercury", "Gusto"];

function spark(seed: number[]) {
  const W = 120;
  const H = 36;
  const max = Math.max(...seed);
  const min = Math.min(...seed);
  return seed
    .map((v, i) => `${i === 0 ? "M" : "L"}${((i / (seed.length - 1)) * W).toFixed(1)},${(H - 4 - ((v - min) / (max - min || 1)) * (H - 8)).toFixed(1)}`)
    .join(" ");
}

const KPIS = [
  { label: "MRR", value: 48.7, prefix: "$", suffix: "k", trend: "+23% MoM", tone: "text-emerald-400", stroke: "stroke-emerald-400", data: [22, 25, 24, 29, 33, 36, 41, 44, 48.7] },
  { label: "Net burn", value: 31.2, prefix: "$", suffix: "k", trend: "-4% MoM", tone: "text-primary", stroke: "stroke-primary", data: [39, 38, 40, 36, 35, 34, 33, 32, 31.2] },
  { label: "Runway", value: 18.2, prefix: "", suffix: " mo", trend: "P50", tone: "text-violet-400", stroke: "stroke-violet-400", data: [12, 13, 12.5, 14, 15, 15.8, 16.9, 17.5, 18.2] },
];

export function TwinDashboardDemo() {
  const reduced = useReducedMotion();
  const paths = useMemo(() => KPIS.map((k) => spark(k.data)), []);

  return (
    <Tilt3D className="w-full" maxTilt={6}>
      <div className="rounded-2xl glass-medium p-5 md:p-6 shadow-2xl shadow-primary/10" style={{ transformStyle: "preserve-3d" }} data-testid="demo-digital-twin">
        <div className="flex items-center justify-between mb-4" style={{ transform: "translateZ(28px)" }}>
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-md bg-blue-500/15 flex items-center justify-center">
              <Database className="h-3.5 w-3.5 text-blue-400" />
            </div>
            <span className="text-sm font-medium text-foreground">Digital Twin — live</span>
          </div>
          <div className="flex gap-1.5">
            {CONNECTORS.map((c, i) => (
              <span key={c} className="hidden sm:inline-flex items-center gap-1.5 rounded-full border bg-muted/40 px-2 py-0.5 text-[10px] text-muted-foreground">
                <motion.span
                  className="h-1.5 w-1.5 rounded-full bg-emerald-500"
                  animate={reduced ? {} : { opacity: [0.3, 1, 0.3] }}
                  transition={{ repeat: Infinity, duration: 2, delay: i * 0.45 }}
                />
                {c}
              </span>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3" style={{ transform: "translateZ(40px)" }}>
          {KPIS.map((k, i) => (
            <div key={k.label} className="rounded-xl border bg-card/60 p-4">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{k.label}</p>
              <p className={`mt-1 text-xl font-bold font-mono ${k.tone}`}>
                {k.prefix}
                <NumberTicker value={k.value} decimals={1} />
                {k.suffix}
              </p>
              <svg viewBox="0 0 120 36" className="mt-2 w-full h-9 overflow-visible">
                <motion.path
                  d={paths[i]}
                  fill="none"
                  strokeWidth="2"
                  className={k.stroke}
                  initial={reduced ? false : { pathLength: 0 }}
                  whileInView={{ pathLength: 1 }}
                  viewport={{ once: true, margin: "-10%" }}
                  transition={{ duration: 1.6, ease: "easeOut", delay: i * 0.2 }}
                />
              </svg>
              <p className="mt-1.5 text-[11px] text-muted-foreground">{k.trend}</p>
            </div>
          ))}
        </div>

        <div className="mt-3 rounded-xl border bg-card/60 p-3 flex items-center justify-between" style={{ transform: "translateZ(20px)" }}>
          <span className="text-xs text-muted-foreground">Last sync — 2 min ago · 37 connectors available</span>
          <span className="inline-flex items-center gap-1.5 text-xs text-emerald-400">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            Healthy
          </span>
        </div>
      </div>
    </Tilt3D>
  );
}
