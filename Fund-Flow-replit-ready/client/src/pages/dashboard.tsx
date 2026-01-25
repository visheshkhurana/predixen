import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { EnhancedKPICard } from "@/components/enhanced-kpi-card";
import { CashFlowChart } from "@/components/cash-flow-chart";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Link } from "wouter";
import { useFounderStore } from "@/store/founderStore";
import {
  DollarSign,
  Flame,
  Calendar,
  TrendingUp,
  Plus,
  ArrowRight,
  Info,
  Percent,
  Target,
  AlertCircle,
  Lightbulb,
  BarChart3,
  AlertTriangle,
  ExternalLink,
} from "lucide-react";
import type { SimulationResult, Scenario, DashboardKPIs } from "@shared/schema";

type TimePeriod = "last_month" | "this_quarter" | "last_quarter" | "this_year" | "last_12_months";

const periodLabels: Record<TimePeriod, string> = {
  last_month: "Last Month",
  this_quarter: "This Quarter",
  last_quarter: "Last Quarter",
  this_year: "This Year",
  last_12_months: "Last 12 Months",
};

export default function Dashboard() {
  const { currentCompany: selectedCompany } = useFounderStore();
  const [selectedPeriod, setSelectedPeriod] = useState<TimePeriod>("last_12_months");
  
  const { data: scenarios, isLoading: scenariosLoading } = useQuery<Scenario[]>({
    queryKey: ["/api/scenarios"],
  });

  const { data: latestResult, isLoading: resultLoading } = useQuery<SimulationResult>({
    queryKey: ["/api/simulations/latest"],
  });

  const { data: kpis, isLoading: kpisLoading } = useQuery<DashboardKPIs>({
    queryKey: ["/api/dashboard/companies", selectedCompany?.id, "kpis", selectedPeriod],
    queryFn: async () => {
      const res = await fetch(`/api/dashboard/companies/${selectedCompany?.id}/kpis?period=${selectedPeriod}`);
      if (!res.ok) throw new Error("Failed to fetch KPIs");
      return res.json();
    },
    enabled: !!selectedCompany?.id,
  });

  const isLoading = scenariosLoading || resultLoading || kpisLoading;

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case "high":
        return <Badge variant="destructive" className="text-xs">High Priority</Badge>;
      case "medium":
        return <Badge variant="secondary" className="bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400 text-xs">Medium</Badge>;
      default:
        return <Badge variant="secondary" className="text-xs">Low</Badge>;
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Monitor your startup's financial health
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select
            value={selectedPeriod}
            onValueChange={(value) => setSelectedPeriod(value as TimePeriod)}
          >
            <SelectTrigger className="w-[160px]" data-testid="select-period">
              <SelectValue placeholder="Select period" />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(periodLabels).map(([value, label]) => (
                <SelectItem key={value} value={value} data-testid={`select-period-${value}`}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          {kpis && (
            <Tooltip>
              <TooltipTrigger asChild>
                <div 
                  className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-muted cursor-help"
                  data-testid="indicator-data-confidence"
                >
                  <Info className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium" data-testid="text-data-confidence-value">
                    Data Confidence: {kpis.dataConfidence}%
                  </span>
                </div>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <p>Data confidence score reflects the completeness and accuracy of your financial inputs. Upload more data to improve this score.</p>
              </TooltipContent>
            </Tooltip>
          )}
          <Button asChild data-testid="button-new-scenario">
            <Link href="/scenarios">
              <Plus className="h-4 w-4 mr-2" />
              New Scenario
            </Link>
          </Button>
        </div>
      </div>

      {kpis?.missingData && kpis.missingData.length > 0 && (
        <Alert variant="destructive" className="border-amber-500/50 bg-amber-50 dark:bg-amber-900/20" data-testid="alert-missing-data">
          <AlertTriangle className="h-4 w-4 text-amber-600" />
          <AlertTitle className="text-amber-800 dark:text-amber-400">Data Missing</AlertTitle>
          <AlertDescription className="text-amber-700 dark:text-amber-300">
            <ul className="mt-2 space-y-1">
              {kpis.missingData.map((item: { field: string; message: string }, idx: number) => (
                <li key={idx} className="flex items-center gap-2">
                  <span>{item.message}</span>
                </li>
              ))}
            </ul>
            <Button asChild variant="outline" size="sm" className="mt-3" data-testid="button-fix-data">
              <Link href="/ingest">
                <ExternalLink className="h-3 w-3 mr-1" />
                Fix Now
              </Link>
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {isLoading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Card className="lg:col-span-1 lg:row-span-2">
              <CardContent className="p-6">
                <Skeleton className="h-4 w-24 mb-2" />
                <Skeleton className="h-12 w-32 mb-4" />
                <Skeleton className="h-16 w-full" />
              </CardContent>
            </Card>
            {[...Array(4)].map((_, i) => (
              <Card key={i}>
                <CardContent className="p-4">
                  <Skeleton className="h-4 w-24 mb-2" />
                  <Skeleton className="h-8 w-32" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ) : kpis ? (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-1 lg:row-span-2">
              <EnhancedKPICard
                data={kpis.runway}
                title="Runway (P50)"
                format="months"
                icon={<Calendar className="h-5 w-5" />}
                highlighted={true}
                testId="kpi-runway"
              />
            </div>
            
            <EnhancedKPICard
              data={kpis.cashOnHand}
              title="Cash on Hand"
              format="currency"
              icon={<DollarSign className="h-4 w-4" />}
              testId="kpi-cash"
            />
            
            <EnhancedKPICard
              data={kpis.netBurn}
              title="Net Burn"
              format="currency"
              icon={<Flame className="h-4 w-4" />}
              testId="kpi-burn"
            />
            
            <EnhancedKPICard
              data={kpis.mrr}
              title="MRR"
              format="currency"
              icon={<TrendingUp className="h-4 w-4" />}
              testId="kpi-mrr"
            />
            
            <EnhancedKPICard
              data={kpis.grossMargin}
              title="Gross Margin"
              format="percent"
              icon={<Percent className="h-4 w-4" />}
              testId="kpi-margin"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <EnhancedKPICard
              data={kpis.revenueGrowth}
              title="Revenue Growth (YoY)"
              format="percent"
              icon={<BarChart3 className="h-4 w-4" />}
              testId="kpi-growth"
            />
            
            <EnhancedKPICard
              data={kpis.burnMultiple}
              title="Burn Multiple"
              format="multiple"
              icon={<Target className="h-4 w-4" />}
              testId="kpi-burn-multiple"
            />
            
            <Card className="overflow-visible" data-testid="kpi-quality-of-growth">
              <CardContent className="p-4">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-muted-foreground">Quality of Growth</span>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span 
                        className="text-muted-foreground cursor-help"
                        data-testid="tooltip-trigger-qog"
                      >
                        <Info className="h-3 w-3" />
                      </span>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Composite score based on growth efficiency, unit economics, and capital efficiency</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
                <div className="mt-2">
                  <span className="text-2xl font-semibold font-mono tracking-tight" data-testid="text-qog-value">
                    {kpis.qualityOfGrowthIndex !== null ? kpis.qualityOfGrowthIndex : "N/A"}
                  </span>
                  <span className="text-sm text-muted-foreground ml-1">/100</span>
                </div>
                <p className="text-xs text-muted-foreground mt-2" data-testid="text-top-concentration">
                  Top 5 concentration: {kpis.topConcentration !== null ? `${kpis.topConcentration}%` : "N/A"}
                </p>
              </CardContent>
            </Card>
          </div>

          {kpis.recommendations && kpis.recommendations.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <Lightbulb className="h-5 w-5 text-primary" />
                  <CardTitle className="text-lg">Top Recommendations</CardTitle>
                </div>
                <CardDescription>Context-aware suggestions based on your metrics</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {kpis.recommendations.map((rec) => (
                    <div
                      key={rec.id}
                      className="flex items-start justify-between gap-4 p-4 rounded-lg bg-muted/50"
                      data-testid={`recommendation-${rec.id}`}
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <h4 className="font-medium text-sm" data-testid={`text-recommendation-title-${rec.id}`}>
                            {rec.title}
                          </h4>
                          {getPriorityBadge(rec.priority)}
                        </div>
                        <p className="text-sm text-muted-foreground" data-testid={`text-recommendation-desc-${rec.id}`}>
                          {rec.description}
                        </p>
                      </div>
                      {rec.action && (
                        <Button 
                          variant="outline" 
                          size="sm" 
                          asChild
                          data-testid={`button-recommendation-action-${rec.id}`}
                        >
                          <Link href="/scenarios">
                            {rec.action}
                            <ArrowRight className="h-3 w-3 ml-1" />
                          </Link>
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {latestResult && <CashFlowChart projections={latestResult.projections} />}

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
      ) : latestResult ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4">
                <span className="text-sm font-medium text-muted-foreground">Cash on Hand</span>
                <div className="mt-2">
                  <span className="text-2xl font-semibold font-mono">
                    ${(latestResult.summary.initialCash / 1000000).toFixed(1)}M
                  </span>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <span className="text-sm font-medium text-muted-foreground">Monthly Burn</span>
                <div className="mt-2">
                  <span className="text-2xl font-semibold font-mono">
                    ${(latestResult.summary.avgMonthlyBurn / 1000).toFixed(0)}K
                  </span>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <span className="text-sm font-medium text-muted-foreground">Runway</span>
                <div className="mt-2">
                  <span className="text-2xl font-semibold font-mono">
                    {latestResult.summary.runwayMonths ? `${latestResult.summary.runwayMonths} mo` : "Profitable"}
                  </span>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <span className="text-sm font-medium text-muted-foreground">MRR</span>
                <div className="mt-2">
                  <span className="text-2xl font-semibold font-mono">
                    ${((latestResult.projections[0]?.revenue || 0) / 1000).toFixed(0)}K
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>

          <CashFlowChart projections={latestResult.projections} />
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
