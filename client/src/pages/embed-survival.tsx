import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Rocket, ArrowRight } from "lucide-react";

function calc(cash: number, burn: number, revenue: number) {
  const net = Math.max(0, burn - revenue);
  if (net === 0) return { months: 999, status: "Profitable", tone: "text-emerald-400" };
  const months = Math.floor(cash / net);
  if (months >= 18) return { months, status: "Healthy", tone: "text-emerald-400" };
  if (months >= 12) return { months, status: "Watch", tone: "text-amber-400" };
  if (months >= 6) return { months, status: "Raise soon", tone: "text-orange-400" };
  return { months, status: "Critical", tone: "text-red-400" };
}

export default function EmbedSurvivalWidget() {
  const [cash, setCash] = useState(500000);
  const [burn, setBurn] = useState(80000);
  const [revenue, setRevenue] = useState(20000);
  const r = calc(cash, burn, revenue);

  const targetUrl = `https://founderconsole.ai/survival-simulator?cash=${cash}&burn=${burn}&revenue=${revenue}&utm_source=embed&utm_medium=widget`;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-4 flex items-center justify-center" data-testid="embed-survival-widget">
      <Card className="w-full max-w-md border-zinc-800 bg-zinc-900/80">
        <CardContent className="p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Rocket className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-semibold">Startup Runway</h1>
          </div>
          <p className="text-xs text-muted-foreground">
            Quick estimate. For full Monte Carlo with P10/P50/P90, open the full simulator.
          </p>

          <div className="grid grid-cols-1 gap-3">
            <div>
              <Label htmlFor="e-cash" className="text-xs">Cash on hand ($)</Label>
              <Input id="e-cash" type="number" value={cash}
                onChange={(e) => setCash(Number(e.target.value) || 0)}
                data-testid="embed-input-cash" className="bg-zinc-800 border-zinc-700" />
            </div>
            <div>
              <Label htmlFor="e-burn" className="text-xs">Monthly burn ($)</Label>
              <Input id="e-burn" type="number" value={burn}
                onChange={(e) => setBurn(Number(e.target.value) || 0)}
                data-testid="embed-input-burn" className="bg-zinc-800 border-zinc-700" />
            </div>
            <div>
              <Label htmlFor="e-rev" className="text-xs">Monthly revenue ($)</Label>
              <Input id="e-rev" type="number" value={revenue}
                onChange={(e) => setRevenue(Number(e.target.value) || 0)}
                data-testid="embed-input-revenue" className="bg-zinc-800 border-zinc-700" />
            </div>
          </div>

          <div className="rounded-md border border-zinc-800 bg-zinc-950/60 p-4">
            <div className="text-xs text-muted-foreground">Estimated runway</div>
            <div className="flex items-baseline justify-between mt-1">
              <div className="text-3xl font-bold" data-testid="embed-result-months">
                {r.months >= 999 ? "Profitable" : `${r.months} mo`}
              </div>
              <div className={`text-sm font-medium ${r.tone}`} data-testid="embed-result-status">{r.status}</div>
            </div>
          </div>

          <Button
            className="w-full"
            onClick={() => window.open(targetUrl, "_blank", "noopener")}
            data-testid="embed-cta-full-sim"
          >
            Run full Monte Carlo on FounderConsole <ArrowRight className="ml-2 h-4 w-4" />
          </Button>

          <a
            href="https://founderconsole.ai/survival-simulator?utm_source=embed&utm_medium=footer"
            target="_blank" rel="noopener noreferrer"
            className="text-[10px] text-muted-foreground text-center block hover:text-primary"
            data-testid="embed-footer-link"
          >
            Powered by FounderConsole
          </a>
        </CardContent>
      </Card>
    </div>
  );
}
