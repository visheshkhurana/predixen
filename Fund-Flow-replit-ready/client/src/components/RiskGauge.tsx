import { cn } from '@/lib/utils';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Info } from 'lucide-react';

interface RiskGaugeProps {
  survivalProbability: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  showPercentage?: boolean;
  testId?: string;
}

export function RiskGauge({
  survivalProbability,
  size = 'md',
  showLabel = true,
  showPercentage = true,
  testId = 'risk-gauge',
}: RiskGaugeProps) {
  const percentage = Math.round(survivalProbability * 100);
  
  const getRiskLevel = () => {
    if (percentage >= 80) return { level: 'low', label: 'Low Risk', color: 'emerald' };
    if (percentage >= 50) return { level: 'moderate', label: 'Moderate Risk', color: 'amber' };
    return { level: 'high', label: 'High Risk', color: 'red' };
  };
  
  const risk = getRiskLevel();
  
  const sizeClasses = {
    sm: { gauge: 'h-2', text: 'text-xs', container: 'gap-1' },
    md: { gauge: 'h-3', text: 'text-sm', container: 'gap-2' },
    lg: { gauge: 'h-4', text: 'text-base', container: 'gap-3' },
  };
  
  const colorClasses = {
    emerald: {
      fill: 'bg-emerald-500',
      bg: 'bg-emerald-500/20',
      text: 'text-emerald-600 dark:text-emerald-400',
    },
    amber: {
      fill: 'bg-amber-500',
      bg: 'bg-amber-500/20',
      text: 'text-amber-600 dark:text-amber-400',
    },
    red: {
      fill: 'bg-red-500',
      bg: 'bg-red-500/20',
      text: 'text-red-600 dark:text-red-400',
    },
  };
  
  const colors = colorClasses[risk.color as keyof typeof colorClasses];
  const sizes = sizeClasses[size];
  
  return (
    <div className={cn('flex flex-col', sizes.container)} data-testid={testId}>
      {(showLabel || showPercentage) && (
        <div className="flex items-center justify-between gap-2">
          {showLabel && (
            <div className="flex items-center gap-1.5">
              <span className={cn('font-medium', sizes.text, colors.text)}>
                {risk.label}
              </span>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button type="button" className="inline-flex">
                    <Info className="h-3.5 w-3.5 text-muted-foreground" />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-xs">
                  <p className="text-sm">
                    {risk.level === 'low' && 'High probability of survival. Your runway looks healthy.'}
                    {risk.level === 'moderate' && 'Moderate risk. Consider optimizing costs or accelerating revenue.'}
                    {risk.level === 'high' && 'High risk of running out of cash. Immediate action recommended.'}
                  </p>
                </TooltipContent>
              </Tooltip>
            </div>
          )}
          {showPercentage && (
            <span className={cn('font-mono font-semibold', sizes.text, colors.text)}>
              {percentage}%
            </span>
          )}
        </div>
      )}
      
      <div className={cn('relative w-full rounded-full overflow-hidden', sizes.gauge, colors.bg)}>
        <div
          className={cn('absolute left-0 top-0 h-full rounded-full transition-all duration-500', colors.fill)}
          style={{ width: `${percentage}%` }}
        />
        <div className="absolute inset-0 flex">
          <div className="flex-1 border-r border-white/30" />
          <div className="flex-1 border-r border-white/30" />
          <div className="flex-1" />
        </div>
      </div>
      
      {size !== 'sm' && (
        <div className="flex justify-between text-[10px] text-muted-foreground">
          <span>0%</span>
          <span>50%</span>
          <span>80%</span>
          <span>100%</span>
        </div>
      )}
    </div>
  );
}

interface TrafficLightProps {
  survivalProbability: number;
  showLabel?: boolean;
  testId?: string;
}

export function TrafficLight({
  survivalProbability,
  showLabel = true,
  testId = 'traffic-light',
}: TrafficLightProps) {
  const percentage = Math.round(survivalProbability * 100);
  
  const isHigh = percentage >= 80;
  const isMedium = percentage >= 50 && percentage < 80;
  const isLow = percentage < 50;
  
  const getLabel = () => {
    if (isHigh) return 'Low Risk';
    if (isMedium) return 'Moderate Risk';
    return 'High Risk';
  };
  
  return (
    <div className="flex items-center gap-2" data-testid={testId}>
      <div className="flex gap-1">
        <div className={cn(
          'w-4 h-4 rounded-full border-2',
          isLow ? 'bg-red-500 border-red-600' : 'bg-muted border-muted-foreground/20'
        )} />
        <div className={cn(
          'w-4 h-4 rounded-full border-2',
          isMedium ? 'bg-amber-500 border-amber-600' : 'bg-muted border-muted-foreground/20'
        )} />
        <div className={cn(
          'w-4 h-4 rounded-full border-2',
          isHigh ? 'bg-emerald-500 border-emerald-600' : 'bg-muted border-muted-foreground/20'
        )} />
      </div>
      {showLabel && (
        <span className={cn(
          'text-sm font-medium',
          isHigh && 'text-emerald-600 dark:text-emerald-400',
          isMedium && 'text-amber-600 dark:text-amber-400',
          isLow && 'text-red-600 dark:text-red-400'
        )}>
          {getLabel()} ({percentage}%)
        </span>
      )}
    </div>
  );
}
