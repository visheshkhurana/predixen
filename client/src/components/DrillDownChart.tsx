import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn, formatCurrencyAbbrev } from '@/lib/utils';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ReferenceLine,
  ReferenceArea,
  Brush,
} from 'recharts';
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Target,
  TrendingUp,
  DollarSign,
  Flame,
  Info,
  Settings2,
} from 'lucide-react';

type MetricType = 'cash' | 'revenue' | 'burn' | 'runway';

interface MonthlyData {
  month: number;
  cash_p10?: number;
  cash_p50: number;
  cash_p90?: number;
  revenue_p10?: number;
  revenue_p50: number;
  revenue_p90?: number;
  burn_p10?: number;
  burn_p50: number;
  burn_p90?: number;
  runway_p10?: number;
  runway_p50: number;
  runway_p90?: number;
  survival_rate?: number;
}

interface DrillDownChartProps {
  data: MonthlyData[];
  scenarioName: string;
  targetRunway?: number;
  minCash?: number;
  onBenchmarkChange?: (target: number) => void;
  testId?: string;
}

export function DrillDownChart({
  data,
  scenarioName,
  targetRunway = 18,
  minCash = 0,
  onBenchmarkChange,
  testId = 'drill-down-chart',
}: DrillDownChartProps) {
  const [metric, setMetric] = useState<MetricType>('cash');
  const [showBands, setShowBands] = useState(true);
  const [zoomDomain, setZoomDomain] = useState<{ start: number; end: number } | null>(null);
  const [localTargetRunway, setLocalTargetRunway] = useState(targetRunway);
  const [showBenchmark, setShowBenchmark] = useState(true);
  
  const metricConfig = {
    cash: {
      label: 'Cash Balance',
      icon: DollarSign,
      color: 'hsl(var(--primary))',
      format: (v: number) => formatCurrencyAbbrev(v),
      suffix: '',
    },
    revenue: {
      label: 'Monthly Revenue',
      icon: TrendingUp,
      color: 'hsl(142, 76%, 36%)',
      format: (v: number) => formatCurrencyAbbrev(v),
      suffix: '/mo',
    },
    burn: {
      label: 'Monthly Burn',
      icon: Flame,
      color: 'hsl(0, 84%, 60%)',
      format: (v: number) => formatCurrencyAbbrev(v),
      suffix: '/mo',
    },
    runway: {
      label: 'Runway Remaining',
      icon: Target,
      color: 'hsl(217, 91%, 60%)',
      format: (v: number) => `${v.toFixed(1)} mo`,
      suffix: '',
    },
  };
  
  const config = metricConfig[metric];
  
  const chartData = useMemo(() => {
    return data.map((d) => ({
      month: d.month,
      p10: d[`${metric}_p10` as keyof MonthlyData] as number | undefined,
      p50: d[`${metric}_p50` as keyof MonthlyData] as number,
      p90: d[`${metric}_p90` as keyof MonthlyData] as number | undefined,
      survival: d.survival_rate,
    }));
  }, [data, metric]);
  
  const benchmarkMonth = useMemo(() => {
    if (metric === 'runway') {
      return chartData.find(d => d.p50 <= 0)?.month;
    }
    if (metric === 'cash') {
      return chartData.find(d => d.p50 <= minCash)?.month;
    }
    return null;
  }, [chartData, metric, minCash]);
  
  const meetsBenchmark = useMemo(() => {
    if (!chartData || chartData.length === 0) return false;
    if (metric === 'runway') {
      const lastMonth = chartData[chartData.length - 1];
      return lastMonth && typeof lastMonth.p50 === 'number' && lastMonth.p50 >= localTargetRunway;
    }
    if (metric === 'cash') {
      return !benchmarkMonth || benchmarkMonth > localTargetRunway;
    }
    return true;
  }, [chartData, metric, localTargetRunway, benchmarkMonth]);
  
  const handleZoomIn = () => {
    const currentStart = zoomDomain?.start || 0;
    const currentEnd = zoomDomain?.end || chartData.length - 1;
    const range = currentEnd - currentStart;
    const newRange = Math.max(3, Math.floor(range / 2));
    const center = Math.floor((currentStart + currentEnd) / 2);
    setZoomDomain({
      start: Math.max(0, center - Math.floor(newRange / 2)),
      end: Math.min(chartData.length - 1, center + Math.ceil(newRange / 2)),
    });
  };
  
  const handleZoomOut = () => {
    if (!zoomDomain) return;
    const currentStart = zoomDomain.start;
    const currentEnd = zoomDomain.end;
    const range = currentEnd - currentStart;
    const newRange = Math.min(chartData.length - 1, range * 2);
    const center = Math.floor((currentStart + currentEnd) / 2);
    setZoomDomain({
      start: Math.max(0, center - Math.floor(newRange / 2)),
      end: Math.min(chartData.length - 1, center + Math.ceil(newRange / 2)),
    });
  };
  
  const handleReset = () => {
    setZoomDomain(null);
  };
  
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-popover border rounded-lg p-3 shadow-lg">
          <p className="font-semibold mb-2">Month {label}</p>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between gap-4">
              <span className="text-muted-foreground">P50 (Median):</span>
              <span className="font-mono font-medium">{config.format(data.p50)}</span>
            </div>
            {data.p10 !== undefined && (
              <div className="flex justify-between gap-4">
                <span className="text-muted-foreground">P10 (Pessimistic):</span>
                <span className="font-mono">{config.format(data.p10)}</span>
              </div>
            )}
            {data.p90 !== undefined && (
              <div className="flex justify-between gap-4">
                <span className="text-muted-foreground">P90 (Optimistic):</span>
                <span className="font-mono">{config.format(data.p90)}</span>
              </div>
            )}
            {data.survival !== undefined && (
              <div className="flex justify-between gap-4 pt-1 border-t">
                <span className="text-muted-foreground">Survival:</span>
                <span className="font-mono">{Math.round(data.survival * 100)}%</span>
              </div>
            )}
          </div>
        </div>
      );
    }
    return null;
  };
  
  return (
    <Card data-testid={testId}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <config.icon className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">{scenarioName}: {config.label}</CardTitle>
            {showBenchmark && (
              <Badge 
                variant={meetsBenchmark ? 'default' : 'destructive'}
                className="ml-2"
              >
                {meetsBenchmark ? 'Meets Target' : 'Below Target'}
              </Badge>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button 
                  variant={showBands ? 'default' : 'outline'} 
                  size="sm"
                  onClick={() => setShowBands(!showBands)}
                >
                  P10/P90
                </Button>
              </TooltipTrigger>
              <TooltipContent>Toggle confidence bands</TooltipContent>
            </Tooltip>
            
            <Button variant="outline" size="icon" onClick={handleZoomIn}>
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon" onClick={handleZoomOut}>
              <ZoomOut className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon" onClick={handleReset}>
              <RotateCcw className="h-4 w-4" />
            </Button>
          </div>
        </div>
        
        <Tabs value={metric} onValueChange={(v) => setMetric(v as MetricType)} className="mt-3">
          <TabsList>
            <TabsTrigger value="cash" data-testid="tab-metric-cash">
              <DollarSign className="h-4 w-4 mr-1" />
              Cash
            </TabsTrigger>
            <TabsTrigger value="revenue" data-testid="tab-metric-revenue">
              <TrendingUp className="h-4 w-4 mr-1" />
              Revenue
            </TabsTrigger>
            <TabsTrigger value="burn" data-testid="tab-metric-burn">
              <Flame className="h-4 w-4 mr-1" />
              Burn
            </TabsTrigger>
            <TabsTrigger value="runway" data-testid="tab-metric-runway">
              <Target className="h-4 w-4 mr-1" />
              Runway
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </CardHeader>
      
      <CardContent>
        <div className="h-[350px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart 
              data={zoomDomain 
                ? chartData.slice(zoomDomain.start, zoomDomain.end + 1) 
                : chartData
              }
              margin={{ top: 10, right: 30, left: 10, bottom: 40 }}
            >
              <defs>
                <linearGradient id="bandGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={config.color} stopOpacity={0.2} />
                  <stop offset="100%" stopColor={config.color} stopOpacity={0.05} />
                </linearGradient>
              </defs>
              
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              
              <XAxis 
                dataKey="month" 
                tickFormatter={(v) => `M${v}`}
                stroke="hsl(var(--muted-foreground))"
                tick={{ fontSize: 12 }}
              />
              <YAxis 
                tickFormatter={config.format}
                stroke="hsl(var(--muted-foreground))"
                tick={{ fontSize: 12 }}
                width={70}
              />
              
              <RechartsTooltip content={<CustomTooltip />} />
              
              {showBenchmark && metric === 'runway' && (
                <ReferenceLine 
                  y={localTargetRunway} 
                  stroke="hsl(var(--primary))" 
                  strokeDasharray="5 5"
                  label={{ 
                    value: `Target: ${localTargetRunway}mo`, 
                    position: 'insideTopRight',
                    fill: 'hsl(var(--primary))',
                    fontSize: 12,
                  }}
                />
              )}
              
              {showBenchmark && metric === 'cash' && minCash > 0 && (
                <ReferenceLine 
                  y={minCash} 
                  stroke="hsl(var(--destructive))" 
                  strokeDasharray="5 5"
                  label={{ 
                    value: `Min Cash: ${config.format(minCash)}`, 
                    position: 'insideTopRight',
                    fill: 'hsl(var(--destructive))',
                    fontSize: 12,
                  }}
                />
              )}
              
              {benchmarkMonth && showBenchmark && (
                <ReferenceArea
                  x1={benchmarkMonth}
                  x2={chartData.length}
                  fill="hsl(var(--destructive))"
                  fillOpacity={0.1}
                />
              )}
              
              {showBands && chartData[0]?.p10 !== undefined && (
                <Area
                  type="monotone"
                  dataKey="p90"
                  stroke="none"
                  fill="url(#bandGradient)"
                  name="P90"
                />
              )}
              
              {showBands && chartData[0]?.p10 !== undefined && (
                <Area
                  type="monotone"
                  dataKey="p10"
                  stroke="none"
                  fill="hsl(var(--background))"
                  name="P10"
                />
              )}
              
              <Line
                type="monotone"
                dataKey="p50"
                stroke={config.color}
                strokeWidth={2}
                dot={false}
                name="Median (P50)"
              />
              
              {!zoomDomain && (
                <Brush
                  dataKey="month"
                  height={30}
                  stroke="hsl(var(--primary))"
                  fill="hsl(var(--muted))"
                  tickFormatter={(v) => `M${v}`}
                />
              )}
              
              <Legend />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        
        {showBenchmark && metric === 'runway' && (
          <div className="mt-4 flex items-center gap-4 p-3 bg-muted/50 rounded-lg">
            <Settings2 className="h-4 w-4 text-muted-foreground shrink-0" />
            <div className="flex-1">
              <Label htmlFor="target-runway" className="text-sm">
                Target Runway (months)
              </Label>
              <div className="flex items-center gap-4 mt-1">
                <Slider
                  id="target-runway"
                  value={[localTargetRunway]}
                  onValueChange={([v]) => {
                    setLocalTargetRunway(v);
                    onBenchmarkChange?.(v);
                  }}
                  min={6}
                  max={36}
                  step={1}
                  className="flex-1"
                />
                <Input
                  type="number"
                  value={localTargetRunway}
                  onChange={(e) => {
                    const v = parseInt(e.target.value);
                    if (v >= 6 && v <= 36) {
                      setLocalTargetRunway(v);
                      onBenchmarkChange?.(v);
                    }
                  }}
                  className="w-20"
                />
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
