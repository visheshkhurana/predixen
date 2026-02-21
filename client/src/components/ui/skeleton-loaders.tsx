import { cn } from "@/lib/utils";

/**
 * Reusable skeleton loading components for data loading states
 * Uses Tailwind CSS animate-pulse for shimmer effect
 */

/* ===== TABLE SKELETON ===== */

interface TableSkeletonProps {
  rows?: number;
  columns?: number;
  className?: string;
}

export function TableSkeleton({
  rows = 5,
  columns = 4,
  className
}: TableSkeletonProps) {
  return (
    <div className={cn("w-full border rounded-lg overflow-hidden", className)}>
      {/* Header */}
      <div className="bg-muted/20 border-b">
        <div className="flex items-center">
          {Array.from({ length: columns }).map((_, i) => (
            <div key={`header-${i}`} className="flex-1 px-4 py-3 border-r last:border-r-0">
              <div className="h-4 bg-muted rounded animate-pulse" />
            </div>
          ))}
        </div>
      </div>

      {/* Rows */}
      <div>
        {Array.from({ length: rows }).map((_, rowIdx) => (
          <div key={`row-${rowIdx}`} className="flex items-center border-b last:border-b-0">
            {Array.from({ length: columns }).map((_, colIdx) => (
              <div key={`cell-${rowIdx}-${colIdx}`} className="flex-1 px-4 py-3 border-r last:border-r-0">
                <div className="h-3 bg-muted rounded animate-pulse" />
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ===== CARD SKELETON ===== */

interface CardSkeletonProps {
  variant?: 'compact' | 'standard' | 'large';
  showChart?: boolean;
  className?: string;
}

export function CardSkeleton({
  variant = 'standard',
  showChart = false,
  className
}: CardSkeletonProps) {
  const paddingMap = {
    compact: 'p-3',
    standard: 'p-4',
    large: 'p-6'
  };

  const headerHeight = {
    compact: 'h-3',
    standard: 'h-4',
    large: 'h-5'
  };

  const contentHeight = {
    compact: 'h-6',
    standard: 'h-8',
    large: 'h-10'
  };

  return (
    <div className={cn("border rounded-lg bg-card", className)}>
      <div className={paddingMap[variant]}>
        {/* Header */}
        <div className="space-y-2 mb-4">
          <div className={`${headerHeight[variant]} bg-muted rounded animate-pulse w-1/3`} />
          <div className="h-2 bg-muted rounded animate-pulse w-1/2" />
        </div>

        {/* Content */}
        {showChart ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={`line-${i}`} className="flex items-end gap-2">
                <div className="h-12 w-8 bg-muted rounded animate-pulse" />
                <div className="h-8 w-8 bg-muted rounded animate-pulse" />
                <div className="h-16 w-8 bg-muted rounded animate-pulse" />
                <div className="h-10 w-8 bg-muted rounded animate-pulse" />
              </div>
            ))}
          </div>
        ) : (
          <div className={`${contentHeight[variant]} bg-muted rounded animate-pulse mb-3`} />
        )}

        {/* Footer */}
        <div className="mt-4 pt-4 border-t space-y-2">
          <div className="h-2 bg-muted rounded animate-pulse w-2/3" />
          <div className="h-2 bg-muted rounded animate-pulse w-1/2" />
        </div>
      </div>
    </div>
  );
}

/* ===== CHART SKELETON ===== */

interface ChartSkeletonProps {
  height?: number;
  className?: string;
}

export function ChartSkeleton({
  height = 300,
  className
}: ChartSkeletonProps) {
  return (
    <div
      className={cn("border rounded-lg bg-card p-6", className)}
      style={{ height: `${height}px` }}
    >
      <div className="space-y-4 h-full flex flex-col">
        {/* Header */}
        <div className="space-y-2">
          <div className="h-4 bg-muted rounded animate-pulse w-1/4" />
          <div className="h-2 bg-muted rounded animate-pulse w-1/3" />
        </div>

        {/* Chart bars/lines */}
        <div className="flex-1 flex items-end justify-around gap-3 pb-8">
          {Array.from({ length: 6 }).map((_, i) => {
            const heightPercent = Math.random() * 100;
            return (
              <div key={`bar-${i}`} className="flex-1 flex flex-col items-center gap-2">
                <div
                  className="w-full bg-muted rounded-t animate-pulse"
                  style={{ height: `${heightPercent}%` }}
                />
                <div className="h-2 bg-muted rounded animate-pulse w-8" />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ===== FORM SKELETON ===== */

interface FormSkeletonProps {
  fields?: number;
  showButton?: boolean;
  className?: string;
}

export function FormSkeleton({
  fields = 4,
  showButton = true,
  className
}: FormSkeletonProps) {
  return (
    <div className={cn("space-y-4", className)}>
      {Array.from({ length: fields }).map((_, i) => (
        <div key={`field-${i}`} className="space-y-2">
          {/* Label */}
          <div className="h-3 bg-muted rounded animate-pulse w-1/4" />
          {/* Input */}
          <div className="h-10 bg-muted rounded animate-pulse" />
        </div>
      ))}

      {showButton && (
        <div className="flex gap-2 pt-4">
          <div className="h-10 bg-primary rounded animate-pulse flex-1" />
          <div className="h-10 bg-muted rounded animate-pulse flex-1" />
        </div>
      )}
    </div>
  );
}

/* ===== METRIC GRID SKELETON ===== */

interface MetricGridSkeletonProps {
  count?: number;
  className?: string;
}

export function MetricGridSkeleton({
  count = 4,
  className
}: MetricGridSkeletonProps) {
  return (
    <div className={cn("grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4", className)}>
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={`metric-${i}`} variant="compact" />
      ))}
    </div>
  );
}

/* ===== LIST SKELETON ===== */

interface ListSkeletonProps {
  items?: number;
  variant?: 'compact' | 'detailed';
  className?: string;
}

export function ListSkeleton({
  items = 5,
  variant = 'compact',
  className
}: ListSkeletonProps) {
  const isDetailed = variant === 'detailed';

  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: items }).map((_, i) => (
        <div key={`item-${i}`} className="p-3 border rounded-lg">
          {isDetailed ? (
            <div className="space-y-2">
              <div className="flex items-start gap-3">
                <div className="h-10 w-10 bg-muted rounded-full animate-pulse shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 bg-muted rounded animate-pulse w-1/3" />
                  <div className="h-2 bg-muted rounded animate-pulse w-1/2" />
                </div>
              </div>
              <div className="h-2 bg-muted rounded animate-pulse w-2/3 ml-13" />
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <div className="h-4 w-4 bg-muted rounded animate-pulse shrink-0" />
              <div className="h-3 bg-muted rounded animate-pulse flex-1" />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

/* ===== HERO SKELETON ===== */

interface HeroSkeletonProps {
  className?: string;
}

export function HeroSkeleton({ className }: HeroSkeletonProps) {
  return (
    <div className={cn("border rounded-lg bg-card p-6 md:p-8", className)}>
      <div className="space-y-4">
        {/* Large title */}
        <div className="h-8 bg-muted rounded animate-pulse w-1/2" />

        {/* Subtitle */}
        <div className="space-y-2">
          <div className="h-4 bg-muted rounded animate-pulse w-full" />
          <div className="h-4 bg-muted rounded animate-pulse w-5/6" />
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={`stat-${i}`} className="space-y-2">
              <div className="h-3 bg-muted rounded animate-pulse w-3/4" />
              <div className="h-5 bg-muted rounded animate-pulse" />
            </div>
          ))}
        </div>

        {/* Action button */}
        <div className="pt-2">
          <div className="h-10 bg-primary rounded animate-pulse w-40" />
        </div>
      </div>
    </div>
  );
}
