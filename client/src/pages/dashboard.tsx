import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { KPICard } from "@/components/kpi-card";
import { CashFlowChart } from "@/components/cash-flow-chart";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "wouter";
import {
  DollarSign,
  Flame,
  Calendar,
  TrendingUp,
  Plus,
  ArrowRight,
} from "lucide-react";
import type { SimulationResult, Scenario } from "@shared/schema";

export default function Dashboard() {
  const { data: scenarios, isLoading: scenariosLoading } = useQuery<Scenario[]>({
    queryKey: ["/api/scenarios"],
  });

  const { data: latestResult, isLoading: resultLoading } = useQuery<SimulationResult>({
    queryKey: ["/api/simulations/latest"],
  });

  const formatCurrency = (value: number) => {
    if (Math.abs(value) >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`;
    }
    if (Math.abs(value) >= 1000) {
      return `$${(value / 1000).toFixed(0)}K`;
    }
    return `$${value.toFixed(0)}`;
  };

  const getRunwayVariant = (months: number | null): "default" | "warning" | "danger" | "success" => {
    if (!months) return "success";
    if (months <= 6) return "danger";
    if (months <= 12) return "warning";
    return "default";
  };

  const isLoading = scenariosLoading || resultLoading;

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Monitor your startup's financial health
          </p>
        </div>
        <Button asChild data-testid="button-new-scenario">
          <Link href="/scenarios">
            <Plus className="h-4 w-4 mr-2" />
            New Scenario
          </Link>
        </Button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <Skeleton className="h-4 w-24 mb-2" />
                <Skeleton className="h-8 w-32" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : latestResult ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <KPICard
              title="Cash on Hand"
              value={formatCurrency(latestResult.summary.initialCash)}
              icon={<DollarSign className="h-4 w-4" />}
              testId="kpi-cash"
            />
            <KPICard
              title="Monthly Burn"
              value={formatCurrency(latestResult.summary.avgMonthlyBurn)}
              trend="down"
              trendLabel="Net cash outflow"
              icon={<Flame className="h-4 w-4" />}
              testId="kpi-burn"
            />
            <KPICard
              title="Runway"
              value={latestResult.summary.runwayMonths ? `${latestResult.summary.runwayMonths} months` : "Profitable"}
              subtitle={latestResult.summary.cashOutDate ? `Until ${latestResult.summary.cashOutDate}` : undefined}
              icon={<Calendar className="h-4 w-4" />}
              variant={getRunwayVariant(latestResult.summary.runwayMonths)}
              testId="kpi-runway"
            />
            <KPICard
              title="MRR"
              value={formatCurrency(latestResult.projections[0]?.revenue || 0)}
              trend="up"
              trendLabel="Monthly recurring revenue"
              icon={<TrendingUp className="h-4 w-4" />}
              testId="kpi-mrr"
            />
          </div>

          <CashFlowChart projections={latestResult.projections} />

          {scenarios && scenarios.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <CardTitle className="text-lg">Recent Scenarios</CardTitle>
                    <CardDescription>Compare different financial scenarios</CardDescription>
                  </div>
                  <Button variant="ghost" size="sm" asChild>
                    <Link href="/scenarios">
                      View all
                      <ArrowRight className="h-4 w-4 ml-1" />
                    </Link>
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {scenarios.slice(0, 3).map((scenario) => (
                    <div
                      key={scenario.id}
                      className="flex items-center justify-between p-3 rounded-md bg-muted/50"
                      data-testid={`scenario-item-${scenario.id}`}
                    >
                      <div>
                        <p className="font-medium text-sm">{scenario.name}</p>
                        {scenario.description && (
                          <p className="text-xs text-muted-foreground">{scenario.description}</p>
                        )}
                      </div>
                      <Button variant="ghost" size="sm" asChild>
                        <Link href={`/scenarios?id=${scenario.id}`}>
                          <ArrowRight className="h-4 w-4" />
                        </Link>
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      ) : (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <div className="p-4 rounded-full bg-muted mb-4">
              <FlaskConical className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="font-semibold text-lg mb-2">No simulations yet</h3>
            <p className="text-muted-foreground text-sm text-center max-w-md mb-4">
              Create your first scenario to see projected cash flow, runway, and financial metrics
            </p>
            <Button asChild data-testid="button-create-first-scenario">
              <Link href="/scenarios">
                <Plus className="h-4 w-4 mr-2" />
                Create Scenario
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function FlaskConical(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M10 2v7.31" />
      <path d="M14 9.3V2" />
      <path d="M8.5 2h7" />
      <path d="M14 9.3a6.5 6.5 0 1 1-4 0" />
      <path d="M5.52 16h12.96" />
    </svg>
  );
}
