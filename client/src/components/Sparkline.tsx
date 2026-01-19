import { useMemo } from 'react';
import { cn } from '@/lib/utils';

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  strokeWidth?: number;
  color?: string;
  showDot?: boolean;
  className?: string;
}

export function Sparkline({
  data,
  width = 60,
  height = 20,
  strokeWidth = 1.5,
  color,
  showDot = true,
  className,
}: SparklineProps) {
  const { path, lastPoint, trend } = useMemo(() => {
    if (!data || data.length < 2) {
      return { path: '', lastPoint: null, trend: 'neutral' as const };
    }

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    
    const padding = 2;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;
    
    const points = data.map((value, index) => ({
      x: padding + (index / (data.length - 1)) * chartWidth,
      y: padding + chartHeight - ((value - min) / range) * chartHeight,
    }));

    const pathStr = points
      .map((point, i) => `${i === 0 ? 'M' : 'L'} ${point.x} ${point.y}`)
      .join(' ');

    const lastVal = data[data.length - 1];
    const firstVal = data[0];
    const trendDirection = lastVal > firstVal ? 'up' : lastVal < firstVal ? 'down' : 'neutral';

    return {
      path: pathStr,
      lastPoint: points[points.length - 1],
      trend: trendDirection,
    };
  }, [data, width, height]);

  if (!data || data.length < 2) {
    return (
      <div 
        className={cn("flex items-center justify-center text-muted-foreground/50", className)}
        style={{ width, height }}
      >
        <span className="text-[8px]">No trend</span>
      </div>
    );
  }

  const strokeColor = color || (trend === 'up' ? '#10b981' : trend === 'down' ? '#ef4444' : '#6b7280');

  return (
    <svg
      width={width}
      height={height}
      className={className}
      viewBox={`0 0 ${width} ${height}`}
    >
      <path
        d={path}
        fill="none"
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {showDot && lastPoint && (
        <circle
          cx={lastPoint.x}
          cy={lastPoint.y}
          r={2.5}
          fill={strokeColor}
        />
      )}
    </svg>
  );
}

export function generateMockTrendData(baseValue: number, months: number = 6, volatility: number = 0.1): number[] {
  const data: number[] = [baseValue];
  for (let i = 1; i < months; i++) {
    const change = (Math.random() - 0.5) * 2 * volatility * baseValue;
    const trend = (Math.random() - 0.4) * 0.05 * baseValue;
    data.push(Math.max(0, data[i - 1] + change + trend));
  }
  return data;
}
