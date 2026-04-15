import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { TrendingUp, TrendingDown, Minus, Info, Database, Calculator, Clock, GitBranch } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Sparkline } from './Sparkline';
import { formatDistanceToNow } from 'date-fns';
import { motion, useReducedMotion } from 'framer-motion';

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

const variantAccent = {
  default: 'from-white/[0.03] to-transparent',
  warning: 'from-amber-500/[0.06] to-transparent',
  danger: 'from-red-500/[0.06] to-transparent',
  success: 'from-emerald-500/[0.06] to-transparent',
};

const variantBorder = {
  default: 'border-white/[0.06]',
  warning: 'border-amber-500/20',
  danger: 'border-red-500/20',
  success: 'border-emerald-500/20',
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
  const prefersReducedMotion = useReducedMotion();

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
        return 'text-emerald-400';
      case 'down':
        return 'text-red-400';
      case 'stable':
        return 'text-muted-foreground';
    }
  };

  const Wrapper = prefersReducedMotion ? 'div' : motion.div;
  const wrapperProps = prefersReducedMotion ? {} : {
    whileHover: { y: -2, transition: { type: 'spring', stiffness: 400, damping: 25 } },
    whileTap: { scale: 0.98 },
  };

  return (
    <Wrapper
      {...wrapperProps}
      className={cn(
        'group relative rounded-xl border p-5 transition-all duration-300',
        'bg-gradient-to-b backdrop-blur-xl',
        variantAccent[variant],
        variantBorder[variant],
        'hover:border-white/[0.12] hover:shadow-lg hover:shadow-black/10',
        onClick && 'cursor-pointer',
      )}
      data-testid={testId}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-xs font-medium text-muted-foreground/80 uppercase tracking-wider truncate">{title}</span>
          {(tooltip || provenance) && (
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  className="inline-flex items-center justify-center rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={(e) => e.stopPropagation()}
                  data-testid={`${testId}-tooltip`}
                >
                  <Info className="h-3 w-3 text-muted-foreground/60" />
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
        {metricSource && metricSource !== 'reported' && (
          <Badge
            variant="secondary"
            className={cn('text-[10px] px-1.5 py-0 h-4 shrink-0 opacity-60 group-hover:opacity-100 transition-opacity', metricSourceConfig[metricSource].className)}
            data-testid={`${testId}-source-badge`}
          >
            {metricSourceConfig[metricSource].label}
          </Badge>
        )}
      </div>

      <div className="flex items-end justify-between gap-3">
        <div className="min-w-0">
          <span
            className="text-2xl font-semibold font-mono tracking-tight leading-none"
            data-testid={`${testId}-value`}
          >
            {value}
          </span>
          {subtitle && (
            <p className="text-[11px] text-muted-foreground/70 mt-1.5 truncate">{subtitle}</p>
          )}
        </div>
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          {trendData && trendData.length > 1 && (
            <div data-testid={`${testId}-sparkline`}>
              <Sparkline data={trendData} width={48} height={20} />
            </div>
          )}
          {trend && trendValue && (
            <div className={cn('flex items-center gap-0.5 text-[11px] font-medium', getTrendColor())}>
              {getTrendIcon()}
              <span>{trendValue}</span>
            </div>
          )}
        </div>
      </div>

      {lastUpdated && (
        <p className="text-[9px] text-muted-foreground/40 mt-2 font-mono" data-testid={`${testId}-last-updated`}>
          {formatDistanceToNow(new Date(lastUpdated), { addSuffix: true })}
        </p>
      )}
    </Wrapper>
  );
}
