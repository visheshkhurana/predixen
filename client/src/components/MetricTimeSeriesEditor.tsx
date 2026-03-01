import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { useQuery } from '@tanstack/react-query';
import { useFounderStore } from '@/store/founderStore';
import { useToast } from '@/hooks/use-toast';
import { useCurrency } from '@/hooks/useCurrency';
import { queryClient, apiRequest } from '@/lib/queryClient';
import { cn } from '@/lib/utils';
import { Save, Loader2, Calendar, TrendingUp } from 'lucide-react';

interface MetricDef {
  id: number;
  key: string;
  name: string;
  unit: string | null;
  format_type: string;
  grain: string;
  latest_value: number | null;
  tags: string[] | null;
}

interface MetricTimeSeriesValue {
  period_start: string;
  value: number;
}

export function MetricTimeSeriesEditor() {
  const { currentCompany } = useFounderStore();
  const { toast } = useToast();
  const { format } = useCurrency();
  const companyId = currentCompany?.id;

  const [editingValues, setEditingValues] = useState<Record<string, Record<string, number>>>({});
  const [isSaving, setIsSaving] = useState(false);

  const months = useMemo(() => {
    const result: string[] = [];
    const now = new Date();
    for (let i = 5; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      result.push(d.toISOString().slice(0, 10));
    }
    return result;
  }, []);

  const formatMonth = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
  };

  const { data: metrics, isLoading: metricsLoading } = useQuery<MetricDef[]>({
    queryKey: ['/api/metrics', companyId],
    queryFn: async () => {
      const res = await fetch(`/api/metrics?company_id=${companyId}`, {
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Failed to fetch metrics');
      return res.json();
    },
    enabled: !!companyId,
  });

  const formatValue = (value: number | null, formatType: string) => {
    if (value === null || value === undefined) return '-';
    if (formatType === 'currency') return format(value);
    if (formatType === 'percent') return `${value.toFixed(1)}%`;
    return value.toLocaleString();
  };

  const handleCellChange = (metricKey: string, period: string, value: string) => {
    const num = parseFloat(value.replace(/,/g, ''));
    setEditingValues(prev => ({
      ...prev,
      [metricKey]: {
        ...(prev[metricKey] || {}),
        [period]: isNaN(num) ? 0 : num,
      },
    }));
  };

  const handleSave = async () => {
    if (!companyId) return;
    setIsSaving(true);

    try {
      const values: Array<{ metric_key: string; value: number; period_start: string }> = [];
      for (const [metricKey, periods] of Object.entries(editingValues)) {
        for (const [period, value] of Object.entries(periods)) {
          values.push({ metric_key: metricKey, value, period_start: period });
        }
      }

      if (values.length === 0) {
        toast({ title: 'No changes', description: 'Enter some values first.' });
        setIsSaving(false);
        return;
      }

      await apiRequest('POST', `/api/metrics/values/bulk?company_id=${companyId}`, { values });

      toast({ title: 'Saved', description: `${values.length} metric values saved successfully.` });
      setEditingValues({});
      queryClient.invalidateQueries({ queryKey: ['/api/metrics'] });
    } catch (err) {
      toast({ title: 'Error', description: 'Failed to save metric values.', variant: 'destructive' });
    } finally {
      setIsSaving(false);
    }
  };

  const hasChanges = Object.keys(editingValues).length > 0;

  if (metricsLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
        </CardHeader>
        <CardContent className="space-y-3">
          {[1,2,3].map(i => <Skeleton key={i} className="h-10 w-full" />)}
        </CardContent>
      </Card>
    );
  }

  if (!metrics || metrics.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Multi-Period Metrics
          </CardTitle>
          <CardDescription>
            No metric definitions found. Apply an industry template pack from Settings to get started with industry-specific metrics.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Multi-Period Metrics
            </CardTitle>
            <CardDescription>
              Enter monthly values for your tracked metrics. Changes are saved in bulk.
            </CardDescription>
          </div>
          {hasChanges && (
            <Button onClick={handleSave} disabled={isSaving} data-testid="button-save-metrics">
              {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              <span className="ml-2">Save {Object.values(editingValues).reduce((sum, periods) => sum + Object.keys(periods).length, 0)} values</span>
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="w-full">
          <div className="min-w-[600px]">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 pr-4 font-medium text-muted-foreground sticky left-0 bg-card min-w-[180px]">
                    Metric
                  </th>
                  {months.map(m => (
                    <th key={m} className="text-center py-2 px-2 font-medium text-muted-foreground min-w-[100px]">
                      {formatMonth(m)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {metrics.map(metric => (
                  <tr key={metric.key} className="border-b border-border/50" data-testid={`row-metric-${metric.key}`}>
                    <td className="py-2 pr-4 sticky left-0 bg-card">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-foreground">{metric.name}</span>
                        {metric.unit && (
                          <Badge variant="outline" className="text-xs">
                            {metric.unit === 'currency' ? currentCompany?.currency || 'USD' : metric.unit}
                          </Badge>
                        )}
                      </div>
                    </td>
                    {months.map(period => {
                      const editedValue = editingValues[metric.key]?.[period];
                      const isEdited = editedValue !== undefined;
                      return (
                        <td key={period} className="py-1 px-1">
                          <Input
                            type="number"
                            className={cn(
                              "h-8 text-center text-sm",
                              isEdited && "border-primary/50 bg-primary/5"
                            )}
                            placeholder={metric.latest_value !== null ? formatValue(metric.latest_value, metric.format_type) : '-'}
                            value={isEdited ? editedValue : ''}
                            onChange={(e) => handleCellChange(metric.key, period, e.target.value)}
                            data-testid={`input-metric-${metric.key}-${period}`}
                          />
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ScrollBar orientation="horizontal" />
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
