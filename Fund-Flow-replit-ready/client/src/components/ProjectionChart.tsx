import { useState, useMemo, useCallback } from 'react';
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Brush,
  ReferenceArea,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Settings2, TrendingUp, TrendingDown, Target, AlertTriangle, DollarSign } from 'lucide-react';

export interface MonthlyDataPoint {
  month: number;
  cashBalance: number;
  monthlyBurn: number;
  monthlyRevenue: number;
  runwayRemaining: number;
  headcount?: number;
}

export interface FundingEvent {
  month: number;
  amount: number;
  label?: string;
}

interface ProjectionChartProps {
  timeseries: MonthlyDataPoint[];
  fundingEvents?: FundingEvent[];
  scenarioName?: string;
  showHeadcount?: boolean;
  targetRunway?: number;
  targetRevenue?: number;
  onBenchmarkChange?: (benchmarks: { targetRunway?: number; targetRevenue?: number }) => void;
  testId?: string;
}

const formatCurrency = (value: number): string => {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(0)}K`;
  }
  return `$${value.toFixed(0)}`;
};

const formatMonthLabel = (month: number, startDate?: Date): string => {
  const date = startDate || new Date();
  const futureDate = new Date(date.getFullYear(), date.getMonth() + month, 1);
  const monthName = futureDate.toLocaleString('default', { month: 'short' });
  return `${monthName} ${futureDate.getFullYear()}`;
};

interface CustomTooltipProps {
  active?: boolean;
  payload?: any[];
  label?: string | number;
  visibleSeries: Record<string, boolean>;
}

const CustomTooltip = ({ active, payload, label, visibleSeries }: CustomTooltipProps) => {
  if (!active || !payload || !payload.length) return null;

  const monthNum = typeof label === 'number' ? label : parseInt(label as string);
  const monthLabel = formatMonthLabel(monthNum);

  return (
    <div 
      className="bg-popover border border-border rounded-lg p-3 shadow-lg"
      role="tooltip"
      aria-label={`Projection details for ${monthLabel}`}
    >
      <p className="font-semibold text-sm mb-2">Month {monthNum} - {monthLabel}</p>
      <div className="space-y-1 text-sm">
        {visibleSeries.cashBalance && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-blue-500" />
            <span className="text-muted-foreground">Cash Balance:</span>
            <span className="font-mono font-medium">
              {formatCurrency(payload.find(p => p.dataKey === 'cashBalance')?.value || 0)}
            </span>
          </div>
        )}
        {visibleSeries.monthlyRevenue && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-emerald-500" />
            <span className="text-muted-foreground">Monthly Revenue:</span>
            <span className="font-mono font-medium">
              {formatCurrency(payload.find(p => p.dataKey === 'monthlyRevenue')?.value || 0)}
            </span>
          </div>
        )}
        {visibleSeries.monthlyBurn && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-red-400" />
            <span className="text-muted-foreground">Monthly Burn:</span>
            <span className="font-mono font-medium">
              {formatCurrency(payload.find(p => p.dataKey === 'monthlyBurn')?.value || 0)}
            </span>
          </div>
        )}
        {visibleSeries.runwayRemaining && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-amber-500" />
            <span className="text-muted-foreground">Runway:</span>
            <span className="font-mono font-medium">
              {(payload.find(p => p.dataKey === 'runwayRemaining')?.value || 0).toFixed(1)} months
            </span>
          </div>
        )}
        {visibleSeries.headcount && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-purple-500" />
            <span className="text-muted-foreground">Headcount:</span>
            <span className="font-mono font-medium">
              {payload.find(p => p.dataKey === 'headcount')?.value || 0}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export function ProjectionChart({
  timeseries,
  fundingEvents = [],
  scenarioName = 'Projection',
  showHeadcount = false,
  targetRunway: initialTargetRunway = 18,
  targetRevenue: initialTargetRevenue,
  onBenchmarkChange,
  testId = 'projection-chart',
}: ProjectionChartProps) {
  const [visibleSeries, setVisibleSeries] = useState({
    cashBalance: true,
    monthlyBurn: true,
    monthlyRevenue: true,
    runwayRemaining: true,
    headcount: showHeadcount,
  });

  const [localTargetRunway, setLocalTargetRunway] = useState(initialTargetRunway);
  const [localTargetRevenue, setLocalTargetRevenue] = useState(initialTargetRevenue);
  const [showBenchmarks, setShowBenchmarks] = useState(true);

  const toggleSeries = useCallback((key: keyof typeof visibleSeries) => {
    setVisibleSeries(prev => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const milestones = useMemo(() => {
    const result: {
      breakEvenMonth: number | null;
      runwayExhaustionMonth: number | null;
      peakCash: { month: number; value: number };
      lowestCash: { month: number; value: number };
    } = {
      breakEvenMonth: null,
      runwayExhaustionMonth: null,
      peakCash: { month: 0, value: 0 },
      lowestCash: { month: 0, value: Infinity },
    };

    for (let i = 0; i < timeseries.length; i++) {
      const point = timeseries[i];
      
      if (result.breakEvenMonth === null && point.monthlyRevenue >= point.monthlyBurn) {
        result.breakEvenMonth = point.month;
      }
      
      if (result.runwayExhaustionMonth === null && point.cashBalance <= 0) {
        result.runwayExhaustionMonth = point.month;
      }
      
      if (point.cashBalance > result.peakCash.value) {
        result.peakCash = { month: point.month, value: point.cashBalance };
      }
      
      if (point.cashBalance < result.lowestCash.value && point.cashBalance > 0) {
        result.lowestCash = { month: point.month, value: point.cashBalance };
      }
    }

    if (result.lowestCash.value === Infinity) {
      result.lowestCash = { month: 0, value: 0 };
    }

    return result;
  }, [timeseries]);

  const averageBurn = useMemo(() => {
    if (!timeseries.length) return 0;
    return timeseries.reduce((sum, p) => sum + p.monthlyBurn, 0) / timeseries.length;
  }, [timeseries]);

  const targetCashLevel = useMemo(() => {
    return localTargetRunway * averageBurn;
  }, [localTargetRunway, averageBurn]);

  const handleBenchmarkUpdate = useCallback(() => {
    onBenchmarkChange?.({ targetRunway: localTargetRunway, targetRevenue: localTargetRevenue });
  }, [localTargetRunway, localTargetRevenue, onBenchmarkChange]);

  if (!timeseries || timeseries.length === 0) {
    return (
      <Card data-testid={testId}>
        <CardContent className="py-12 text-center">
          <p className="text-muted-foreground">No projection data available</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid={testId}>
      <CardHeader>
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <CardTitle className="text-lg">{scenarioName} - Month-by-Month Projections</CardTitle>
            <CardDescription>
              Interactive visualization of cash, burn, revenue, and runway over time
            </CardDescription>
          </div>
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" size="sm" data-testid="button-benchmark-settings">
                <Settings2 className="h-4 w-4 mr-2" />
                Benchmarks
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-72" align="end">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="target-runway">Target Runway (months)</Label>
                  <Input
                    id="target-runway"
                    type="number"
                    value={localTargetRunway}
                    onChange={(e) => setLocalTargetRunway(Number(e.target.value))}
                    min={1}
                    max={48}
                    data-testid="input-target-runway"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="target-revenue">Target Monthly Revenue ($)</Label>
                  <Input
                    id="target-revenue"
                    type="number"
                    value={localTargetRevenue || ''}
                    onChange={(e) => setLocalTargetRevenue(e.target.value ? Number(e.target.value) : undefined)}
                    placeholder="e.g., 500000"
                    data-testid="input-target-revenue"
                  />
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="show-benchmarks"
                    checked={showBenchmarks}
                    onCheckedChange={(checked) => setShowBenchmarks(checked as boolean)}
                    data-testid="checkbox-show-benchmarks"
                  />
                  <Label htmlFor="show-benchmarks">Show benchmark lines</Label>
                </div>
                <Button size="sm" onClick={handleBenchmarkUpdate} className="w-full" data-testid="button-apply-benchmarks">
                  Apply
                </Button>
              </div>
            </PopoverContent>
          </Popover>
        </div>

        <div className="flex flex-wrap gap-4 mt-4" role="group" aria-label="Toggle chart series">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="toggle-cash"
              checked={visibleSeries.cashBalance}
              onCheckedChange={() => toggleSeries('cashBalance')}
              data-testid="checkbox-toggle-cash"
            />
            <Label htmlFor="toggle-cash" className="flex items-center gap-1 cursor-pointer">
              <div className="w-3 h-3 rounded-full bg-blue-500" />
              Cash Balance
            </Label>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="toggle-revenue"
              checked={visibleSeries.monthlyRevenue}
              onCheckedChange={() => toggleSeries('monthlyRevenue')}
              data-testid="checkbox-toggle-revenue"
            />
            <Label htmlFor="toggle-revenue" className="flex items-center gap-1 cursor-pointer">
              <div className="w-3 h-3 rounded-full bg-emerald-500" />
              Revenue
            </Label>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="toggle-burn"
              checked={visibleSeries.monthlyBurn}
              onCheckedChange={() => toggleSeries('monthlyBurn')}
              data-testid="checkbox-toggle-burn"
            />
            <Label htmlFor="toggle-burn" className="flex items-center gap-1 cursor-pointer">
              <div className="w-3 h-3 rounded-full bg-red-400" />
              Burn
            </Label>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="toggle-runway"
              checked={visibleSeries.runwayRemaining}
              onCheckedChange={() => toggleSeries('runwayRemaining')}
              data-testid="checkbox-toggle-runway"
            />
            <Label htmlFor="toggle-runway" className="flex items-center gap-1 cursor-pointer">
              <div className="w-3 h-3 rounded-full bg-amber-500" />
              Runway
            </Label>
          </div>
          {showHeadcount && (
            <div className="flex items-center space-x-2">
              <Checkbox
                id="toggle-headcount"
                checked={visibleSeries.headcount}
                onCheckedChange={() => toggleSeries('headcount')}
                data-testid="checkbox-toggle-headcount"
              />
              <Label htmlFor="toggle-headcount" className="flex items-center gap-1 cursor-pointer">
                <div className="w-3 h-3 rounded-full bg-purple-500" />
                Headcount
              </Label>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[400px]" role="img" aria-label="Projection chart showing financial metrics over time">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={timeseries}
              margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="month"
                tickFormatter={(m) => `M${m}`}
                tick={{ fontSize: 12 }}
                className="text-muted-foreground"
              />
              <YAxis
                yAxisId="left"
                tickFormatter={formatCurrency}
                tick={{ fontSize: 12 }}
                className="text-muted-foreground"
                label={{ value: 'Amount ($)', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle' } }}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fontSize: 12 }}
                className="text-muted-foreground"
                label={{ value: 'Months / Count', angle: 90, position: 'insideRight', style: { textAnchor: 'middle' } }}
              />
              <Tooltip content={<CustomTooltip visibleSeries={visibleSeries} />} />
              
              {showBenchmarks && targetCashLevel > 0 && (
                <ReferenceLine
                  yAxisId="left"
                  y={targetCashLevel}
                  stroke="hsl(var(--primary))"
                  strokeDasharray="5 5"
                  strokeWidth={2}
                  label={{
                    value: `Target Runway Cash: ${formatCurrency(targetCashLevel)}`,
                    position: 'top',
                    fill: 'hsl(var(--primary))',
                    fontSize: 11,
                  }}
                />
              )}
              
              {showBenchmarks && localTargetRevenue && (
                <ReferenceLine
                  yAxisId="left"
                  y={localTargetRevenue}
                  stroke="hsl(var(--chart-2))"
                  strokeDasharray="5 5"
                  strokeWidth={2}
                  label={{
                    value: `Target Revenue: ${formatCurrency(localTargetRevenue)}`,
                    position: 'top',
                    fill: 'hsl(var(--chart-2))',
                    fontSize: 11,
                  }}
                />
              )}

              {fundingEvents.map((event, idx) => (
                <ReferenceLine
                  key={`funding-${idx}`}
                  x={event.month}
                  yAxisId="left"
                  stroke="hsl(var(--chart-3))"
                  strokeWidth={2}
                  label={{
                    value: event.label || `+${formatCurrency(event.amount)}`,
                    position: 'top',
                    fill: 'hsl(var(--chart-3))',
                    fontSize: 11,
                  }}
                />
              ))}

              {milestones.breakEvenMonth !== null && (
                <ReferenceLine
                  x={milestones.breakEvenMonth}
                  yAxisId="left"
                  stroke="hsl(var(--chart-2))"
                  strokeWidth={2}
                  label={{
                    value: `Break-even M${milestones.breakEvenMonth}`,
                    position: 'insideTopRight',
                    fill: 'hsl(var(--chart-2))',
                    fontSize: 11,
                  }}
                />
              )}

              {milestones.runwayExhaustionMonth !== null && (
                <ReferenceArea
                  x1={milestones.runwayExhaustionMonth}
                  x2={timeseries[timeseries.length - 1]?.month}
                  yAxisId="left"
                  fill="hsl(var(--destructive))"
                  fillOpacity={0.1}
                  label={{
                    value: `Cash depleted M${milestones.runwayExhaustionMonth}`,
                    position: 'insideTop',
                    fill: 'hsl(var(--destructive))',
                    fontSize: 11,
                  }}
                />
              )}

              {visibleSeries.cashBalance && (
                <Area
                  yAxisId="left"
                  type="monotone"
                  dataKey="cashBalance"
                  stroke="#3b82f6"
                  fill="#3b82f6"
                  fillOpacity={0.1}
                  strokeWidth={2}
                  name="Cash Balance"
                  dot={false}
                  activeDot={{ r: 5 }}
                />
              )}
              
              {visibleSeries.monthlyRevenue && (
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="monthlyRevenue"
                  stroke="#10b981"
                  strokeWidth={2}
                  name="Monthly Revenue"
                  dot={false}
                  activeDot={{ r: 5 }}
                />
              )}
              
              {visibleSeries.monthlyBurn && (
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="monthlyBurn"
                  stroke="#f87171"
                  strokeWidth={2}
                  name="Monthly Burn"
                  dot={false}
                  activeDot={{ r: 5 }}
                />
              )}
              
              {visibleSeries.runwayRemaining && (
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="runwayRemaining"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  strokeDasharray="4 2"
                  name="Runway"
                  dot={false}
                  activeDot={{ r: 5 }}
                />
              )}
              
              {visibleSeries.headcount && showHeadcount && (
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="headcount"
                  stroke="#a855f7"
                  strokeWidth={2}
                  name="Headcount"
                  dot={false}
                  activeDot={{ r: 5 }}
                />
              )}
              
              <Brush
                dataKey="month"
                height={30}
                stroke="hsl(var(--primary))"
                tickFormatter={(m) => `M${m}`}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        <div className="flex flex-wrap gap-2 mt-4">
          {fundingEvents.length > 0 && (
            <Badge variant="outline" className="gap-1">
              <DollarSign className="h-3 w-3" />
              {fundingEvents.length} Funding Event{fundingEvents.length > 1 ? 's' : ''}
            </Badge>
          )}
          {milestones.breakEvenMonth !== null && (
            <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 gap-1">
              <TrendingUp className="h-3 w-3" />
              Break-even Month {milestones.breakEvenMonth}
            </Badge>
          )}
          {milestones.runwayExhaustionMonth !== null && (
            <Badge variant="destructive" className="gap-1">
              <AlertTriangle className="h-3 w-3" />
              Cash Depleted Month {milestones.runwayExhaustionMonth}
            </Badge>
          )}
          {milestones.runwayExhaustionMonth === null && milestones.breakEvenMonth === null && (
            <Badge className="bg-blue-500/10 text-blue-600 border-blue-500/20 gap-1">
              <Target className="h-3 w-3" />
              Runway Extends Full Horizon
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
