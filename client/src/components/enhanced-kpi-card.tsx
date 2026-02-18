import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { TrendingUp, TrendingDown, Minus, AlertTriangle, Info, Calculator, Database } from "lucide-react";
import { cn, formatCurrencyAbbrev } from "@/lib/utils";
import { Area, AreaChart, ResponsiveContainer, Tooltip as RechartsTooltip } from "recharts";
import type { KPITimeSeries } from "@shared/schema";

interface MetricDefinition {
  name: string;
  formula: string;
  description: string;
  unit: string;
  data_sources: string[];
}

interface EnhancedKPICardProps {
  data: KPITimeSeries & { definition?: MetricDefinition };
  title: string;
  format?: "currency" | "percent" | "months" | "number" | "multiple";
  icon?: React.ReactNode;
  highlighted?: boolean;
  onClick?: () => void;
  testId?: string;
  currency?: string;
}

export function EnhancedKPICard({
  data,
  title,
  format = "number",
  icon,
  highlighted = false,
  onClick,
  testId = "enhanced-kpi-card",
  currency = "USD",
}: EnhancedKPICardProps) {
  const formatValue = (value: number | null): string => {
    if (value === null || value === undefined) return "N/A";
    switch (format) {
      case "currency":
        return formatCurrencyAbbrev(value, currency);
      case "percent": {
        const p = value.toFixed(1);
        return `${p.replace(/\.0$/, '')}%`;
      }
      case "months": {
        const m = value.toFixed(1);
        return `${m.replace(/\.0$/, '')} mo`;
      }
      case "multiple": {
        const x = value.toFixed(1);
        return `${x.replace(/\.0$/, '')}x`;
      }
      default:
        return value.toLocaleString();
    }
  };

  const getTrendIcon = () => {
    switch (data.trend) {
      case "up":
        return <TrendingUp className="h-3 w-3" />;
      case "down":
        return <TrendingDown className="h-3 w-3" />;
      default:
        return <Minus className="h-3 w-3" />;
    }
  };

  const getTrendColor = () => {
    const isPositiveTrendGood = !["netBurn", "burnMultiple"].includes(data.metricName);
    if (data.trend === "stable") return "text-muted-foreground";
    if (data.trend === "up") {
      return isPositiveTrendGood ? "text-emerald-600 dark:text-emerald-400" : "text-red-500 dark:text-red-400";
    }
    return isPositiveTrendGood ? "text-red-500 dark:text-red-400" : "text-emerald-600 dark:text-emerald-400";
  };

  const getSparklineColor = () => {
    if (data.status === "critical") return "hsl(var(--destructive))";
    if (data.status === "warning") return "hsl(38, 92%, 50%)";
    return "hsl(var(--primary))";
  };

  const getStatusBadge = () => {
    switch (data.status) {
      case "critical":
        return (
          <Badge variant="destructive" className="text-xs">
            Critical
          </Badge>
        );
      case "warning":
        return (
          <Badge variant="secondary" className="bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400 text-xs">
            Caution
          </Badge>
        );
      case "missing":
        return (
          <Tooltip>
            <TooltipTrigger asChild>
              <Badge variant="secondary" className="text-xs cursor-help">
                <AlertTriangle className="h-3 w-3 mr-1" />
                Data needed
              </Badge>
            </TooltipTrigger>
            <TooltipContent>
              <p>This metric requires additional data input to calculate accurately.</p>
            </TooltipContent>
          </Tooltip>
        );
      case "healthy":
        return (
          <Badge variant="secondary" className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400 text-xs">
            Healthy
          </Badge>
        );
      default:
        return null;
    }
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-popover border rounded-md p-2 shadow-md text-xs">
          <p className="text-muted-foreground">{payload[0].payload.date}</p>
          <p className="font-medium">{formatValue(payload[0].value)}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card
      className={cn(
        "overflow-visible transition-all",
        highlighted && "ring-2 ring-primary shadow-lg",
        onClick && "cursor-pointer hover-elevate"
      )}
      onClick={onClick}
      data-testid={testId}
    >
      <CardContent className={cn("p-4", highlighted && "p-6")}>
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2">
            {icon && <span className="text-muted-foreground">{icon}</span>}
            <span className={cn("font-medium text-muted-foreground", highlighted ? "text-base" : "text-sm")}>
              {title}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {getStatusBadge()}
            {data.definition ? (
              <Dialog>
                <DialogTrigger asChild>
                  <span 
                    className="text-muted-foreground cursor-pointer hover:text-foreground transition-colors"
                    data-testid={`${testId}-info-trigger`}
                  >
                    <Info className="h-3 w-3" />
                  </span>
                </DialogTrigger>
                <DialogContent className="max-w-md">
                  <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                      <Calculator className="h-5 w-5" />
                      {data.definition.name}
                    </DialogTitle>
                    <DialogDescription>{data.definition.description}</DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div>
                      <h4 className="text-sm font-medium mb-2">Formula</h4>
                      <code className="block p-3 bg-muted rounded-md text-sm font-mono">
                        {data.definition.formula}
                      </code>
                    </div>
                    <div>
                      <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                        <Database className="h-4 w-4" />
                        Data Sources
                      </h4>
                      <ul className="text-sm text-muted-foreground space-y-1">
                        {data.definition.data_sources.map((source, idx) => (
                          <li key={idx} className="flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                            {source}
                          </li>
                        ))}
                      </ul>
                    </div>
                    {data.benchmark !== null && data.benchmark !== undefined && (
                      <div>
                        <h4 className="text-sm font-medium mb-2">Benchmark</h4>
                        <p className="text-sm text-muted-foreground">
                          {data.benchmarkLabel || "Target"}: <span className="font-medium">{formatValue(data.benchmark)}</span>
                        </p>
                      </div>
                    )}
                  </div>
                </DialogContent>
              </Dialog>
            ) : data.benchmark !== null && data.benchmark !== undefined ? (
              <Tooltip>
                <TooltipTrigger asChild>
                  <span 
                    className="text-muted-foreground cursor-help"
                    data-testid={`${testId}-benchmark-trigger`}
                  >
                    <Info className="h-3 w-3" />
                  </span>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{data.benchmarkLabel || "Benchmark"}: {formatValue(data.benchmark)}</p>
                </TooltipContent>
              </Tooltip>
            ) : null}
          </div>
        </div>

        <div className="mt-2">
          <span
            className={cn(
              "font-semibold font-mono tracking-tight",
              highlighted ? "text-4xl" : "text-2xl",
              data.status === "missing" && "text-muted-foreground"
            )}
            data-testid={`${testId}-value`}
          >
            {formatValue(data.currentValue)}
          </span>
        </div>

        {data.changePercent !== null && (
          <div className={cn("flex items-center gap-1 mt-1 text-xs", getTrendColor())}>
            {getTrendIcon()}
            <span>{data.changePercent > 0 ? "+" : ""}{data.changePercent.toFixed(1)}% vs last month</span>
          </div>
        )}

        {data.history && data.history.length > 1 && (
          <div className="mt-3 h-12">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.history} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id={`gradient-${data.metricName}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={getSparklineColor()} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={getSparklineColor()} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <RechartsTooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke={getSparklineColor()}
                  strokeWidth={2}
                  fill={`url(#gradient-${data.metricName})`}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
