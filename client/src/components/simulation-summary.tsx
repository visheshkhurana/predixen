import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, CheckCircle, TrendingDown, Calendar, DollarSign, Flame } from "lucide-react";
import type { SimulationResult } from "@shared/schema";
import { cn, formatCurrencyFull } from "@/lib/utils";

interface SimulationSummaryProps {
  result: SimulationResult;
  currency?: string;
}

export function SimulationSummary({ result, currency = 'USD' }: SimulationSummaryProps) {
  const { summary } = result;

  const formatCurrency = (value: number) => formatCurrencyFull(value, currency);

  const getRunwayStatus = () => {
    if (!summary.runwayMonths) return { status: "safe", label: "Profitable" };
    if (summary.runwayMonths <= 6) return { status: "danger", label: "Critical" };
    if (summary.runwayMonths <= 12) return { status: "warning", label: "Caution" };
    return { status: "safe", label: "Healthy" };
  };

  const runwayStatus = getRunwayStatus();

  const getRecommendations = () => {
    const recommendations: string[] = [];
    
    if (summary.runwayMonths && summary.runwayMonths <= 6) {
      recommendations.push("Consider immediate cost reduction measures");
      recommendations.push("Accelerate fundraising efforts");
    } else if (summary.runwayMonths && summary.runwayMonths <= 12) {
      recommendations.push("Start planning for next funding round");
      recommendations.push("Identify non-essential expenses to cut");
    }
    
    if (summary.avgMonthlyBurn > summary.totalRevenue / result.projections.length) {
      recommendations.push("Focus on increasing revenue to reduce burn rate");
    }
    
    if (recommendations.length === 0) {
      recommendations.push("Continue monitoring key metrics");
      recommendations.push("Consider strategic growth investments");
    }
    
    return recommendations;
  };

  return (
    <div className="space-y-6">
      <Card data-testid="card-simulation-summary">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <CardTitle className="text-lg">{result.scenarioName}</CardTitle>
            <Badge
              variant={runwayStatus.status === "danger" ? "destructive" : "secondary"}
              className={cn(
                runwayStatus.status === "warning" && "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
                runwayStatus.status === "safe" && "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400"
              )}
            >
              {runwayStatus.status === "danger" && <AlertTriangle className="h-3 w-3 mr-1" />}
              {runwayStatus.status === "safe" && <CheckCircle className="h-3 w-3 mr-1" />}
              {runwayStatus.label}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Calendar className="h-3 w-3" />
                <span>Runway</span>
              </div>
              <p className="text-xl font-semibold font-mono" data-testid="text-runway-months">
                {summary.runwayMonths ? `${summary.runwayMonths} mo` : "N/A"}
              </p>
              {summary.cashOutDate && (
                <p className="text-xs text-muted-foreground">
                  Until {summary.cashOutDate}
                </p>
              )}
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Flame className="h-3 w-3" />
                <span>Avg Monthly Burn</span>
              </div>
              <p className="text-xl font-semibold font-mono text-red-600 dark:text-red-400" data-testid="text-avg-burn">
                {formatCurrency(summary.avgMonthlyBurn)}
              </p>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <DollarSign className="h-3 w-3" />
                <span>Final Cash</span>
              </div>
              <p className={cn(
                "text-xl font-semibold font-mono",
                summary.finalCash <= 0 ? "text-red-600 dark:text-red-400" : "text-emerald-600 dark:text-emerald-400"
              )} data-testid="text-final-cash">
                {formatCurrency(Math.max(0, summary.finalCash))}
              </p>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <TrendingDown className="h-3 w-3" />
                <span>Total Expenses</span>
              </div>
              <p className="text-xl font-semibold font-mono" data-testid="text-total-expenses">
                {formatCurrency(summary.totalExpenses)}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            Recommendations
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {getRecommendations().map((rec, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <CheckCircle className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <div className="flex items-center justify-between text-xs text-muted-foreground px-1" data-testid="simulation-footer-meta">
        <div className="flex items-center gap-4">
          {(result as any).seed !== undefined && (result as any).seed !== null && (
            <span className="font-mono">Seed: {(result as any).seed}</span>
          )}
          {((result as any).iterations || (result as any).n_sims) && (
            <span className="font-mono">Iterations: {(result as any).iterations || (result as any).n_sims}</span>
          )}
          {result.projections?.length > 0 && (
            <span className="font-mono">Horizon: {result.projections.length} months</span>
          )}
        </div>
        <span className="font-mono">Monte Carlo Simulation</span>
      </div>
    </div>
  );
}
