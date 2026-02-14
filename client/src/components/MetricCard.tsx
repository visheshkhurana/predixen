import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { TrendingUp, TrendingDown, Minus, Info, Database, Calculator, Clock, GitBranch } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Sparkline } from './Sparkline';
import { formatDistanceToNow } from 'date-fns';

export interface MetricProvenance {
  definition: string;
  formula?: string;
  source: 'truth_scan' | 'simulation' | 'manual' | 'computed' | 'imported';
  sourceLabel?: string;
  timestamp?: string;
  runId?: string;
  confidence?: number;
}

const sourceConfig = {
  truth_scan: { label: 'Truth Scan', color: 'text-emerald-400', bgColor: 'bg-emerald-500/10' },
  simulation: { label: 'Simulation', color: 'text-blue-400', bgColor: 'bg-blue-500/10' },
  manual: { label: 'Manual Entry', color: 'text-amber-400', bgColor: 'bg-amber-500/10' },
  computed: { label: 'Computed', color: 'text-purple-400', bgColor: 'bg-purple-500/10' },
  imported: { label: 'Imported', color: 'text-cyan-400', bgColor: 'bg-cyan-500/10' },
};

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: string;
  trendData?: number[];
  benchmark?: {
    position: 'above_p75' | 'above_p50' | 'above_p25' | 'below_p25';
    direction: 'higher_is_better' | 'lower_is_better';
  };
  variant?: 'default' | 'warning' | 'danger' | 'success';
  metricSource?: 'reported' | 'computed' | 'estimated';
  lastUpdated?: string;
  testId?: string;
  tooltip?: string;
  provenance?: MetricProvenance;
  onClick?: () => void;
}

const metricSourceConfig = {
  estimated: { label: 'AI Estimated', className: 'bg-amber-500/20 text-amber-400' },
  computed: { label: 'Computed', className: 'bg-purple-500/20 text-purple-400' },
  reported: { label: 'Verified', className: 'bg-emerald-500/20 text-emerald-400' },
};

export function MetricCard({
  title,
  value,
  subtitle,
  trend,
  trendValue,
  trendData,
  benchmark,
  variant = 'default',
  metricSource,
  lastUpdated,
  testId = 'metric-card',
  tooltip,
  provenance,
  onClick,
}: MetricCardProps) {
  const getTrendIcon = () => {
    if (!trend) return null;
    switch (trend) {
      case 'up':
        return <TrendingUp className="h-3 w-3" />;
      case 'down':
        return <TrendingDown className="h-3 w-3" />;
      case 'stable':
        return <Minus className="h-3 w-3" />;
    }
  };

  const getTrendColor = () => {
    if (!trend) return '';
    switch (trend) {
      case 'up':
        return 'text-emerald-500';
      case 'down':
        return 'text-red-500';
      case 'stable':
        return 'text-muted-foreground';
    }
  };

  const getBenchmarkBadge = () => {
    if (!benchmark) return null;
    
    const isGood =
      (benchmark.direction === 'higher_is_better' && benchmark.position.startsWith('above')) ||
      (benchmark.direction === 'lower_is_better' && benchmark.position === 'below_p25');
    
    const labels: Record<string, string> = {
      above_p75: 'Top Quartile',
      above_p50: 'Above Median',
      above_p25: 'Above P25',
      below_p25: 'Below P25',
    };
    
    return (
      <Badge
        variant="secondary"
        className={cn(
          'text-xs',
          isGood
            ? 'bg-emerald-500/20 text-emerald-400'
            : 'bg-amber-500/20 text-amber-400'
        )}
      >
        {labels[benchmark.position]}
      </Badge>
    );
  };

  const getVariantBadge = () => {
    switch (variant) {
      case 'warning':
        return (
          <Badge variant="secondary" className="bg-amber-500/20 text-amber-400 text-xs">
            Caution
          </Badge>
        );
      case 'danger':
        return (
          <Badge variant="destructive" className="text-xs">
            Critical
          </Badge>
        );
      case 'success':
        return (
          <Badge variant="secondary" className="bg-emerald-500/20 text-emerald-400 text-xs">
            Healthy
          </Badge>
        );
      default:
        return null;
    }
  };

  return (
    <Card 
      className={cn('overflow-visible', onClick && 'cursor-pointer hover-elevate')} 
      data-testid={testId}
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-medium text-muted-foreground">{title}</span>
            {(tooltip || provenance) && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    className="inline-flex items-center justify-center rounded-full p-0.5"
                    onClick={(e) => e.stopPropagation()}
                    data-testid={`${testId}-tooltip`}
                  >
                    <Info className="h-3.5 w-3.5 text-muted-foreground" />
                  </button>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs p-3" side="top">
                  {provenance ? (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-sm">{title}</span>
                        <Badge 
                          variant="outline" 
                          className={cn(
                            "text-[10px] px-1.5 py-0",
                            sourceConfig[provenance.source].bgColor,
                            sourceConfig[provenance.source].color
                          )}
                        >
                          {provenance.sourceLabel || sourceConfig[provenance.source].label}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">{provenance.definition}</p>
                      {provenance.formula && (
                        <div className="flex items-start gap-1.5 text-xs">
                          <Calculator className="h-3 w-3 mt-0.5 text-muted-foreground shrink-0" />
                          <code className="font-mono text-[10px] bg-muted px-1 py-0.5 rounded break-all">
                            {provenance.formula}
                          </code>
                        </div>
                      )}
                      <div className="flex items-center gap-3 text-[10px] text-muted-foreground pt-1 border-t border-border/50">
                        <div className="flex items-center gap-1">
                          <Database className={cn("h-3 w-3", sourceConfig[provenance.source].color)} />
                          <span>{provenance.sourceLabel || sourceConfig[provenance.source].label}</span>
                        </div>
                        {provenance.timestamp && (
                          <div className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            <span>{formatDistanceToNow(new Date(provenance.timestamp), { addSuffix: true })}</span>
                          </div>
                        )}
                        {provenance.runId && (
                          <div className="flex items-center gap-1">
                            <GitBranch className="h-3 w-3" />
                            <span className="font-mono">{provenance.runId.slice(0, 8)}</span>
                          </div>
                        )}
                      </div>
                      {provenance.confidence !== undefined && (
                        <div className="text-[10px] text-muted-foreground">
                          Confidence: {provenance.confidence}%
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm">{tooltip}</p>
                  )}
                </TooltipContent>
              </Tooltip>
            )}
          </div>
          <div className="flex items-center gap-2">
            {metricSource && (
              <Badge
                variant="secondary"
                className={cn('text-xs', metricSourceConfig[metricSource].className)}
                data-testid={`${testId}-source-badge`}
              >
                {metricSourceConfig[metricSource].label}
              </Badge>
            )}
            {getVariantBadge()}
            {getBenchmarkBadge()}
          </div>
        </div>
        <div className="mt-2 flex items-end justify-between gap-2">
          <div>
            <span
              className="text-2xl font-semibold font-mono tracking-tight"
              data-testid={`${testId}-value`}
            >
              {value}
            </span>
            {subtitle && (
              <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
            )}
            {lastUpdated && (
              <p className="text-[10px] text-muted-foreground/70 mt-0.5" data-testid={`${testId}-last-updated`}>
                Updated {formatDistanceToNow(new Date(lastUpdated), { addSuffix: true })}
              </p>
            )}
          </div>
          {trendData && trendData.length > 1 && (
            <div className="flex-shrink-0" data-testid={`${testId}-sparkline`}>
              <Sparkline data={trendData} width={50} height={24} />
            </div>
          )}
        </div>
        {trend && trendValue && (
          <div className={cn('flex items-center gap-1 mt-2 text-xs', getTrendColor())}>
            {getTrendIcon()}
            <span>{trendValue}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
