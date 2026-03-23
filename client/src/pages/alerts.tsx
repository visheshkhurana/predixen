import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Link } from "wouter";
import { useSEO } from "@/lib/seo";
import { useFounderStore } from "@/store/founderStore";
import { useFinancialMetrics } from "@/hooks/useFinancialMetrics";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
  ChevronDown,
  ChevronRight,
  Mail,
  Loader2,
  Zap,
  Eye,
  FlaskConical,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { LineChart, Line, ResponsiveContainer } from "recharts";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";
import { apiRequest, queryClient } from "@/lib/queryClient";

interface SmartAlert {
  id: string;
  type: string;
  severity: "critical" | "warning" | "info" | "success";
  title: string;
  message: string;
  metric: string;
  currentValue: number;
  previousValue: number;
  changePercent: number;
  timestamp: string;
  acknowledged: boolean;
  suggestedAction: string;
}

interface AlertRule {
  id: string;
  type: string;
  enabled: boolean;
  threshold: number;
  label: string;
  description: string;
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
  alerts: SmartAlert[];
  total: number;
  unacknowledged: number;
}

interface OldAlertsResponse {
  alerts: { id: string; type: string; severity: "info" | "warning" | "critical"; metric: string; message: string; details: Record<string, unknown>; created_at: string; is_active: boolean }[];
  health: Record<string, DriverHealth>;
  total_alerts: number;
  critical_count: number;
  warning_count: number;
}

const severityIcons = {
  info: <Info className="h-4 w-4" />,
  success: <CheckCircle className="h-4 w-4" />,
  warning: <AlertTriangle className="h-4 w-4" />,
  critical: <AlertCircle className="h-4 w-4" />,
};

const severityColors = {
  info: "bg-blue-500/10 text-blue-500 border-blue-500/20",
  success: "bg-green-500/10 text-green-500 border-green-500/20",
  warning: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
  critical: "bg-red-500/10 text-red-500 border-red-500/20",
};

const METRIC_DISPLAY_NAMES: Record<string, string> = {
  runway_months: "Runway (Months)",
  burn_multiple: "Burn Multiple",
  revenue_growth_mom: "Revenue Growth (MoM %)",
  gross_margin: "Gross Margin",
  churn_rate: "Churn Rate",
  net_burn: "Net Burn",
  mrr: "Monthly Recurring Revenue",
  arr: "Annual Recurring Revenue",
  burn_rate: "Burn Rate",
  monthly_burn: "Monthly Burn",
  growth_rate: "Growth Rate",
};

const DEFAULT_ALERT_RULES: AlertRule[] = [
  { id: "burn-spike", type: "burn_spike", enabled: true, threshold: 15, label: "Burn Spike", description: "Alert when monthly burn increases by more than threshold %" },
  { id: "mrr-drop", type: "mrr_drop", enabled: true, threshold: 5, label: "MRR Drop", description: "Alert when MRR drops by more than threshold %" },
  { id: "churn-spike", type: "churn_spike", enabled: true, threshold: 10, label: "Churn Spike", description: "Alert when churn increases by more than threshold %" },
  { id: "runway-warning", type: "runway_warning", enabled: true, threshold: 12, label: "Runway Warning", description: "Alert when runway drops below threshold months" },
  { id: "runway-caution", type: "runway_caution", enabled: true, threshold: 18, label: "Runway Caution", description: "Alert when runway drops below threshold months" },
  { id: "growth-slowdown", type: "growth_slowdown", enabled: true, threshold: 30, label: "Growth Slowdown", description: "Alert when growth rate drops by more than threshold %" },
];

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

function AlertCard({ alert, companyId, onAcknowledge }: { alert: SmartAlert; companyId: number; onAcknowledge: (id: string) => void }) {
  const [expanded, setExpanded] = useState(false);

  const formatMetricChange = (current: number, previous: number, changePercent: number) => {
    const direction = changePercent >= 0 ? "+" : "";
    return `${direction}${changePercent.toFixed(1)}%`;
  };

  return (
    <Collapsible open={expanded} onOpenChange={setExpanded}>
      <Card className={cn("border", severityColors[alert.severity])} data-testid={`card-alert-${alert.id}`}>
        <CardContent className="py-4">
          <div className="flex items-start gap-4">
            <div className={cn("mt-0.5 shrink-0", severityColors[alert.severity].split(" ")[1])}>
              {severityIcons[alert.severity]}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <Badge
                  variant={alert.severity === "critical" ? "destructive" : "outline"}
                  className={cn(
                    "text-xs",
                    alert.severity === "warning" && "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
                    alert.severity === "info" && "bg-blue-500/10 text-blue-500 border-blue-500/20",
                    alert.severity === "success" && "bg-green-500/10 text-green-500 border-green-500/20"
                  )}
                >
                  {alert.severity}
                </Badge>
                <Badge variant="secondary" className="text-xs">
                  {alert.type.replace(/_/g, " ")}
                </Badge>
                {alert.acknowledged && (
                  <Badge variant="secondary" className="text-xs bg-muted">
                    Acknowledged
                  </Badge>
                )}
              </div>
              <p className="font-medium" data-testid={`text-alert-title-${alert.id}`}>{alert.title}</p>
              <p className="text-sm text-muted-foreground mt-0.5">{alert.message}</p>
              <div className="flex items-center gap-4 mt-2 flex-wrap">
                <span className="text-xs text-muted-foreground" data-testid={`text-alert-time-${alert.id}`}>
                  {formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true })}
                </span>
                {alert.currentValue !== undefined && alert.previousValue !== undefined && (
                  <span className={cn(
                    "text-xs font-mono font-medium",
                    alert.changePercent >= 0 ? "text-green-500" : "text-red-500"
                  )} data-testid={`text-alert-change-${alert.id}`}>
                    {formatMetricChange(alert.currentValue, alert.previousValue, alert.changePercent)}
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              {!alert.acknowledged && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => onAcknowledge(alert.id)}
                  data-testid={`button-acknowledge-${alert.id}`}
                >
                  <CheckCircle className="h-4 w-4 mr-1" />
                  Acknowledge
                </Button>
              )}
              <CollapsibleTrigger asChild>
                <Button size="icon" variant="ghost" data-testid={`button-expand-${alert.id}`}>
                  {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                </Button>
              </CollapsibleTrigger>
            </div>
          </div>

          <CollapsibleContent>
            <div className="mt-4 pt-4 border-t space-y-3">
              <div>
                <p className="text-sm font-medium mb-1">Metric Details</p>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-muted-foreground">Current:</span>{" "}
                    <span className="font-mono font-medium">{alert.currentValue?.toLocaleString() ?? "N/A"}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Previous:</span>{" "}
                    <span className="font-mono font-medium">{alert.previousValue?.toLocaleString() ?? "N/A"}</span>
                  </div>
                </div>
              </div>
              {alert.suggestedAction && (
                <div>
                  <p className="text-sm font-medium mb-1">Suggested Action</p>
                  <p className="text-sm text-muted-foreground">{alert.suggestedAction}</p>
                </div>
              )}
              <div className="flex items-center gap-2 flex-wrap">
                <Link href="/scenarios">
                  <Button size="sm" variant="outline" data-testid={`button-run-scenario-${alert.id}`}>
                    <FlaskConical className="h-4 w-4 mr-1" />
                    Run Scenario
                  </Button>
                </Link>
                <Link href="/truth">
                  <Button size="sm" variant="outline" data-testid={`button-view-details-${alert.id}`}>
                    <Eye className="h-4 w-4 mr-1" />
                    View Details
                  </Button>
                </Link>
              </div>
            </div>
          </CollapsibleContent>
        </CardContent>
      </Card>
    </Collapsible>
  );
}

function AlertSettingsSection({ companyId }: { companyId: number }) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [localRules, setLocalRules] = useState<AlertRule[]>(DEFAULT_ALERT_RULES);
  const { toast } = useToast();

  const { data: rules } = useQuery<AlertRule[]>({
    queryKey: ["/api/companies", companyId, "smart-alerts", "rules"],
    enabled: !!companyId,
  });

  const displayRules = rules && rules.length > 0 ? rules : localRules;

  const saveRulesMutation = useMutation({
    mutationFn: async (updatedRule: AlertRule) => {
      const res = await apiRequest("PUT", `/api/companies/${companyId}/smart-alerts/rules/${updatedRule.id}`, updatedRule);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/companies", companyId, "smart-alerts", "rules"] });
      toast({ title: "Rule Updated", description: "Alert rule has been saved." });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to save rule. Changes saved locally.", variant: "destructive" });
    },
  });

  const handleToggle = (id: string) => {
    const updated = displayRules.map(r => r.id === id ? { ...r, enabled: !r.enabled } : r);
    setLocalRules(updated);
    const rule = updated.find(r => r.id === id);
    if (rule) saveRulesMutation.mutate(rule);
  };

  const handleThresholdChange = (id: string, value: string) => {
    const numValue = parseFloat(value);
    if (!isNaN(numValue)) {
      const updated = displayRules.map(r => r.id === id ? { ...r, threshold: numValue } : r);
      setLocalRules(updated);
    }
  };

  const handleSaveThreshold = (id: string) => {
    const rule = localRules.find(r => r.id === id);
    if (rule) saveRulesMutation.mutate(rule);
  };

  return (
    <Collapsible open={settingsOpen} onOpenChange={setSettingsOpen}>
      <Card data-testid="card-alert-settings">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between gap-2">
            <div>
              <CardTitle className="text-lg">Alert Settings</CardTitle>
              <CardDescription>Configure alert rules and notification preferences</CardDescription>
            </div>
            <CollapsibleTrigger asChild>
              <Button size="icon" variant="ghost" data-testid="button-toggle-settings">
                {settingsOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </Button>
            </CollapsibleTrigger>
          </div>
        </CardHeader>
        <CollapsibleContent>
          <CardContent className="space-y-4">
            {displayRules.map((rule) => (
              <div
                key={rule.id}
                className={cn(
                  "flex items-center gap-4 p-3 rounded-lg border",
                  rule.enabled ? "bg-card" : "bg-muted/30"
                )}
                data-testid={`rule-${rule.id}`}
              >
                <Switch
                  checked={rule.enabled}
                  onCheckedChange={() => handleToggle(rule.id)}
                  data-testid={`switch-rule-${rule.id}`}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{rule.label}</p>
                  <p className="text-xs text-muted-foreground">{rule.description}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    value={rule.threshold}
                    onChange={(e) => handleThresholdChange(rule.id, e.target.value)}
                    onBlur={() => handleSaveThreshold(rule.id)}
                    className="w-20"
                    disabled={!rule.enabled}
                    data-testid={`input-rule-threshold-${rule.id}`}
                  />
                  <span className="text-xs text-muted-foreground">
                    {rule.type.includes("runway") ? "mo" : "%"}
                  </span>
                </div>
              </div>
            ))}
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}

function generateThresholdAlerts(metrics: ReturnType<typeof useFinancialMetrics>['metrics']): SmartAlert[] {
  const thresholdAlerts: SmartAlert[] = [];
  const now = new Date().toISOString();

  if (metrics.hasData && metrics.runway < 6 && metrics.runway > 0) {
    thresholdAlerts.push({
      id: 'threshold-runway-critical',
      type: 'runway_warning',
      severity: 'critical',
      title: 'Cash Runway Critical',
      message: `Only ${metrics.runway.toFixed(1)} months of runway remaining. Immediate fundraising or burn reduction required.`,
      metric: 'runway_months',
      currentValue: metrics.runway,
      previousValue: 0,
      changePercent: 0,
      timestamp: now,
      acknowledged: false,
      suggestedAction: 'Consider reducing burn rate or initiating fundraising conversations immediately.',
    });
  } else if (metrics.hasData && metrics.runway < 12 && metrics.runway > 0) {
    thresholdAlerts.push({
      id: 'threshold-runway-warning',
      type: 'runway_warning',
      severity: 'warning',
      title: 'Low Runway Warning',
      message: `${metrics.runway.toFixed(1)} months of runway remaining. Plan fundraising or reduce expenses.`,
      metric: 'runway_months',
      currentValue: metrics.runway,
      previousValue: 0,
      changePercent: 0,
      timestamp: now,
      acknowledged: false,
      suggestedAction: 'Start fundraising preparations or identify areas to reduce burn.',
    });
  }

  if (metrics.hasData && metrics.netBurn > 0 && metrics.mrr > 0 && metrics.netBurn > metrics.mrr * 3) {
    thresholdAlerts.push({
      id: 'threshold-burn-high',
      type: 'burn_spike',
      severity: 'warning',
      title: 'High Burn Rate',
      message: 'Monthly burn exceeds 3x MRR. Growth efficiency may be compromised.',
      metric: 'burn_rate',
      currentValue: metrics.netBurn,
      previousValue: metrics.mrr,
      changePercent: 0,
      timestamp: now,
      acknowledged: false,
      suggestedAction: 'Review expenses and identify areas to reduce burn relative to revenue.',
    });
  }

  if (metrics.hasData && metrics.cashOnHand > 0 && metrics.cashOnHand < 100000) {
    thresholdAlerts.push({
      id: 'threshold-cash-critical',
      type: 'cash_critical',
      severity: 'critical',
      title: 'Cash Balance Critical',
      message: `Cash reserves at $${(metrics.cashOnHand / 1000).toFixed(0)}K — dangerously low. Immediate fundraising required.`,
      metric: 'cash_balance',
      currentValue: metrics.cashOnHand,
      previousValue: 0,
      changePercent: 0,
      timestamp: now,
      acknowledged: false,
      suggestedAction: 'Seek emergency funding or drastically cut expenses.',
    });
  }

  if (metrics.hasData && metrics.churnRatePct > 10) {
    thresholdAlerts.push({
      id: 'threshold-churn-high',
      type: 'churn_spike',
      severity: 'warning',
      title: 'High Customer Churn',
      message: `Monthly churn rate at ${metrics.churnRatePct.toFixed(1)}%. This may threaten long-term growth.`,
      metric: 'churn_rate',
      currentValue: metrics.churnRatePct,
      previousValue: 0,
      changePercent: 0,
      timestamp: now,
      acknowledged: false,
      suggestedAction: 'Investigate churn drivers and implement retention strategies.',
    });
  }

  return thresholdAlerts;
}

export default function AlertsPage() {
  useSEO({
    title: "Smart Alerts — Real-time Startup Metrics Monitoring | FounderConsole",
    description: "Track anomalies, threshold breaches, and financial health drivers in real time. Z-score detection and severity-based filtering catch issues before they escalate.",
    path: "/alerts",
    robots: "noindex, nofollow",
  });
  const { currentCompany } = useFounderStore();
  const companyId = currentCompany?.id;
  const { toast } = useToast();
  const { metrics } = useFinancialMetrics();
  const hasAutoEvaluated = useRef(false);

  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [showAcknowledged, setShowAcknowledged] = useState(false);

  const { data: smartAlertsData, isLoading: smartAlertsLoading } = useQuery<AlertsResponse>({
    queryKey: ["/api/companies", companyId, "smart-alerts"],
    enabled: !!companyId,
  });

  const { data: oldAlertsData, isLoading: oldAlertsLoading } = useQuery<OldAlertsResponse>({
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

  const evaluateMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", `/api/companies/${companyId}/smart-alerts/evaluate`);
      return res.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["/api/companies", companyId, "smart-alerts"] });
      queryClient.invalidateQueries({ queryKey: ["/api/alerts/companies", companyId, "alerts"] });
      const newAlerts = data?.new_alerts ?? 0;
      toast({
        title: "Alert Check Complete",
        description: newAlerts > 0 ? `${newAlerts} new alert(s) detected.` : "No new alerts found.",
      });
    },
    onError: () => {
      toast({ title: "Check Failed", description: "Could not evaluate alerts. Try again.", variant: "destructive" });
    },
  });

  const acknowledgeMutation = useMutation({
    mutationFn: async (alertId: string) => {
      const res = await apiRequest("PUT", `/api/companies/${companyId}/smart-alerts/${alertId}/acknowledge`);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/companies", companyId, "smart-alerts"] });
      toast({ title: "Alert Acknowledged" });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to acknowledge alert.", variant: "destructive" });
    },
  });

  const weeklyBriefingMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", `/api/companies/${companyId}/smart-alerts/weekly-briefing`);
      return res.json();
    },
    onSuccess: () => {
      toast({ title: "Weekly Briefing Sent", description: "Check your email for the briefing." });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to send weekly briefing.", variant: "destructive" });
    },
  });

  const thresholdAlerts = generateThresholdAlerts(metrics);

  useEffect(() => {
    if (companyId && !hasAutoEvaluated.current && !smartAlertsLoading && metrics.hasData) {
      hasAutoEvaluated.current = true;
      evaluateMutation.mutate();
    }
  }, [companyId, smartAlertsLoading, metrics.hasData]);

  const smartAlerts = smartAlertsData?.alerts ?? [];
  const smartAlertIds = new Set(smartAlerts.map(a => a.type));
  const uniqueThresholdAlerts = thresholdAlerts.filter(ta => !smartAlertIds.has(ta.type));
  const alerts = [...smartAlerts, ...uniqueThresholdAlerts];
  const isLoading = smartAlertsLoading || oldAlertsLoading;

  const filteredAlerts = alerts.filter((alert) => {
    if (severityFilter !== "all" && alert.severity !== severityFilter) return false;
    if (typeFilter !== "all" && alert.type !== typeFilter) return false;
    if (!showAcknowledged && alert.acknowledged) return false;
    return true;
  });

  const alertTypes = Array.from(new Set(alerts.map((a) => a.type)));
  const unacknowledgedCount = alerts.filter(a => !a.acknowledged).length;
  const criticalCount = alerts.filter(a => a.severity === "critical" && !a.acknowledged).length;
  const warningCount = alerts.filter(a => a.severity === "warning" && !a.acknowledged).length;

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
          <Button
            onClick={() => evaluateMutation.mutate()}
            disabled={evaluateMutation.isPending || !companyId}
            data-testid="button-check-now"
          >
            {evaluateMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Zap className="h-4 w-4 mr-2" />
            )}
            Check Now
          </Button>
          <Button
            variant="outline"
            onClick={() => weeklyBriefingMutation.mutate()}
            disabled={weeklyBriefingMutation.isPending || !companyId}
            data-testid="button-send-briefing"
          >
            {weeklyBriefingMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Mail className="h-4 w-4 mr-2" />
            )}
            Send Weekly Briefing
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              queryClient.invalidateQueries({ queryKey: ["/api/companies", companyId, "smart-alerts"] });
              queryClient.invalidateQueries({ queryKey: ["/api/alerts/companies", companyId, "alerts"] });
              queryClient.invalidateQueries({ queryKey: ["/api/alerts/companies", companyId, "analyze"] });
            }}
            data-testid="button-refresh"
          >
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
                <p className="text-sm text-muted-foreground">Unread Alerts</p>
                <p className="text-2xl font-bold" data-testid="text-total-alerts">
                  {unacknowledgedCount}
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
                  {criticalCount}
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
                  {warningCount}
                </p>
              </div>
              <AlertTriangle className="h-8 w-8 text-yellow-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="alerts">
        <TabsList data-testid="tabs-view">
          <TabsTrigger value="alerts" data-testid="tab-alerts">
            Active Alerts
            {unacknowledgedCount > 0 && (
              <Badge variant="destructive" className="ml-2 text-[10px] px-1.5 py-0 h-4 border-0">
                {unacknowledgedCount}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="health" data-testid="tab-health">Health Dashboard</TabsTrigger>
          <TabsTrigger value="drivers" data-testid="tab-drivers">Driver Details</TabsTrigger>
          <TabsTrigger value="settings" data-testid="tab-settings">Settings</TabsTrigger>
          <TabsTrigger value="recommendations" data-testid="tab-recommendations">Recommendations</TabsTrigger>
        </TabsList>

        <TabsContent value="alerts" className="space-y-4">
          <Card>
            <CardContent className="py-3">
              <div className="flex items-center gap-3 flex-wrap">
                <Select value={severityFilter} onValueChange={setSeverityFilter}>
                  <SelectTrigger className="w-[150px]" data-testid="select-severity-filter">
                    <SelectValue placeholder="Severity" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Severities</SelectItem>
                    <SelectItem value="critical">Critical</SelectItem>
                    <SelectItem value="warning">Warning</SelectItem>
                    <SelectItem value="info">Info</SelectItem>
                    <SelectItem value="success">Success</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={typeFilter} onValueChange={setTypeFilter}>
                  <SelectTrigger className="w-[170px]" data-testid="select-type-filter">
                    <SelectValue placeholder="Type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Types</SelectItem>
                    {alertTypes.map((type) => (
                      <SelectItem key={type} value={type}>
                        {type.replace(/_/g, " ")}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <div className="flex items-center gap-2">
                  <Switch
                    checked={showAcknowledged}
                    onCheckedChange={setShowAcknowledged}
                    data-testid="switch-show-acknowledged"
                  />
                  <span className="text-sm text-muted-foreground">Show acknowledged</span>
                </div>

                <span className="text-sm text-muted-foreground ml-auto">
                  {filteredAlerts.length} alert{filteredAlerts.length !== 1 ? "s" : ""}
                </span>
              </div>
            </CardContent>
          </Card>

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
          ) : filteredAlerts.length > 0 ? (
            <div className="space-y-3">
              {filteredAlerts.map((alert) => (
                <AlertCard
                  key={alert.id}
                  alert={alert}
                  companyId={companyId!}
                  onAcknowledge={(id) => acknowledgeMutation.mutate(id)}
                />
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
                    : alerts.length > 0 && filteredAlerts.length === 0
                    ? "No alerts match the current filters."
                    : "All metrics are within normal ranges. Click 'Check Now' to evaluate."}
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

        <TabsContent value="health" className="space-y-4">
          <HealthDashboard drivers={healthData?.drivers || {}} />
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

        <TabsContent value="settings" className="space-y-4">
          {companyId && <AlertSettingsSection companyId={companyId} />}
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
