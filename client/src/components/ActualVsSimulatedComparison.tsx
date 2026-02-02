import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Check,
  AlertTriangle,
  AlertCircle,
} from 'lucide-react';

interface MetricData {
  month: string;
  actual?: number;
  simulated?: number;
}

interface ActualVsSimulatedComparisonProps {
  metricName: string;
  metricLabel: string;
  data: MetricData[];
  formatValue?: (value: number) => string;
  thresholdPct?: number;
}

function formatCurrency(value: number): string {
  if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function getVarianceStatus(actual: number, simulated: number, thresholdPct: number = 10) {
  if (simulated === 0) return { status: 'neutral', variance: 0, label: 'N/A' };
  
  const variance = ((actual - simulated) / simulated) * 100;
  const absVariance = Math.abs(variance);
  
  if (absVariance <= thresholdPct) {
    return { status: 'good', variance, label: 'On Track' };
  } else if (absVariance <= thresholdPct * 2) {
    return { status: 'warning', variance, label: 'Minor Variance' };
  } else {
    return { status: 'critical', variance, label: 'Significant Variance' };
  }
}

export function ActualVsSimulatedComparison({
  metricName,
  metricLabel,
  data,
  formatValue = formatCurrency,
  thresholdPct = 10,
}: ActualVsSimulatedComparisonProps) {
  const comparisonData = useMemo(() => {
    return data.map((item) => {
      if (item.actual === undefined || item.simulated === undefined) {
        return { ...item, variance: null, status: 'pending' };
      }
      const { status, variance } = getVarianceStatus(item.actual, item.simulated, thresholdPct);
      return { ...item, variance, status };
    });
  }, [data, thresholdPct]);

  const overallAccuracy = useMemo(() => {
    const validPoints = comparisonData.filter(
      (d) => d.actual !== undefined && d.simulated !== undefined
    );
    if (validPoints.length === 0) return null;

    const totalVariance = validPoints.reduce((sum, d) => {
      const variance = Math.abs(((d.actual! - d.simulated!) / d.simulated!) * 100);
      return sum + (isNaN(variance) ? 0 : variance);
    }, 0);

    return 100 - totalVariance / validPoints.length;
  }, [comparisonData]);

  const latestPoint = comparisonData[comparisonData.length - 1];
  const latestStatus = latestPoint?.status || 'pending';

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <div>
            <CardTitle className="text-lg">{metricLabel}: Actual vs Simulated</CardTitle>
            <CardDescription>
              Compare actual performance against simulation predictions
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {overallAccuracy !== null && (
              <Badge variant={overallAccuracy >= 90 ? 'default' : overallAccuracy >= 75 ? 'secondary' : 'destructive'}>
                {overallAccuracy.toFixed(0)}% Accuracy
              </Badge>
            )}
            {latestStatus === 'good' && (
              <Badge variant="default" className="gap-1">
                <Check className="h-3 w-3" />
                On Track
              </Badge>
            )}
            {latestStatus === 'warning' && (
              <Badge variant="secondary" className="gap-1">
                <AlertTriangle className="h-3 w-3" />
                Minor Variance
              </Badge>
            )}
            {latestStatus === 'critical' && (
              <Badge variant="destructive" className="gap-1">
                <AlertCircle className="h-3 w-3" />
                Significant Variance
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={comparisonData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="month" tick={{ fontSize: 12 }} />
            <YAxis tickFormatter={(v) => formatValue(v)} tick={{ fontSize: 12 }} />
            <Tooltip formatter={(value: number) => formatValue(value)} />
            <Legend />
            <Line
              type="monotone"
              dataKey="actual"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              name="Actual"
              dot={{ r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="simulated"
              stroke="hsl(var(--muted-foreground))"
              strokeWidth={2}
              strokeDasharray="5 5"
              name="Simulated"
              dot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Period</TableHead>
              <TableHead className="text-right">Actual</TableHead>
              <TableHead className="text-right">Simulated</TableHead>
              <TableHead className="text-right">Variance</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {comparisonData.slice(-6).map((row, idx) => (
              <TableRow key={idx} data-testid={`comparison-row-${idx}`}>
                <TableCell className="font-medium">{row.month}</TableCell>
                <TableCell className="text-right">
                  {row.actual !== undefined ? formatValue(row.actual) : '—'}
                </TableCell>
                <TableCell className="text-right">
                  {row.simulated !== undefined ? formatValue(row.simulated) : '—'}
                </TableCell>
                <TableCell className="text-right">
                  {row.variance !== null ? (
                    <span className={row.variance >= 0 ? 'text-green-600' : 'text-red-600'}>
                      {row.variance >= 0 ? '+' : ''}
                      {row.variance.toFixed(1)}%
                    </span>
                  ) : (
                    '—'
                  )}
                </TableCell>
                <TableCell>
                  {row.status === 'good' && (
                    <Badge variant="default" className="gap-1">
                      <Check className="h-3 w-3" />
                    </Badge>
                  )}
                  {row.status === 'warning' && (
                    <Badge variant="secondary" className="gap-1">
                      <AlertTriangle className="h-3 w-3" />
                    </Badge>
                  )}
                  {row.status === 'critical' && (
                    <Badge variant="destructive" className="gap-1">
                      <AlertCircle className="h-3 w-3" />
                    </Badge>
                  )}
                  {row.status === 'pending' && (
                    <Badge variant="outline">Pending</Badge>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

interface MultiMetricComparisonProps {
  metrics: Array<{
    id: string;
    label: string;
    data: MetricData[];
    formatValue?: (value: number) => string;
  }>;
}

export function MultiMetricComparison({ metrics }: MultiMetricComparisonProps) {
  const summaryData = useMemo(() => {
    return metrics.map((metric) => {
      const validPoints = metric.data.filter(
        (d) => d.actual !== undefined && d.simulated !== undefined
      );

      if (validPoints.length === 0) {
        return { ...metric, accuracy: null, trend: 'neutral' as const };
      }

      const latest = validPoints[validPoints.length - 1];
      const variance = ((latest.actual! - latest.simulated!) / latest.simulated!) * 100;
      const accuracy = 100 - Math.abs(variance);

      let trend: 'up' | 'down' | 'neutral' = 'neutral';
      if (variance > 5) trend = 'up';
      else if (variance < -5) trend = 'down';

      return { ...metric, accuracy, trend, variance };
    });
  }, [metrics]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Performance vs Predictions</CardTitle>
        <CardDescription>
          Summary of actual performance compared to simulated forecasts
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {summaryData.map((metric) => (
            <Card key={metric.id} className="p-4">
              <div className="flex items-center justify-between gap-2 mb-2">
                <span className="text-sm font-medium text-muted-foreground">{metric.label}</span>
                {metric.trend === 'up' && <TrendingUp className="h-4 w-4 text-green-500" />}
                {metric.trend === 'down' && <TrendingDown className="h-4 w-4 text-red-500" />}
                {metric.trend === 'neutral' && <Minus className="h-4 w-4 text-muted-foreground" />}
              </div>
              {metric.accuracy !== null ? (
                <>
                  <div className="text-2xl font-bold">{metric.accuracy.toFixed(0)}%</div>
                  <div className="text-xs text-muted-foreground">
                    {metric.variance && metric.variance >= 0 ? '+' : ''}
                    {metric.variance?.toFixed(1)}% variance
                  </div>
                </>
              ) : (
                <div className="text-sm text-muted-foreground">No data</div>
              )}
            </Card>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
