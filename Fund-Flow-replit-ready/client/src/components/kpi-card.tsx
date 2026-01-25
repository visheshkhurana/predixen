import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

interface KPICardProps {
  title: string;
  value: string;
  subtitle?: string;
  trend?: "up" | "down" | "stable";
  trendLabel?: string;
  icon?: React.ReactNode;
  variant?: "default" | "warning" | "danger" | "success";
  testId?: string;
}

export function KPICard({
  title,
  value,
  subtitle,
  trend,
  trendLabel,
  icon,
  variant = "default",
  testId = "kpi-card",
}: KPICardProps) {
  const getTrendIcon = () => {
    if (!trend) return null;
    switch (trend) {
      case "up":
        return <TrendingUp className="h-3 w-3" />;
      case "down":
        return <TrendingDown className="h-3 w-3" />;
      case "stable":
        return <Minus className="h-3 w-3" />;
    }
  };

  const getTrendColor = () => {
    if (!trend) return "";
    switch (trend) {
      case "up":
        return "text-emerald-600 dark:text-emerald-400";
      case "down":
        return "text-red-500 dark:text-red-400";
      case "stable":
        return "text-muted-foreground";
    }
  };

  const getVariantBadge = () => {
    switch (variant) {
      case "warning":
        return (
          <Badge variant="secondary" className="bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400 text-xs">
            Caution
          </Badge>
        );
      case "danger":
        return (
          <Badge variant="destructive" className="text-xs">
            Critical
          </Badge>
        );
      case "success":
        return (
          <Badge variant="secondary" className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400 text-xs">
            Healthy
          </Badge>
        );
      default:
        return null;
    }
  };

  return (
    <Card className="overflow-visible" data-testid={testId}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <span className="text-sm font-medium text-muted-foreground">{title}</span>
          <div className="flex items-center gap-2">
            {getVariantBadge()}
            {icon && <span className="text-muted-foreground">{icon}</span>}
          </div>
        </div>
        <div className="mt-2">
          <span className="text-2xl font-semibold font-mono tracking-tight" data-testid={`${testId}-value`}>
            {value}
          </span>
          {subtitle && (
            <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
          )}
        </div>
        {trend && trendLabel && (
          <div className={cn("flex items-center gap-1 mt-2 text-xs", getTrendColor())}>
            {getTrendIcon()}
            <span>{trendLabel}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
