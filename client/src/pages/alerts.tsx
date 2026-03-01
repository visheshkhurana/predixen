import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { useFounderStore } from "@/store/founderStore";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { 
  AlertTriangle, 
  AlertCircle, 
  Info, 
  CheckCircle, 
  TrendingUp, 
  TrendingDown,
  Activity,
  RefreshCw,
  Settings,
  Database,
  ArrowRight,
  HelpCircle,
  Minus,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { LineChart, Line, ResponsiveContainer } from "recharts";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";

interface Alert {
  id: string;
  type: string;
  severity: "info" | "warning" | "critical";
  metric: string;
  message: string;
  details: Record<string, unknown>;
  created_at: string;
  is_active: boolean;
}

interface DriverHealth {
  metric: string;
  status: "healthy" | "warning" | "critical" | "unknown";
  current_value: number;
  historical_mean: number;
  z_score: number;
  trend_direction: "up" | "down" | "flat";
  alert_count: number;
  history?: number[];
}

interface AlertsResponse {
  alerts: Alert[];
  health: Record<string, DriverHealth>;
  total_alerts: number;
  critical_count: number;
  warning_count: number;
}

interface AlertThreshold {
  id: string;
  metric: string;
  operator: "lt" | "gt" | "lte" | "gte";
  value: number;
  severity: "warning" | "critical";
  enabled: boolean;
}

const severityIcons = {
  info: <Info className="h-4 w-4" />,
  warning: <AlertTriangle className="h-4 w-4" />,
  critical: <AlertCircle className="h-4 w-4" />,
};

const severityColors = {
  info: "bg-blue-500/10 text-blue-500 border-blue-500/20",
  warning: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
  critical: "bg-red-500/10 text-red-500 border-red-500/20",
};

const DEFAULT_THRESHOLDS: AlertThreshold[] = [
  { id: "1", metric: "runway_months", operator: "lt", value: 6, severity: "critical", enabled: true },
  { id: "2", metric: "runway_months", operator: "lt", value: 12, severity: "warning", enabled: true },
  { id: "3", metric: "burn_multiple", operator: "gt", value: 2.0, severity: "warning", enabled: true },
  { id: "4", metric: "burn_multiple", operator: "gt", value: 3.0, severity: "critical", enabled: true },
  { id: "5", metric: "revenue_growth_mom", operator: "lt", value: 5, severity: "warning", enabled: true },
  { id: "6", metric: "gross_margin", operator: "lt", value: 0.5, severity: "warning", enabled: true },
  { id: "7", metric: "churn_rate", operator: "gt", value: 0.05, severity: "warning", enabled: true },
];

const METRIC_DISPLAY_NAMES: Record<string, string> = {
  runway_months: "Runway (Months)",
  burn_multiple: "Burn Multiple",
  revenue_growth_mom: "Revenue Growth (MoM %)",
  gross_margin: "Gross Margin",
  churn_rate: "Churn Rate",
  net_burn: "Net Burn",
  mrr: "Monthly Recurring Revenue",
  arr: "Annual Recurring Revenue",
};

const OPERATOR_LABELS: Record<string, string> = {
  lt: "less than",
  gt: "greater than",
  lte: "less than or equal to",
  gte: "greater than or equal to",
};

function Sparkline({ data, color = "currentColor", height = 24 }: { data: number[]; color?: string; height?: number }) {
  if (!data || data.length < 2) return null;
  
  const chartData = data.map((value, index) => ({ value, index }));
  
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData}>
        <Line 
          type="monotone" 
          dataKey="value" 
          stroke={color} 
          strokeWidth={1.5} 
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

function TrafficLightIndicator({ status }: { status: "healthy" | "warning" | "critical" | "unknown" }) {
  return (
    <div className="flex gap-1" data-testid="traffic-light-indicator">
      <div className={cn(
        "w-3 h-3 rounded-full border",
        status === "critical" ? "bg-red-500 border-red-600" : "bg-muted border-muted-foreground/20"
      )} />
      <div className={cn(
        "w-3 h-3 rounded-full border",
        status === "warning" ? "bg-yellow-500 border-yellow-600" : "bg-muted border-muted-foreground/20"
      )} />
      <div className={cn(
        "w-3 h-3 rounded-full border",
        status === "healthy" ? "bg-green-500 border-green-600" : "bg-muted border-muted-foreground/20"
      )} />
    </div>
  );
}

function UnknownStatusCard() {
  return (
    <Card className="border-dashed border-2 border-muted-foreground/30" data-testid="card-unknown-status">
      <CardContent className="py-8 text-center space-y-4">
        <div className="mx-auto w-16 h-16 rounded-full bg-muted flex items-center justify-center">
          <HelpCircle className="h-8 w-8 text-muted-foreground" />
        </div>
        <div className="space-y-2">
          <h3 className="text-lg font-semibold">Status Unknown</h3>
          <p className="text-muted-foreground max-w-md mx-auto">
            We need financial data to assess your company's health. 
            Complete the Data Input or run a Truth Scan to get started.
          </p>
        </div>
        <div className="flex items-center justify-center gap-3 flex-wrap">
          <Link href="/data">
            <Button data-testid="button-go-to-data-input">
              <Database className="h-4 w-4 mr-2" />
              Go to Data Input
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </Link>
          <Link href="/truth">
            <Button variant="outline" data-testid="button-go-to-truth-scan">
              Run Truth Scan
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

function HealthDashboard({ drivers }: { drivers: Record<string, DriverHealth> }) {
  const keyMetrics = [
    { key: "runway_months", label: "Runway", unit: " months", format: (v: number) => v.toFixed(1) },
    { key: "burn_multiple", label: "Burn Multiple", unit: "x", format: (v: number) => v.toFixed(2) },
    { key: "revenue_growth_mom", label: "Revenue Growth", unit: "%", format: (v: number) => (v * 100).toFixed(1) },
    { key: "gross_margin", label: "Gross Margin", unit: "%", format: (v: number) => (v * 100).toFixed(1) },
    { key: "net_burn", label: "Net Burn", unit: "", format: (v: number) => `$${(v / 1000).toFixed(0)}K` },
    { key: "churn_rate", label: "Churn Rate", unit: "%", format: (v: number) => (v * 100).toFixed(2) },
  ];

  const getSparklineColor = (status: string) => {
    switch (status) {
      case "healthy": return "hsl(142, 70%, 45%)";
      case "warning": return "hsl(38, 92%, 50%)";
      case "critical": return "hsl(0, 84%, 60%)";
      default: return "hsl(210, 15%, 60%)";
    }
  };

  const hasAnyData = Object.keys(drivers).length > 0;

  if (!hasAnyData) {
    return <UnknownStatusCard />;
  }

  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="health-dashboard">
      {keyMetrics.map((metric) => {
        const health = drivers[metric.key];
        const hasData = health && health.status !== "unknown";
        
        return (
          <Card key={metric.key} data-testid={`health-metric-${metric.key}`}>
            <CardContent className="py-4">
              <div className="flex items-center justify-between mb-3 gap-2">
                <span className="text-sm font-medium text-muted-foreground">{metric.label}</span>
                {hasData ? (
                  <TrafficLightIndicator status={health.status} />
                ) : (
                  <Badge variant="secondary" className="text-xs">No data</Badge>
                )}
              </div>
              
              {hasData ? (
                <>
                  <div className="flex items-end justify-between gap-4">
                    <div className="flex items-baseline gap-1">
                      <span className="text-2xl font-bold font-mono">
                        {metric.format(health.current_value)}
                      </span>
                      {metric.unit && metric.key !== "net_burn" && (
                        <span className="text-sm text-muted-foreground">{metric.unit}</span>
                      )}
                    </div>
                    <div className="flex items-center gap-1 text-sm">
                      {health.trend_direction === "up" ? (
                        <TrendingUp className="h-4 w-4 text-green-500" />
                      ) : health.trend_direction === "down" ? (
                        <TrendingDown className="h-4 w-4 text-red-500" />
                      ) : (
                        <Minus className="h-4 w-4 text-muted-foreground" />
                      )}
                    </div>
                  </div>
                  
                  {health.history && health.history.length >= 2 && (
                    <div className="mt-3 h-6">
                      <Sparkline 
                        data={health.history} 
                        color={getSparklineColor(health.status)}
                      />
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-2">
                  <p className="text-sm text-muted-foreground">
                    Add data to see this metric
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

function ThresholdConfigModal({ thresholds, onSave }: { thresholds: AlertThreshold[]; onSave: (thresholds: AlertThreshold[]) => void }) {
  const [localThresholds, setLocalThresholds] = useState<AlertThreshold[]>(thresholds);
  const { toast } = useToast();

  const handleToggle = (id: string) => {
    setLocalThresholds(prev => 
      prev.map(t => t.id === id ? { ...t, enabled: !t.enabled } : t)
    );
  };

  const handleValueChange = (id: string, value: string) => {
    const numValue = parseFloat(value);
    if (!isNaN(numValue)) {
      setLocalThresholds(prev =>
        prev.map(t => t.id === id ? { ...t, value: numValue } : t)
      );
    }
  };

  const handleSave = () => {
    onSave(localThresholds);
    toast({
      title: "Thresholds Saved",
      description: "Your alert thresholds have been updated.",
    });
  };

  const handleReset = () => {
    setLocalThresholds(DEFAULT_THRESHOLDS);
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" data-testid="button-configure-thresholds">
          <Settings className="h-4 w-4 mr-2" />
          Configure Thresholds
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Alert Threshold Configuration</DialogTitle>
          <DialogDescription>
            Customize when alerts are triggered based on your specific needs. 
            Configure thresholds for key metrics to receive timely warnings.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="rounded-lg bg-muted/50 p-4 space-y-2">
            <div className="flex items-center gap-2">
              <Info className="h-4 w-4 text-primary" />
              <span className="text-sm font-medium">How it works</span>
            </div>
            <p className="text-sm text-muted-foreground">
              When a metric crosses a threshold, an alert is created. Critical alerts indicate 
              urgent issues requiring immediate attention. Warning alerts highlight potential concerns.
            </p>
          </div>

          <div className="space-y-3">
            {localThresholds.map((threshold) => (
              <div 
                key={threshold.id} 
                className={cn(
                  "flex items-center gap-4 p-3 rounded-lg border",
                  threshold.enabled ? "bg-card" : "bg-muted/30"
                )}
                data-testid={`threshold-${threshold.id}`}
              >
                <Switch
                  checked={threshold.enabled}
                  onCheckedChange={() => handleToggle(threshold.id)}
                  data-testid={`switch-threshold-${threshold.id}`}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge 
                      variant={threshold.severity === "critical" ? "destructive" : "outline"}
                      className={threshold.severity === "warning" ? "bg-yellow-500/10 text-yellow-500 border-yellow-500/20" : ""}
                    >
                      {threshold.severity}
                    </Badge>
                    <span className="text-sm">
                      {METRIC_DISPLAY_NAMES[threshold.metric] || threshold.metric.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      {OPERATOR_LABELS[threshold.operator]}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    value={threshold.value}
                    onChange={(e) => handleValueChange(threshold.id, e.target.value)}
                    className="w-24"
                    disabled={!threshold.enabled}
                    data-testid={`input-threshold-${threshold.id}`}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="rounded-lg border border-dashed p-4 space-y-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-yellow-500" />
              <span className="text-sm font-medium">Sample Alert Preview</span>
            </div>
            <div className="space-y-2">
              <div className="flex items-start gap-3 p-2 rounded bg-yellow-500/10 text-sm">
                <AlertTriangle className="h-4 w-4 text-yellow-500 mt-0.5 shrink-0" />
                <span>
                  <strong>Warning:</strong> Runway is below 12 months (currently 10.5 months). 
                  Consider reducing burn or accelerating revenue growth.
                </span>
              </div>
              <div className="flex items-start gap-3 p-2 rounded bg-red-500/10 text-sm">
                <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
                <span>
                  <strong>Critical:</strong> Runway has dropped below 6 months (currently 5.2 months). 
                  Immediate action required to extend runway or secure funding.
                </span>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={handleReset} data-testid="button-reset-thresholds">
            Reset to Defaults
          </Button>
          <DialogClose asChild>
            <Button variant="ghost" data-testid="button-cancel-thresholds">Cancel</Button>
          </DialogClose>
          <DialogClose asChild>
            <Button onClick={handleSave} data-testid="button-save-thresholds">Save Changes</Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function AlertsPage() {
  const { currentCompany } = useFounderStore();
  const companyId = currentCompany?.id;
  const [thresholds, setThresholds] = useState<AlertThreshold[]>(DEFAULT_THRESHOLDS);

  const { data: alertsData, isLoading, refetch } = useQuery<AlertsResponse>({
    queryKey: ["/api/alerts/companies", companyId, "alerts"],
    enabled: !!companyId,
  });

  const { data: healthData } = useQuery<{
    overall_status: string;
    drivers: Record<string, DriverHealth>;
    recommendations: string[];
  }>({
    queryKey: ["/api/alerts/companies", companyId, "analyze"],
    enabled: !!companyId,
  });

  const formatValue = (value: number, metric: string) => {
    if (metric.includes("margin") || metric.includes("rate")) {
      return `${(value * 100).toFixed(1)}%`;
    }
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`;
    }
    if (value >= 1000) {
      return `$${(value / 1000).toFixed(1)}K`;
    }
    return `$${value.toFixed(0)}`;
  };

  const getOverallStatusBadge = (status: string) => {
    switch (status) {
      case "healthy":
        return (
          <Badge className="bg-green-500/10 text-green-500 border-green-500/20">
            <CheckCircle className="h-3 w-3 mr-1" />
            Healthy
          </Badge>
        );
      case "warning":
        return (
          <Badge className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20">
            <AlertTriangle className="h-3 w-3 mr-1" />
            Attention Needed
          </Badge>
        );
      case "critical":
        return (
          <Badge className="bg-red-500/10 text-red-500 border-red-500/20">
            <AlertCircle className="h-3 w-3 mr-1" />
            Critical Issues
          </Badge>
        );
      case "insufficient_data":
        return (
          <Badge variant="secondary" className="gap-1">
            <Info className="h-3 w-3" />
            Needs More Data
          </Badge>
        );
      default:
        return (
          <Badge variant="secondary" className="gap-1">
            <HelpCircle className="h-3 w-3" />
            Unknown
          </Badge>
        );
    }
  };

  const isStatusUnknown = !healthData?.overall_status || healthData.overall_status === "unknown";
  const isInsufficientData = healthData?.overall_status === "insufficient_data";

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold" data-testid="text-page-title">Alerts & Monitoring</h1>
          <p className="text-muted-foreground">
            Track anomalies, threshold breaches, and driver health
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <ThresholdConfigModal thresholds={thresholds} onSave={setThresholds} />
          <Button variant="outline" onClick={() => refetch()} data-testid="button-refresh">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {isInsufficientData && (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="py-4">
            <div className="flex items-start gap-3">
              <Info className="h-5 w-5 text-amber-500 mt-0.5 shrink-0" />
              <div className="flex-1">
                <p className="font-medium">More Data Needed</p>
                <p className="text-sm text-muted-foreground mt-1">
                  We need at least 2 months of financial data to analyze trends and generate alerts.
                  Add more historical data to enable full monitoring capabilities.
                </p>
              </div>
              <Link href="/data">
                <Button size="sm" variant="outline" data-testid="button-banner-add-data">
                  Add More Data
                  <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      {isStatusUnknown && !isInsufficientData && (
        <Card className="border-primary/30 bg-primary/5">
          <CardContent className="py-4">
            <div className="flex items-start gap-3">
              <Info className="h-5 w-5 text-primary mt-0.5 shrink-0" />
              <div className="flex-1">
                <p className="font-medium">Data Required for Monitoring</p>
                <p className="text-sm text-muted-foreground mt-1">
                  To enable alerts and health monitoring, we need your company's financial data. 
                  Upload your data or run a Truth Scan to get personalized insights and alerts.
                </p>
              </div>
              <Link href="/data">
                <Button size="sm" data-testid="button-banner-data-input">
                  Add Data
                  <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-sm text-muted-foreground">Overall Status</p>
                <div className="mt-1">
                  {getOverallStatusBadge(healthData?.overall_status || "unknown")}
                </div>
              </div>
              <Activity className="h-8 w-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-sm text-muted-foreground">Total Alerts</p>
                <p className="text-2xl font-bold" data-testid="text-total-alerts">
                  {alertsData?.total_alerts || 0}
                </p>
              </div>
              <AlertCircle className="h-8 w-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-sm text-muted-foreground">Critical</p>
                <p className="text-2xl font-bold text-red-500" data-testid="text-critical-count">
                  {alertsData?.critical_count || 0}
                </p>
              </div>
              <AlertCircle className="h-8 w-8 text-red-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-sm text-muted-foreground">Warnings</p>
                <p className="text-2xl font-bold text-yellow-500" data-testid="text-warning-count">
                  {alertsData?.warning_count || 0}
                </p>
              </div>
              <AlertTriangle className="h-8 w-8 text-yellow-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="health">
        <TabsList data-testid="tabs-view">
          <TabsTrigger value="health" data-testid="tab-health">Health Dashboard</TabsTrigger>
          <TabsTrigger value="alerts" data-testid="tab-alerts">Active Alerts</TabsTrigger>
          <TabsTrigger value="drivers" data-testid="tab-drivers">Driver Details</TabsTrigger>
          <TabsTrigger value="recommendations" data-testid="tab-recommendations">Recommendations</TabsTrigger>
        </TabsList>

        <TabsContent value="health" className="space-y-4">
          <HealthDashboard drivers={healthData?.drivers || {}} />
        </TabsContent>

        <TabsContent value="alerts" className="space-y-4">
          {isLoading ? (
            <div className="space-y-3">
              {Array(3).fill(0).map((_, i) => (
                <Card key={i}>
                  <CardContent className="p-4">
                    <div className="flex items-start gap-4">
                      <Skeleton className="h-8 w-8 rounded-full shrink-0" />
                      <div className="flex-1 space-y-2">
                        <Skeleton className="h-4 w-3/4" />
                        <Skeleton className="h-3 w-1/2" />
                        <div className="flex gap-2 pt-1">
                          <Skeleton className="h-5 w-16 rounded-full" />
                          <Skeleton className="h-5 w-20 rounded-full" />
                        </div>
                      </div>
                      <Skeleton className="h-4 w-20" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : alertsData?.alerts && alertsData.alerts.length > 0 ? (
            <div className="space-y-3">
              {alertsData.alerts.map((alert) => (
                <Card key={alert.id} className={`border ${severityColors[alert.severity]}`} data-testid={`card-alert-${alert.id}`}>
                  <CardContent className="py-4">
                    <div className="flex items-start gap-4">
                      <div className={severityColors[alert.severity].split(" ")[1]}>
                        {severityIcons[alert.severity]}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <Badge variant="outline" className="text-xs">
                            {alert.type.replace(/_/g, " ")}
                          </Badge>
                          <Badge variant="secondary" className="text-xs">
                            {METRIC_DISPLAY_NAMES[alert.metric] || alert.metric.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                          </Badge>
                        </div>
                        <p className="font-medium">{alert.message}</p>
                        <p className="text-sm text-muted-foreground mt-1">
                          {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}
                        </p>
                      </div>
                      <Button size="sm" variant="ghost" data-testid={`button-acknowledge-${alert.id}`}>
                        Acknowledge
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <CheckCircle className="h-12 w-12 mx-auto text-green-500 mb-4" />
                <p className="text-lg font-medium">No Active Alerts</p>
                <p className="text-muted-foreground">
                  {isStatusUnknown 
                    ? "Add your financial data to enable alert monitoring." 
                    : "All metrics are within normal ranges"}
                </p>
                {isStatusUnknown && (
                  <Link href="/data">
                    <Button className="mt-4" data-testid="button-empty-add-data">
                      <Database className="h-4 w-4 mr-2" />
                      Add Data
                    </Button>
                  </Link>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="drivers" className="space-y-4">
          {healthData?.drivers && Object.keys(healthData.drivers).length > 0 ? (
            <div className="grid md:grid-cols-2 gap-4">
              {Object.entries(healthData.drivers).map(([name, health]) => (
                <Card key={name} data-testid={`card-driver-${name}`}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between gap-2">
                      <CardTitle className="text-lg capitalize">{name.replace(/_/g, " ")}</CardTitle>
                      <Badge
                        variant="outline"
                        className={
                          health.status === "healthy"
                            ? "bg-green-500/10 text-green-500"
                            : health.status === "warning"
                            ? "bg-yellow-500/10 text-yellow-500"
                            : health.status === "critical"
                            ? "bg-red-500/10 text-red-500"
                            : ""
                        }
                      >
                        {health.status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Current Value</span>
                      <span className="font-medium">{formatValue(health.current_value, name)}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Historical Mean</span>
                      <span>{formatValue(health.historical_mean, name)}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Trend</span>
                      <span className="flex items-center gap-1">
                        {health.trend_direction === "up" ? (
                          <TrendingUp className="h-4 w-4 text-green-500" />
                        ) : health.trend_direction === "down" ? (
                          <TrendingDown className="h-4 w-4 text-red-500" />
                        ) : (
                          <span className="text-muted-foreground">Flat</span>
                        )}
                        {health.trend_direction}
                      </span>
                    </div>
                    <div>
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="text-muted-foreground">Z-Score</span>
                        <span>{health.z_score.toFixed(2)}</span>
                      </div>
                      <Progress
                        value={Math.min(Math.abs(health.z_score) * 25, 100)}
                        className={
                          Math.abs(health.z_score) > 2
                            ? "[&>div]:bg-red-500"
                            : Math.abs(health.z_score) > 1
                            ? "[&>div]:bg-yellow-500"
                            : "[&>div]:bg-green-500"
                        }
                      />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <UnknownStatusCard />
          )}
        </TabsContent>

        <TabsContent value="recommendations" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recommendations</CardTitle>
              <CardDescription>
                Actionable insights based on your current metrics
              </CardDescription>
            </CardHeader>
            <CardContent>
              {healthData?.recommendations && healthData.recommendations.length > 0 ? (
                <ul className="space-y-3">
                  {healthData.recommendations.map((rec, index) => (
                    <li key={index} className="flex items-start gap-3 p-3 bg-muted rounded-lg">
                      <Info className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                      <p>{rec}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-center py-8">
                  {isStatusUnknown ? (
                    <div className="space-y-3">
                      <p className="text-muted-foreground">
                        Add your financial data to receive personalized recommendations.
                      </p>
                      <Link href="/data">
                        <Button variant="outline" data-testid="button-recommendations-add-data">
                          <Database className="h-4 w-4 mr-2" />
                          Add Data
                        </Button>
                      </Link>
                    </div>
                  ) : (
                    <p className="text-muted-foreground">No recommendations available</p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
