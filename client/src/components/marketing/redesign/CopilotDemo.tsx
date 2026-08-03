import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useInView, useReducedMotion } from "framer-motion";
import { Sparkles, User } from "lucide-react";

const EXCHANGES = [
  {
    q: "Can we afford 2 senior engineers next quarter?",
    a: "Yes — with caveats. Hiring both in Q4 cuts P50 runway from 18.2 to 14.1 months. Staggering the second hire by 8 weeks keeps you above your 12-month board floor in 87% of simulations.",
    chip: { label: "P50 runway impact", value: "18.2 → 14.1 mo" },
  },
  {
    q: "When should we start raising our Series A?",
    a: "Start in ~5 months. Your MoM growth (23%) compounds to a stronger story by March, and you'd still hold 9+ months of runway through a 4-month raise in 91% of scenarios.",
    chip: { label: "Optimal raise window", value: "Mar – Jun" },
  },
  {
    q: "What happens if we raise prices 15%?",
    a: "Assuming 6% churn uplift (benchmark median), net revenue rises 8.3% and P50 runway extends by 3.1 months. Break-even on the churn risk sits at 11% — you have margin.",
    chip: { label: "Runway extension", value: "+3.1 mo" },
  },
];

export function CopilotDemo() {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: false, margin: "-15% 0px" });
  const [idx, setIdx] = useState(0);
  const [phase, setPhase] = useState<"typing-q" | "thinking" | "answering" | "done">("typing-q");
  const [qChars, setQChars] = useState(0);
  const [aChars, setAChars] = useState(0);

  const ex = EXCHANGES[idx % EXCHANGES.length];

  useEffect(() => {
    if (!inView) return;
    if (reduced) {
      setQChars(ex.q.length);
      setAChars(ex.a.length);
      setPhase("done");
      return;
    }
    let cancelled = false;
    const timers: ReturnType<typeof setTimeout>[] = [];
    const t = (fn: () => void, ms: number) => timers.push(setTimeout(() => !cancelled && fn(), ms));

    setPhase("typing-q");
    setQChars(0);
    setAChars(0);
    // type the question
    for (let i = 1; i <= ex.q.length; i++) t(() => setQChars(i), i * 28);
    const qDone = ex.q.length * 28 + 200;
    t(() => setPhase("thinking"), qDone);
    t(() => setPhase("answering"), qDone + 900);
    for (let i = 1; i <= ex.a.length; i++) t(() => setAChars(i), qDone + 900 + i * 11);
    const aDone = qDone + 900 + ex.a.length * 11;
    t(() => setPhase("done"), aDone);
    t(() => setIdx((v) => v + 1), aDone + 3200);
    return () => {
      cancelled = true;
      timers.forEach(clearTimeout);
    };
  }, [idx, inView, reduced, ex.q, ex.a]);

  return (
    <div ref={ref} className="rounded-2xl glass-medium p-5 md:p-6 min-h-[340px] flex flex-col" data-testid="demo-copilot">
      <div className="flex items-center gap-2 mb-4">
        <div className="h-7 w-7 rounded-md bg-amber-500/15 flex items-center justify-center">
          <Sparkles className="h-3.5 w-3.5 text-amber-400" />
        </div>
        <span className="text-sm font-medium text-foreground">Founder Copilot</span>
        <span className="ml-auto text-[10px] uppercase tracking-wider text-muted-foreground">Live session</span>
      </div>

      <div className="space-y-3 flex-1">
        {/* question bubble */}
        <div className="flex items-start gap-2.5 justify-end">
          <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-primary/15 border border-primary/20 px-4 py-2.5 text-sm text-foreground">
            {ex.q.slice(0, qChars)}
            {phase === "typing-q" && <span className="inline-block w-0.5 h-4 bg-primary ml-0.5 animate-pulse align-middle" />}
          </div>
          <div className="h-7 w-7 shrink-0 rounded-full bg-muted flex items-center justify-center">
            <User className="h-3.5 w-3.5 text-muted-foreground" />
          </div>
        </div>

        {/* thinking / answer */}
        <AnimatePresence mode="popLayout">
          {phase !== "typing-q" && (
            <motion.div
              key={`a-${idx}`}
              initial={reduced ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex items-start gap-2.5"
            >
              <div className="h-7 w-7 shrink-0 rounded-full bg-gradient-to-br from-primary to-violet-500 flex items-center justify-center shadow-lg shadow-primary/25">
                <Sparkles className="h-3.5 w-3.5 text-white" />
              </div>
              <div className="max-w-[85%] rounded-2xl rounded-tl-sm bg-muted/50 border px-4 py-2.5 text-sm text-muted-foreground leading-relaxed">
                {phase === "thinking" ? (
                  <span className="flex gap-1 py-1" aria-label="Copilot is thinking">
                    {[0, 1, 2].map((d) => (
                      <motion.span
                        key={d}
                        className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60"
                        animate={reduced ? {} : { opacity: [0.3, 1, 0.3] }}
                        transition={{ repeat: Infinity, duration: 1, delay: d * 0.18 }}
                      />
                    ))}
                  </span>
                ) : (
                  <>
                    {ex.a.slice(0, aChars)}
                    {phase === "answering" && <span className="inline-block w-0.5 h-4 bg-muted-foreground ml-0.5 animate-pulse align-middle" />}
                  </>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* metric chip */}
        <AnimatePresence>
          {phase === "done" && (
            <motion.div
              key={`chip-${idx}`}
              initial={reduced ? false : { opacity: 0, scale: 0.9, y: 6 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ type: "spring", stiffness: 260, damping: 20 }}
              className="ml-10 inline-flex items-center gap-2 rounded-lg border border-primary/25 bg-primary/10 px-3 py-1.5"
            >
              <span className="text-[10px] uppercase tracking-wide text-muted-foreground">{ex.chip.label}</span>
              <span className="text-xs font-bold font-mono text-primary">{ex.chip.value}</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
