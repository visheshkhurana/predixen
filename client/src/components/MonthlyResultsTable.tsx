import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn, formatCurrencyAbbrev } from '@/lib/utils';

interface MonthData {
  month: number;
  revenue_p10: number;
  revenue_p50: number;
  revenue_p90: number;
  cash_p10: number;
  cash_p50: number;
  cash_p90: number;
  burn_p10: number;
  burn_p50: number;
  burn_p90: number;
  survival_rate: number;
}

interface ScenarioResult {
  name: string;
  description: string;
  summary: {
    runway_p10: number;
    runway_p50: number;
    runway_p90: number;
    survival_12m: number;
    survival_18m: number;
    survival_24m: number;
    final_cash_p50: number;
  };
  month_data: MonthData[];
}

interface MonthlyResultsTableProps {
  scenarios: Record<string, ScenarioResult>;
  selectedScenarios?: string[];
  testId?: string;
}

type PercentileView = 'p10' | 'p50' | 'p90';
type MetricView = 'revenue' | 'cash' | 'burn' | 'survival';

export function MonthlyResultsTable({
  scenarios,
  selectedScenarios,
  testId = 'monthly-results-table'
}: MonthlyResultsTableProps) {
  const [percentileView, setPercentileView] = useState<PercentileView>('p50');
  const [metricView, setMetricView] = useState<MetricView>('cash');
  const [activeScenario, setActiveScenario] = useState<string>(
    selectedScenarios?.[0] || Object.keys(scenarios)[0] || ''
  );

  const scenarioKeys = selectedScenarios || Object.keys(scenarios);
  const currentScenario = scenarios[activeScenario];

  if (!currentScenario) {
    return (
      <Card data-testid={testId}>
        <CardContent className="p-6 text-center text-muted-foreground">
          No simulation data available
        </CardContent>
      </Card>
    );
  }

  const formatCurrency = (value: number) => formatCurrencyAbbrev(value);

  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(0)}%`;
  };

  const getMetricValue = (monthData: MonthData, metric: MetricView, percentile: PercentileView): number => {
    if (metric === 'survival') {
      return monthData.survival_rate;
    }
    const key = `${metric}_${percentile}` as keyof MonthData;
    return monthData[key] as number;
  };

  const getTrendIcon = (current: number, previous: number) => {
    const delta = current - previous;
    if (Math.abs(delta) < current * 0.01) {
      return <Minus className="h-3 w-3 text-muted-foreground" />;
    }
    if (delta > 0) {
      return <TrendingUp className="h-3 w-3 text-emerald-500" />;
    }
    return <TrendingDown className="h-3 w-3 text-red-500" />;
  };

  const getValueColor = (metric: MetricView, value: number) => {
    if (metric === 'cash') {
      if (value <= 0) return 'text-red-600 dark:text-red-400';
      if (value < 100000) return 'text-amber-600 dark:text-amber-400';
      return '';
    }
    if (metric === 'survival') {
      if (value < 0.5) return 'text-red-600 dark:text-red-400';
      if (value < 0.75) return 'text-amber-600 dark:text-amber-400';
      return 'text-emerald-600 dark:text-emerald-400';
    }
    return '';
  };

  const metricLabels: Record<MetricView, string> = {
    revenue: 'Revenue',
    cash: 'Cash Balance',
    burn: 'Monthly Burn',
    survival: 'Survival Rate'
  };

  return (
    <Card data-testid={testId}>
      <CardHeader className="pb-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <CardTitle className="text-lg">Month-by-Month Projections</CardTitle>
            <CardDescription>
              Detailed monthly breakdown with P10/P50/P90 confidence intervals
            </CardDescription>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Select value={metricView} onValueChange={(v) => setMetricView(v as MetricView)}>
              <SelectTrigger className="w-[140px]" data-testid="select-metric">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="cash">Cash Balance</SelectItem>
                <SelectItem value="revenue">Revenue</SelectItem>
                <SelectItem value="burn">Monthly Burn</SelectItem>
                <SelectItem value="survival">Survival Rate</SelectItem>
              </SelectContent>
            </Select>
            {metricView !== 'survival' && (
              <Select value={percentileView} onValueChange={(v) => setPercentileView(v as PercentileView)}>
                <SelectTrigger className="w-[120px]" data-testid="select-percentile">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="p10">P10 (Bear)</SelectItem>
                  <SelectItem value="p50">P50 (Base)</SelectItem>
                  <SelectItem value="p90">P90 (Bull)</SelectItem>
                </SelectContent>
              </Select>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs value={activeScenario} onValueChange={setActiveScenario}>
          <TabsList className="mb-4 flex-wrap h-auto gap-1">
            {scenarioKeys.map((key) => (
              <TabsTrigger
                key={key}
                value={key}
                className="text-xs sm:text-sm"
                data-testid={`tab-scenario-${key}`}
              >
                {scenarios[key]?.name || key}
              </TabsTrigger>
            ))}
          </TabsList>

          {scenarioKeys.map((key) => {
            const scenario = scenarios[key];
            if (!scenario) return null;

            return (
              <TabsContent key={key} value={key} className="mt-0">
                <div className="mb-4 flex items-center gap-4 flex-wrap">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">Runway:</span>
                    <Badge variant="outline" className="font-mono">
                      {scenario.summary.runway_p50 >= 900 ? 'Sustainable' : `${scenario.summary.runway_p50.toFixed(1)} months`}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">18m Survival:</span>
                    <Badge 
                      variant="outline" 
                      className={cn(
                        "font-mono",
                        scenario.summary.survival_18m < 50 && "border-red-500 text-red-600",
                        scenario.summary.survival_18m >= 50 && scenario.summary.survival_18m < 75 && "border-amber-500 text-amber-600",
                        scenario.summary.survival_18m >= 75 && "border-emerald-500 text-emerald-600"
                      )}
                    >
                      {scenario.summary.survival_18m.toFixed(0)}%
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">End Cash:</span>
                    <Badge 
                      variant="outline" 
                      className={cn(
                        "font-mono",
                        scenario.summary.final_cash_p50 <= 0 && "border-red-500 text-red-600"
                      )}
                    >
                      {formatCurrency(scenario.summary.final_cash_p50)}
                    </Badge>
                  </div>
                </div>

                <div className="overflow-x-auto rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[80px]">Month</TableHead>
                        <TableHead className="text-right">{metricLabels[metricView]}</TableHead>
                        <TableHead className="w-[60px] text-center">Trend</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {scenario.month_data.map((monthData, idx) => {
                        const value = getMetricValue(monthData, metricView, percentileView);
                        const prevValue = idx > 0 
                          ? getMetricValue(scenario.month_data[idx - 1], metricView, percentileView)
                          : value;

                        return (
                          <TableRow 
                            key={monthData.month}
                            data-testid={`row-month-${monthData.month}`}
                          >
                            <TableCell className="font-medium">M{monthData.month}</TableCell>
                            <TableCell className={cn(
                              "text-right font-mono",
                              getValueColor(metricView, value)
                            )}>
                              {metricView === 'survival' 
                                ? formatPercent(value) 
                                : formatCurrency(value)}
                            </TableCell>
                            <TableCell className="text-center">
                              {idx > 0 && getTrendIcon(value, prevValue)}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              </TabsContent>
            );
          })}
        </Tabs>
      </CardContent>
    </Card>
  );
}
