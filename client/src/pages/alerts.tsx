import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { 
  AlertTriangle, 
  AlertCircle, 
  Info, 
  CheckCircle, 
  TrendingUp, 
  TrendingDown,
  Activity,
  RefreshCw
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

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
}

interface AlertsResponse {
  alerts: Alert[];
  health: Record<string, DriverHealth>;
  total_alerts: number;
  critical_count: number;
  warning_count: number;
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

const statusColors = {
  healthy: "text-green-500",
  warning: "text-yellow-500",
  critical: "text-red-500",
  unknown: "text-muted-foreground",
};

export default function AlertsPage() {
  const [companyId] = useState(1);

  const { data: alertsData, isLoading, refetch } = useQuery<AlertsResponse>({
    queryKey: ["/api/alerts/companies", companyId, "alerts"],
  });

  const { data: healthData } = useQuery<{
    overall_status: string;
    drivers: Record<string, DriverHealth>;
    recommendations: string[];
  }>({
    queryKey: ["/api/alerts/companies", companyId, "analyze"],
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
      default:
        return <Badge variant="secondary">Unknown</Badge>;
    }
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" data-testid="text-page-title">Alerts & Monitoring</h1>
          <p className="text-muted-foreground">
            Track anomalies, threshold breaches, and driver health
          </p>
        </div>
        <Button variant="outline" onClick={() => refetch()} data-testid="button-refresh">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="grid md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
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
            <div className="flex items-center justify-between">
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
            <div className="flex items-center justify-between">
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
            <div className="flex items-center justify-between">
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

      <Tabs defaultValue="alerts">
        <TabsList data-testid="tabs-view">
          <TabsTrigger value="alerts" data-testid="tab-alerts">Active Alerts</TabsTrigger>
          <TabsTrigger value="health" data-testid="tab-health">Driver Health</TabsTrigger>
          <TabsTrigger value="recommendations" data-testid="tab-recommendations">Recommendations</TabsTrigger>
        </TabsList>

        <TabsContent value="alerts" className="space-y-4">
          {isLoading ? (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                Loading alerts...
              </CardContent>
            </Card>
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
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant="outline" className="text-xs">
                            {alert.type.replace(/_/g, " ")}
                          </Badge>
                          <Badge variant="secondary" className="text-xs">
                            {alert.metric}
                          </Badge>
                        </div>
                        <p className="font-medium">{alert.message}</p>
                        <p className="text-sm text-muted-foreground mt-1">
                          {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}
                        </p>
                      </div>
                      <Button size="sm" variant="ghost">
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
                  All metrics are within normal ranges
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="health" className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            {healthData?.drivers && Object.entries(healthData.drivers).map(([name, health]) => (
              <Card key={name} data-testid={`card-driver-${name}`}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg capitalize">{name.replace(/_/g, " ")}</CardTitle>
                    <Badge
                      variant="outline"
                      className={
                        health.status === "healthy"
                          ? "bg-green-500/10 text-green-500"
                          : health.status === "warning"
                          ? "bg-yellow-500/10 text-yellow-500"
                          : "bg-red-500/10 text-red-500"
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
                      <Info className="h-5 w-5 text-primary mt-0.5" />
                      <p>{rec}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted-foreground text-center py-8">
                  No recommendations available
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
