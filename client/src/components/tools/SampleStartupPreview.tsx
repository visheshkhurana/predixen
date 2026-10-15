import { useMemo, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { trackFunnel } from "@/lib/funnel";
import { trackEvent } from "@/lib/posthog";
import {
  SAMPLE_STARTUP,
  HORIZON_MONTHS,
  ITERATIONS,
  runSamplePreview,
} from "@/lib/simulation/sampleStartupPreview";
import { ArrowRight, FlaskConical, LineChart } from "lucide-react";

function formatCurrency(val: number): string {
  const abs = Math.abs(val);
  if (abs >= 1_000_000) return `${val < 0 ? "-" : ""}$${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${val < 0 ? "-" : ""}$${(abs / 1_000).toFixed(0)}K`;
  return `${val < 0 ? "-" : ""}$${abs.toFixed(0)}`;
}

const CHART_H = 180;
const CHART_W = 900;

/**
 * Council item 3 (2026-10-15): one-click "Try with Sample Startup" live preview.
 *
 * Client-side only. The button runs the seeded engine in
 * `@/lib/simulation/sampleStartupPreview` in the browser — no fetch, no API
 * call, no account, no persisted state — and draws the result immediately.
 * The one call to action is "Unlock your personalized forecast", which hands
 * control back to the page (`onUnlock`) to put the cursor in the email field
 * that already exists there. It creates no second capture path and sends
 * nothing anywhere.
 *
 * Everything here is about a HARD-CODED SAMPLE. It never reads the visitor's
 * inputs or their company, so it cannot state a probability about their
 * business. The copy says "illustration" on purpose; keep it that way.
 */
export function SampleStartupPreview({ onUnlock }: { onUnlock: () => void }) {
  const [shown, setShown] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  // Only computed once the visitor asks for it — the cost is small (~10 ms)
  // but there is no reason to spend it on the majority who never click, and
  // keeping it out of the initial render keeps it out of the prerendered HTML.
  const preview = useMemo(() => (shown ? runSamplePreview() : null), [shown]);

  const chart = useMemo(() => {
    if (!preview) return null;
    const { month, p10, p50, p90 } = preview.bands;
    const all = [...p10, ...p50, ...p90];
    const min = Math.min(0, ...all);
    const max = Math.max(...all, 1);
    const x = (m: number) => (m / HORIZON_MONTHS) * (CHART_W - 56) + 48;
    const y = (v: number) => CHART_H - 24 - ((v - min) / (max - min)) * (CHART_H - 48);
    const line = (arr: number[]) =>
      arr.map((v, i) => `${i === 0 ? "M" : "L"}${x(month[i]).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
    const zeroY = y(0);
    return { p10: line(p10), p50: line(p50), p90: line(p90), x, y, month, zeroY };
  }, [preview]);

  function handleTry() {
    setShown(true);
    trackFunnel("sample_preview_run", { location: "runway-calculator", is_sample: true });
  }

  function handleOpenModal() {
    setModalOpen(true);
    trackFunnel("sample_preview_unlock_click", { location: "runway-calculator", is_sample: true });
  }

  function handleUnlock() {
    setModalOpen(false);
    // PostHog only: this is an intent signal, not a conversion. The conversion
    // this experiment is measured on is signup conversion rate from this page,
    // which the page already reports as signup_view / signup_start / sign_up.
    trackEvent("sample_preview_unlock_confirm", { location: "runway-calculator", is_sample: true });
    onUnlock();
  }

  return (
    <div className="rounded-xl border bg-card/50 p-6 max-w-2xl mx-auto" data-testid="sample-preview">
      <div className="flex items-center gap-2">
        <FlaskConical className="h-4 w-4 text-primary shrink-0" />
        <h3 className="text-base font-semibold text-foreground" data-testid="text-sample-preview-heading">
          Not sure what to type?
        </h3>
      </div>
      <p className="mt-1.5 text-sm text-muted-foreground">
        Load a real example — {SAMPLE_STARTUP.name}, {formatCurrency(SAMPLE_STARTUP.cash)} in the
        bank, {formatCurrency(SAMPLE_STARTUP.revenue)}/mo revenue,{" "}
        {formatCurrency(SAMPLE_STARTUP.expenses)}/mo costs — and watch {ITERATIONS.toLocaleString()}{" "}
        possible futures play out in your browser. Nothing to sign up for, nothing sent anywhere.
      </p>

      {!shown ? (
        <Button
          className="mt-4"
          onClick={handleTry}
          data-testid="button-sample-preview"
        >
          <FlaskConical className="mr-2 h-4 w-4" />
          Try with Sample Startup
        </Button>
      ) : (
        preview &&
        chart && (
          <div className="mt-5" data-testid="sample-preview-result">
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-lg border bg-background/50 p-3 text-center">
                <p className="text-xl font-bold font-mono text-foreground" data-testid="text-sample-straight-line">
                  {preview.deterministicRunoutMonth === null
                    ? "Never"
                    : `Month ${preview.deterministicRunoutMonth}`}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">One straight-line forecast</p>
              </div>
              <div className="rounded-lg border bg-background/50 p-3 text-center">
                <p className="text-xl font-bold font-mono text-foreground" data-testid="text-sample-median">
                  {preview.medianRunoutMonth === null ? "Never" : `Month ${preview.medianRunoutMonth}`}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Median of {ITERATIONS.toLocaleString()} runs
                </p>
              </div>
              <div className="rounded-lg border bg-background/50 p-3 text-center">
                <p className="text-xl font-bold font-mono text-foreground" data-testid="text-sample-runout-18">
                  {Math.round(preview.runoutByMonth18 * 100)}%
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">Out of cash by month 18</p>
              </div>
            </div>

            <Card className="mt-4">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <LineChart className="h-4 w-4 text-primary" />
                  Cash remaining, {ITERATIONS.toLocaleString()} simulated futures
                </CardTitle>
              </CardHeader>
              <CardContent>
                <svg
                  width="100%"
                  height={CHART_H}
                  viewBox={`0 0 ${CHART_W} ${CHART_H}`}
                  preserveAspectRatio="none"
                  role="img"
                  aria-label={`Simulated cash balance for ${SAMPLE_STARTUP.name}: P10, median and P90 over ${HORIZON_MONTHS} months`}
                  data-testid="chart-sample-preview"
                >
                  <defs>
                    <linearGradient id="sampleBandGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.22" />
                      <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0.02" />
                    </linearGradient>
                  </defs>
                  {/* the month the cash hits zero */}
                  <line
                    x1="0"
                    y1={chart.zeroY}
                    x2={CHART_W}
                    y2={chart.zeroY}
                    stroke="hsl(var(--border))"
                    strokeWidth="1"
                  />
                  {/* P10–P90 band */}
                  <path
                    d={
                      chart.p90 +
                      " " +
                      [...chart.month]
                        .reverse()
                        .map((m, i) => {
                          const v = preview.bands.p10[preview.bands.p10.length - 1 - i];
                          return `L${chart.x(m).toFixed(1)},${chart.y(v).toFixed(1)}`;
                        })
                        .join(" ") +
                      " Z"
                    }
                    fill="url(#sampleBandGrad)"
                  />
                  <path d={chart.p90} fill="none" stroke="hsl(var(--muted-foreground))" strokeWidth="1" strokeDasharray="4 3" />
                  <path d={chart.p10} fill="none" stroke="hsl(var(--muted-foreground))" strokeWidth="1" strokeDasharray="4 3" />
                  <path d={chart.p50} fill="none" stroke="hsl(var(--primary))" strokeWidth="2.5" />
                  <text x="8" y={chart.zeroY - 6} fill="hsl(var(--muted-foreground))" fontSize="11">
                    $0
                  </text>
                  {[0, 6, 12, 18, 24, 30, 36].map((m) => (
                    <text
                      key={m}
                      x={chart.x(m)}
                      y={CHART_H - 6}
                      fill="hsl(var(--muted-foreground))"
                      fontSize="11"
                      textAnchor="middle"
                    >
                      M{m}
                    </text>
                  ))}
                </svg>
                <p className="mt-2 text-xs text-muted-foreground">
                  Solid line is the median of {ITERATIONS.toLocaleString()} runs; the shaded band is
                  the P10–P90 range. Every run draws its own growth and cost path, so the band
                  widens with time — and it is the width, not the middle, that matters. A
                  straight-line forecast gives one of these paths and cannot tell you which one you
                  are on.
                </p>
              </CardContent>
            </Card>

            <Button className="mt-4 w-full sm:w-auto" onClick={handleOpenModal} data-testid="button-sample-unlock">
              Unlock your personalized forecast
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
            <p className="mt-2 text-xs text-muted-foreground">
              That was {SAMPLE_STARTUP.name} — an illustration, not a prediction about your company.
              Replace the four numbers above with yours at any time; the calculator at the top of
              this page is unchanged.
            </p>
          </div>
        )
      )}

      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="max-w-lg" data-testid="dialog-sample-unlock">
          <DialogHeader>
            <DialogTitle>Unlock your personalized forecast</DialogTitle>
            <DialogDescription>
              You just saw {SAMPLE_STARTUP.name}&apos;s {ITERATIONS.toLocaleString()} simulated
              futures. Yours will look different — and you can have it in about a minute.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2 text-sm text-muted-foreground">
            <p>
              With your own four numbers you get the same chart, plus the two things the sample
              cannot give you: the month <em>your</em> cash runs out on the median path, and how
              much of the range is worse than that.
            </p>
            <p>
              No account needed to start. Enter your email and we send you the result you already
              have on this page, so you can forward it to a co-founder.
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button onClick={handleUnlock} className="sm:flex-1" data-testid="button-sample-unlock-confirm">
              Use my email
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
            <Button variant="outline" onClick={() => setModalOpen(false)} data-testid="button-sample-unlock-dismiss">
              Not now
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
