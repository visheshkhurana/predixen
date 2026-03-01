import { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useLocation } from 'wouter';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useFounderStore } from '@/store/founderStore';
import { useToast } from '@/hooks/use-toast';
import { apiRequest } from '@/lib/queryClient';
import { EmptyStateCard } from '@/components/ui/empty-state';
import {
  Plus,
  GripVertical,
  Settings,
  Trash2,
  ArrowLeft,
  Save,
  LayoutGrid,
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  ArrowDownRight,
  Info,
  Database,
  RefreshCw,
  BarChart3,
  LineChart as LineChartIcon,
  Table,
  Hash,
} from 'lucide-react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from 'recharts';

interface Widget {
  id: number;
  dashboard_id: number;
  widget_type: string;
  metric_key: string | null;
  title: string | null;
  config: Record<string, unknown> | null;
  position: { x: number; y: number; w: number; h: number };
}

interface Dashboard {
  id: number;
  company_id: number;
  name: string;
  description: string | null;
  layout_config: Record<string, unknown> | null;
  widgets?: Widget[];
}

interface MetricDefinition {
  id: number;
  key: string;
  name: string;
  description: string | null;
  formula: string;
  unit: string | null;
  format_type: string;
}

interface MetricLatest {
  metric_key: string;
  metric_name: string;
  value: number;
  unit: string | null;
  format_type: string;
  period_start: string;
  period_end: string;
  computed_at: string | null;
  raw_event_count: number;
  contributing_connectors: string[] | null;
}

const WIDGET_TYPES = [
  { id: 'kpi', name: 'KPI Card', icon: Hash, description: 'Big number with trend' },
  { id: 'line', name: 'Line Chart', icon: LineChartIcon, description: 'Trend over time' },
  { id: 'bar', name: 'Bar Chart', icon: BarChart3, description: 'Compare values' },
  { id: 'table', name: 'Table', icon: Table, description: 'Data table' },
];

function formatValue(value: number, formatType: string, unit?: string | null): string {
  if (formatType === 'currency') {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
    return `$${value.toFixed(0)}`;
  }
  if (formatType === 'percentage') {
    return `${(value * 100).toFixed(1)}%`;
  }
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return value.toFixed(value % 1 === 0 ? 0 : 2);
}

function KPIWidget({ widget, companyId }: { widget: Widget; companyId: number }) {
  const { data: metricData, isLoading } = useQuery<MetricLatest>({
    queryKey: [`/api/metrics/${widget.metric_key}/latest?company_id=${companyId}`],
    enabled: !!widget.metric_key,
    refetchInterval: 60000,
    staleTime: 30000,
  });

  if (isLoading) {
    return (
      <Card className="h-full">
        <CardContent className="p-4">
          <Skeleton className="h-4 w-24 mb-2" />
          <Skeleton className="h-8 w-32" />
        </CardContent>
      </Card>
    );
  }

  if (!metricData || metricData.value == null) {
    return (
      <Card className="h-full">
        <CardContent className="p-4 flex items-center justify-center h-full text-muted-foreground">
          No data available
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full relative">
      <CardHeader className="pb-2 flex flex-row items-center justify-between gap-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {widget.title || metricData.metric_name}
        </CardTitle>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon" data-testid={`widget-info-${widget.id}`}>
              <Info className="h-3 w-3" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="left" className="max-w-xs">
            <div className="space-y-1 text-xs">
              <p><strong>Period:</strong> {new Date(metricData.period_start).toLocaleDateString()} - {new Date(metricData.period_end).toLocaleDateString()}</p>
              {metricData.computed_at && <p><strong>Computed:</strong> {new Date(metricData.computed_at).toLocaleString()}</p>}
              {metricData.raw_event_count > 0 && <p><strong>Events:</strong> {metricData.raw_event_count}</p>}
              {metricData.contributing_connectors && metricData.contributing_connectors.length > 0 && (
                <p><strong>Sources:</strong> {metricData.contributing_connectors.join(', ')}</p>
              )}
            </div>
          </TooltipContent>
        </Tooltip>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold" data-testid={`widget-value-${widget.id}`}>
          {formatValue(metricData.value, metricData.format_type, metricData.unit)}
        </div>
      </CardContent>
    </Card>
  );
}

function LineChartWidget({ widget, companyId }: { widget: Widget; companyId: number }) {
  const { data: timeseriesData, isLoading } = useQuery<{ data: Array<{ period_start: string; value: number }> }>({
    queryKey: [`/api/metrics/${widget.metric_key}/timeseries?company_id=${companyId}`],
    enabled: !!widget.metric_key,
    refetchInterval: 60000,
    staleTime: 30000,
  });

  if (isLoading) {
    return (
      <Card className="h-full">
        <CardContent className="p-4">
          <Skeleton className="h-full w-full" />
        </CardContent>
      </Card>
    );
  }

  const chartData = timeseriesData?.data?.map(d => ({
    date: new Date(d.period_start).toLocaleDateString('en-US', { month: 'short' }),
    value: d.value,
  })) || [];

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{widget.title || 'Trend'}</CardTitle>
      </CardHeader>
      <CardContent className="h-[calc(100%-60px)]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="date" className="text-xs" />
            <YAxis className="text-xs" />
            <RechartsTooltip />
            <Line type="monotone" dataKey="value" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function BarChartWidget({ widget, companyId }: { widget: Widget; companyId: number }) {
  const { data: timeseriesData, isLoading } = useQuery<{ data: Array<{ period_start: string; value: number }> }>({
    queryKey: [`/api/metrics/${widget.metric_key}/timeseries?company_id=${companyId}&limit=6`],
    enabled: !!widget.metric_key,
    refetchInterval: 60000,
    staleTime: 30000,
  });

  if (isLoading) {
    return (
      <Card className="h-full">
        <CardContent className="p-4">
          <Skeleton className="h-full w-full" />
        </CardContent>
      </Card>
    );
  }

  const chartData = timeseriesData?.data?.map(d => ({
    date: new Date(d.period_start).toLocaleDateString('en-US', { month: 'short' }),
    value: d.value,
  })) || [];

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{widget.title || 'Comparison'}</CardTitle>
      </CardHeader>
      <CardContent className="h-[calc(100%-60px)]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="date" className="text-xs" />
            <YAxis className="text-xs" />
            <RechartsTooltip />
            <Bar dataKey="value" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function TableWidget({ widget, companyId }: { widget: Widget; companyId: number }) {
  const { data: timeseriesData, isLoading } = useQuery<{ data: Array<{ period_start: string; value: number }> }>({
    queryKey: [`/api/metrics/${widget.metric_key}/timeseries?company_id=${companyId}&limit=12`],
    enabled: !!widget.metric_key,
    refetchInterval: 60000,
    staleTime: 30000,
  });

  if (isLoading) {
    return (
      <Card className="h-full">
        <CardContent className="p-4">
          <Skeleton className="h-full w-full" />
        </CardContent>
      </Card>
    );
  }

  const tableData = timeseriesData?.data || [];

  return (
    <Card className="h-full overflow-auto">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{widget.title || 'Data Table'}</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 sticky top-0">
            <tr>
              <th className="text-left p-2 font-medium">Period</th>
              <th className="text-right p-2 font-medium">Value</th>
            </tr>
          </thead>
          <tbody>
            {tableData.length === 0 ? (
              <tr>
                <td colSpan={2} className="p-4 text-center text-muted-foreground">No data available</td>
              </tr>
            ) : (
              tableData.map((row, idx) => (
                <tr key={idx} className="border-t">
                  <td className="p-2">{new Date(row.period_start).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}</td>
                  <td className="p-2 text-right font-mono">{row.value.toLocaleString()}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function WidgetRenderer({ widget, companyId }: { widget: Widget; companyId: number }) {
  switch (widget.widget_type) {
    case 'kpi':
      return <KPIWidget widget={widget} companyId={companyId} />;
    case 'line':
      return <LineChartWidget widget={widget} companyId={companyId} />;
    case 'bar':
      return <BarChartWidget widget={widget} companyId={companyId} />;
    case 'table':
      return <TableWidget widget={widget} companyId={companyId} />;
    default:
      return (
        <Card className="h-full">
          <CardContent className="p-4 flex items-center justify-center h-full text-muted-foreground">
            Unknown widget type
          </CardContent>
        </Card>
      );
  }
}

export default function DashboardBuilderPage() {
  const params = useParams<{ id: string }>();
  const dashboardId = params.id ? parseInt(params.id) : null;
  const [, setLocation] = useLocation();
  const { currentCompany } = useFounderStore();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  
  const [addWidgetOpen, setAddWidgetOpen] = useState(false);
  const [selectedWidgetType, setSelectedWidgetType] = useState<string>('kpi');
  const [selectedMetric, setSelectedMetric] = useState<string>('');
  const [widgetTitle, setWidgetTitle] = useState<string>('');

  const { data: dashboard, isLoading: dashboardLoading } = useQuery<Dashboard>({
    queryKey: [`/api/dashboards/${dashboardId}`],
    enabled: !!dashboardId,
  });

  const { data: metrics = [], isSuccess: metricsLoaded } = useQuery<MetricDefinition[]>({
    queryKey: [`/api/metrics?company_id=${currentCompany?.id}`],
    enabled: !!currentCompany,
  });

  const initRef = useRef(false);
  useEffect(() => {
    if (metricsLoaded && metrics.length === 0 && currentCompany && !initRef.current) {
      initRef.current = true;
      apiRequest('POST', `/api/metrics/initialize?company_id=${currentCompany.id}`)
        .then(() => {
          queryClient.invalidateQueries({ queryKey: [`/api/metrics?company_id=${currentCompany.id}`] });
        })
        .catch(() => {});
    }
  }, [metricsLoaded, metrics.length, currentCompany, queryClient]);

  const addWidgetMutation = useMutation({
    mutationFn: async (widget: { widget_type: string; metric_key: string; title: string; position: object }) => {
      const res = await apiRequest('POST', `/api/dashboards/${dashboardId}/widgets`, widget);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`/api/dashboards/${dashboardId}`] });
      setAddWidgetOpen(false);
      setWidgetTitle('');
      setSelectedMetric('');
      toast({ title: 'Widget added', description: 'Your widget has been added to the dashboard.' });
    },
  });

  const deleteWidgetMutation = useMutation({
    mutationFn: async (widgetId: number) => {
      const res = await apiRequest('DELETE', `/api/dashboards/widgets/${widgetId}`);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`/api/dashboards/${dashboardId}`] });
      toast({ title: 'Widget removed' });
    },
  });

  const handleAddWidget = () => {
    if (!selectedMetric) {
      toast({ title: 'Select a metric', variant: 'destructive' });
      return;
    }

    const existingWidgets = dashboard?.widgets || [];
    const nextY = existingWidgets.length > 0 
      ? Math.max(...existingWidgets.map(w => w.position.y + w.position.h)) 
      : 0;

    addWidgetMutation.mutate({
      widget_type: selectedWidgetType,
      metric_key: selectedMetric,
      title: widgetTitle || metrics.find(m => m.key === selectedMetric)?.name || '',
      position: { x: 0, y: nextY, w: selectedWidgetType === 'kpi' ? 3 : 6, h: selectedWidgetType === 'kpi' ? 2 : 4 },
    });
  };

  useEffect(() => {
    if (!dashboardLoading && !dashboard && dashboardId) {
      setLocation('/dashboards');
    }
  }, [dashboardLoading, dashboard, dashboardId, setLocation]);

  if (!currentCompany) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            Please select a company first
          </CardContent>
        </Card>
      </div>
    );
  }

  if (dashboardLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-32" />)}
        </div>
      </div>
    );
  }

  if (!dashboard && dashboardId) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6 text-center">
            <p className="text-muted-foreground mb-4">Redirecting to dashboards...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => setLocation('/dashboards')} data-testid="button-back">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold" data-testid="dashboard-title">{dashboard?.name || 'Dashboard'}</h1>
            {dashboard?.description && (
              <p className="text-muted-foreground">{dashboard.description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => queryClient.invalidateQueries({ queryKey: ['/api/dashboards', dashboardId] })} data-testid="button-refresh">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={() => setAddWidgetOpen(true)} data-testid="button-add-widget">
            <Plus className="h-4 w-4 mr-2" />
            Add Widget
          </Button>
        </div>
      </div>

      {(!dashboard?.widgets || dashboard.widgets.length === 0) ? (
        <EmptyStateCard
          icon={LayoutGrid}
          title="Start Building Your Dashboard"
          description="Add widgets to display KPIs, charts, and tables. Drag and resize to customize your layout."
          action={{
            label: "Add Widget",
            onClick: () => setAddWidgetOpen(true),
            icon: Plus,
          }}
        />
      ) : (
        <div className="grid grid-cols-12 gap-4 auto-rows-[80px]">
          {dashboard.widgets.map(widget => (
            <div
              key={widget.id}
              className="relative group"
              style={{
                gridColumn: `span ${widget.position.w}`,
                gridRow: `span ${widget.position.h}`,
              }}
              data-testid={`widget-${widget.id}`}
            >
              <div className="absolute top-2 right-2 z-10 invisible group-hover:visible flex gap-1">
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => deleteWidgetMutation.mutate(widget.id)}
                  data-testid={`button-delete-widget-${widget.id}`}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
              <WidgetRenderer widget={widget} companyId={currentCompany.id} />
            </div>
          ))}
        </div>
      )}

      <Dialog open={addWidgetOpen} onOpenChange={setAddWidgetOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Widget</DialogTitle>
            <DialogDescription>
              Select a widget type and metric to display
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Widget Type</label>
              <div className="grid grid-cols-2 gap-2">
                {WIDGET_TYPES.map(type => (
                  <div
                    key={type.id}
                    className={`p-3 border rounded-lg cursor-pointer hover-elevate ${
                      selectedWidgetType === type.id ? 'border-primary bg-primary/5' : ''
                    }`}
                    onClick={() => setSelectedWidgetType(type.id)}
                    data-testid={`widget-type-${type.id}`}
                  >
                    <type.icon className="h-5 w-5 mb-1" />
                    <p className="font-medium text-sm">{type.name}</p>
                    <p className="text-xs text-muted-foreground">{type.description}</p>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Metric</label>
              <Select value={selectedMetric} onValueChange={setSelectedMetric}>
                <SelectTrigger data-testid="select-metric">
                  <SelectValue placeholder="Select a metric" />
                </SelectTrigger>
                <SelectContent>
                  {metrics.map(metric => (
                    <SelectItem key={metric.key} value={metric.key}>
                      {metric.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Title (optional)</label>
              <Input
                value={widgetTitle}
                onChange={(e) => setWidgetTitle(e.target.value)}
                placeholder="Custom title for the widget"
                data-testid="input-widget-title"
              />
            </div>
          </div>

          <DialogFooter>
            <DialogClose asChild>
              <Button variant="ghost" data-testid="button-cancel-widget">Cancel</Button>
            </DialogClose>
            <Button onClick={handleAddWidget} disabled={addWidgetMutation.isPending} data-testid="button-confirm-add-widget">
              {addWidgetMutation.isPending ? 'Adding...' : 'Add Widget'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
