import { useEffect, useMemo, useRef, useState } from "react";
import { motion, useInView, useReducedMotion } from "framer-motion";
import { FlaskConical } from "lucide-react";

const W = 560;
const H = 260;
const MONTHS = 24;
const ITERATIONS = 10000;

/** Deterministic pseudo-random so the chart is stable between loops. */
function mulberry32(seed: number) {
  return function () {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function buildBands() {
  const rand = mulberry32(42);
  const p10: number[] = [];
  const p50: number[] = [];
  const p90: number[] = [];
  let base = 210; // starting cash (k)
  for (let m = 0; m <= MONTHS; m++) {
    const burn = 11 + m * 0.35;
    const growth = m * 2.1;
    const mid = Math.max(0, base - burn * m + growth * m * 0.9 + (rand() - 0.5) * 6);
    p50.push(mid);
    p10.push(Math.max(0, mid - (14 + m * 3.1)));
    p90.push(mid + 12 + m * 3.4);
  }
  const max = Math.max(...p90) * 1.08;
  const x = (m: number) => (m / MONTHS) * (W - 60) + 44;
  const y = (v: number) => H - 30 - (v / max) * (H - 55);
  const line = (arr: number[]) => arr.map((v, m) => `${m === 0 ? "M" : "L"}${x(m).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const area = `${line(p90)} ${[...p10].reverse().map((v, i) => `L${x(MONTHS - i).toFixed(1)},${y(v).toFixed(1)}`).join(" ")} Z`;
  return { p10: line(p10), p50: line(p50), p90: line(p90), area, x, y, p50raw: p50 };
}

export function MonteCarloDemo() {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: false, margin: "-15% 0px" });
  const [iter, setIter] = useState(0);
  const [runId, setRunId] = useState(0);
  const bands = useMemo(buildBands, []);

  // Iteration counter races to 10,000 while paths draw, then loops.
  useEffect(() => {
    if (!inView || reduced) {
      setIter(ITERATIONS);
      return;
    }
    let raf: number;
    let start: number | null = null;
    const DURATION = 2600;
    const tick = (t: number) => {
      if (start === null) start = t;
      const p = Math.min(1, (t - start) / DURATION);
      const eased = 1 - Math.pow(1 - p, 3);
      setIter(Math.round(eased * ITERATIONS));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    setIter(0);
    raf = requestAnimationFrame(tick);
    const loop = setInterval(() => {
      start = null;
      setIter(0);
      setRunId((r) => r + 1);
      raf = requestAnimationFrame(tick);
    }, 7000);
    return () => {
      cancelAnimationFrame(raf);
      clearInterval(loop);
    };
  }, [inView, reduced]);

  const draw = reduced
    ? { pathLength: 1, opacity: 1 }
    : { pathLength: [0, 1] as number[], opacity: [0, 1] as number[] };

  return (
    <div ref={ref} className="relative rounded-2xl glass-medium p-5 md:p-6 overflow-hidden" data-testid="demo-monte-carlo">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-md bg-violet-500/15 flex items-center justify-center">
            <FlaskConical className="h-3.5 w-3.5 text-violet-400" />
          </div>
          <span className="text-sm font-medium text-foreground">Runway simulation</span>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          <span data-testid="text-demo-iterations">{iter.toLocaleString()} / 10,000 runs</span>
        </div>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label="Monte Carlo runway simulation fan chart">
        {/* grid */}
        {[0.25, 0.5, 0.75].map((g) => (
          <line key={g} x1={44} x2={W - 16} y1={H - 30 - g * (H - 55)} y2={H - 30 - g * (H - 55)} className="stroke-border" strokeDasharray="3 6" strokeWidth="1" />
        ))}
        <line x1={44} x2={W - 16} y1={H - 30} y2={H - 30} className="stroke-border" strokeWidth="1" />

        {/* confidence band */}
        <motion.path
          key={`area-${runId}`}
          d={bands.area}
          className="fill-violet-500/15"
          initial={reduced ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1.4, delay: 0.6 }}
        />
        {/* P90 */}
        <motion.path key={`p90-${runId}`} d={bands.p90} fill="none" strokeWidth="1.5" className="stroke-emerald-400/70"
          initial={reduced ? false : { pathLength: 0 }} animate={draw} transition={{ duration: 1.8, ease: "easeOut" }} />
        {/* P10 */}
        <motion.path key={`p10-${runId}`} d={bands.p10} fill="none" strokeWidth="1.5" className="stroke-rose-400/70"
          initial={reduced ? false : { pathLength: 0 }} animate={draw} transition={{ duration: 1.8, ease: "easeOut", delay: 0.15 }} />
        {/* P50 */}
        <motion.path key={`p50-${runId}`} d={bands.p50} fill="none" strokeWidth="2.5" className="stroke-primary"
          initial={reduced ? false : { pathLength: 0 }} animate={draw} transition={{ duration: 2.1, ease: "easeOut", delay: 0.3 }} />

        {/* axis labels */}
        <text x={44} y={H - 12} className="fill-muted-foreground" fontSize="10">Now</text>
        <text x={W - 70} y={H - 12} className="fill-muted-foreground" fontSize="10">+24 mo</text>
      </svg>

      <div className="mt-3 grid grid-cols-3 gap-3 text-center">
        {[
          { label: "P10 runway", value: "11.4 mo", tone: "text-rose-400" },
          { label: "P50 runway", value: "18.2 mo", tone: "text-primary" },
          { label: "P90 runway", value: "26.8 mo", tone: "text-emerald-400" },
        ].map((s) => (
          <div key={s.label} className="rounded-lg bg-muted/40 py-2">
            <p className={`text-sm font-bold font-mono ${s.tone}`}>{s.value}</p>
            <p className="text-[10px] uppercase tracking-wide text-muted-foreground mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
