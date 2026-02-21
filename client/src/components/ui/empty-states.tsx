import { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Database, TrendingUp, List, AlertCircle } from "lucide-react";

/**
 * Enhanced empty state components for various UI contexts
 * Designed to provide clear feedback when data is not available
 */

interface BaseEmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
    icon?: LucideIcon;
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
  compact?: boolean;
}

/* ===== EMPTY TABLE ===== */

interface EmptyTableProps extends BaseEmptyStateProps {
  columnCount?: number;
}

export function EmptyTable({
  icon: Icon = Database,
  title = "No data yet",
  description = "No records found. Start by adding your first entry.",
  action,
  secondaryAction,
  className,
  compact = false,
  columnCount = 1,
}: EmptyTableProps) {
  const paddingClass = compact ? "py-8 px-4" : "py-16 px-6";

  return (
    <div className={cn("w-full border rounded-lg bg-card/50 overflow-hidden", className)}>
      {/* Mimic table structure */}
      <div className="bg-muted/20 border-b">
        <div className="flex items-center">
          {Array.from({ length: Math.min(columnCount, 4) }).map((_, i) => (
            <div
              key={`col-${i}`}
              className="flex-1 px-4 py-3 border-r last:border-r-0 text-sm font-medium text-muted-foreground"
            >
              {["Name", "Status", "Date", "Action"][i]}
            </div>
          ))}
        </div>
      </div>

      {/* Empty state content */}
      <div className={cn("flex flex-col items-center justify-center text-center", paddingClass)}>
        <div className={cn(
          "rounded-full bg-muted/50 flex items-center justify-center mb-4",
          compact ? "h-12 w-12" : "h-16 w-16"
        )}>
          <Icon className={cn(
            "text-muted-foreground",
            compact ? "h-6 w-6" : "h-8 w-8"
          )} />
        </div>
        <h3 className={cn("font-semibold mb-2", compact ? "text-base" : "text-lg")}>
          {title}
        </h3>
        {description && (
          <p className={cn(
            "text-muted-foreground max-w-md mb-6",
            compact ? "text-sm" : "text-base"
          )}>
            {description}
          </p>
        )}
        <div className="flex flex-col sm:flex-row items-center gap-3">
          {action && (
            <Button onClick={action.onClick} size={compact ? "sm" : "default"}>
              {action.icon && <action.icon className="h-4 w-4 mr-2" />}
              {action.label}
            </Button>
          )}
          {secondaryAction && (
            <Button
              variant="ghost"
              onClick={secondaryAction.onClick}
              size={compact ? "sm" : "default"}
            >
              {secondaryAction.label}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ===== EMPTY CHART ===== */

interface EmptyChartProps extends BaseEmptyStateProps {
  height?: number;
}

export function EmptyChart({
  icon: Icon = TrendingUp,
  title = "No data available",
  description = "There's no data to display yet. Check back after collecting some metrics.",
  action,
  secondaryAction,
  className,
  compact = false,
  height = 300,
}: EmptyChartProps) {
  return (
    <div
      className={cn(
        "border rounded-lg bg-card/50 flex flex-col items-center justify-center",
        className
      )}
      style={{ height: `${height}px` }}
    >
      <div className={cn(
        "rounded-full bg-muted/50 flex items-center justify-center mb-4",
        compact ? "h-12 w-12" : "h-16 w-16"
      )}>
        <Icon className={cn(
          "text-muted-foreground",
          compact ? "h-6 w-6" : "h-8 w-8"
        )} />
      </div>
      <h3 className={cn("font-semibold mb-2 text-center", compact ? "text-base" : "text-lg")}>
        {title}
      </h3>
      {description && (
        <p className={cn(
          "text-muted-foreground max-w-sm mb-6 text-center",
          compact ? "text-sm px-4" : "text-base px-6"
        )}>
          {description}
        </p>
      )}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        {action && (
          <Button onClick={action.onClick} size={compact ? "sm" : "default"}>
            {action.icon && <action.icon className="h-4 w-4 mr-2" />}
            {action.label}
          </Button>
        )}
        {secondaryAction && (
          <Button
            variant="ghost"
            onClick={secondaryAction.onClick}
            size={compact ? "sm" : "default"}
          >
            {secondaryAction.label}
          </Button>
        )}
      </div>
    </div>
  );
}

/* ===== EMPTY LIST ===== */

interface EmptyListProps extends BaseEmptyStateProps {}

export function EmptyList({
  icon: Icon = List,
  title = "Nothing here yet",
  description = "Start creating items to see them appear in this list.",
  action,
  secondaryAction,
  className,
  compact = false,
}: EmptyListProps) {
  const paddingClass = compact ? "py-8 px-4" : "py-16 px-6";

  return (
    <div className={cn(
      "border border-dashed rounded-lg bg-card/30 flex flex-col items-center justify-center text-center",
      paddingClass,
      className
    )}>
      <div className={cn(
        "rounded-full bg-muted/30 flex items-center justify-center mb-4",
        compact ? "h-12 w-12" : "h-16 w-16"
      )}>
        <Icon className={cn(
          "text-muted-foreground/60",
          compact ? "h-6 w-6" : "h-8 w-8"
        )} />
      </div>
      <h3 className={cn("font-semibold mb-2", compact ? "text-base" : "text-lg")}>
        {title}
      </h3>
      {description && (
        <p className={cn(
          "text-muted-foreground max-w-md mb-6",
          compact ? "text-sm" : "text-base"
        )}>
          {description}
        </p>
      )}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        {action && (
          <Button onClick={action.onClick} size={compact ? "sm" : "default"}>
            {action.icon && <action.icon className="h-4 w-4 mr-2" />}
            {action.label}
          </Button>
        )}
        {secondaryAction && (
          <Button
            variant="ghost"
            onClick={secondaryAction.onClick}
            size={compact ? "sm" : "default"}
          >
            {secondaryAction.label}
          </Button>
        )}
      </div>
    </div>
  );
}

/* ===== EMPTY SEARCH RESULTS ===== */

interface EmptySearchProps extends BaseEmptyStateProps {
  searchQuery?: string;
}

export function EmptySearch({
  icon: Icon = AlertCircle,
  title = "No results found",
  description = "Try adjusting your search terms or filters.",
  action,
  secondaryAction,
  className,
  compact = false,
  searchQuery,
}: EmptySearchProps) {
  const paddingClass = compact ? "py-8 px-4" : "py-12 px-6";

  return (
    <div className={cn(
      "border rounded-lg bg-card/50 flex flex-col items-center justify-center text-center",
      paddingClass,
      className
    )}>
      <div className={cn(
        "rounded-full bg-amber-500/10 flex items-center justify-center mb-4",
        compact ? "h-12 w-12" : "h-16 w-16"
      )}>
        <Icon className={cn(
          "text-amber-600 dark:text-amber-500",
          compact ? "h-6 w-6" : "h-8 w-8"
        )} />
      </div>
      <h3 className={cn("font-semibold mb-1", compact ? "text-base" : "text-lg")}>
        {title}
      </h3>
      {searchQuery && (
        <p className={cn("text-muted-foreground mb-2", compact ? "text-xs" : "text-sm")}>
          for <span className="font-medium text-foreground">"{searchQuery}"</span>
        </p>
      )}
      {description && (
        <p className={cn(
          "text-muted-foreground max-w-md mb-6",
          compact ? "text-sm" : "text-base"
        )}>
          {description}
        </p>
      )}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        {action && (
          <Button onClick={action.onClick} variant="outline" size={compact ? "sm" : "default"}>
            {action.icon && <action.icon className="h-4 w-4 mr-2" />}
            {action.label}
          </Button>
        )}
        {secondaryAction && (
          <Button
            variant="ghost"
            onClick={secondaryAction.onClick}
            size={compact ? "sm" : "default"}
          >
            {secondaryAction.label}
          </Button>
        )}
      </div>
    </div>
  );
}

/* ===== EMPTY STATE CARD ===== */

interface EmptyStateCardProps extends BaseEmptyStateProps {
  variant?: 'default' | 'muted' | 'warning';
}

export function EmptyStateCard({
  icon: Icon = List,
  title,
  description,
  action,
  secondaryAction,
  className,
  compact = false,
  variant = 'default',
}: EmptyStateCardProps) {
  const bgMap = {
    default: 'bg-card/50',
    muted: 'bg-muted/20',
    warning: 'bg-amber-500/5 border-amber-200 dark:border-amber-900/30',
  };

  const paddingClass = compact ? 'py-6 px-4' : 'py-12 px-6';

  return (
    <div className={cn(
      "border rounded-lg flex flex-col items-center justify-center text-center",
      bgMap[variant],
      paddingClass,
      className
    )}>
      {Icon && (
        <div className={cn(
          "rounded-full bg-muted/50 flex items-center justify-center mb-4",
          compact ? "h-10 w-10" : "h-12 w-12"
        )}>
          <Icon className={cn(
            "text-muted-foreground",
            compact ? "h-5 w-5" : "h-6 w-6"
          )} />
        </div>
      )}
      <h3 className={cn("font-semibold mb-2", compact ? "text-sm" : "text-base")}>
        {title}
      </h3>
      {description && (
        <p className={cn(
          "text-muted-foreground max-w-sm mb-6",
          compact ? "text-xs" : "text-sm"
        )}>
          {description}
        </p>
      )}
      {(action || secondaryAction) && (
        <div className="flex flex-col sm:flex-row items-center gap-2">
          {action && (
            <Button onClick={action.onClick} size={compact ? "sm" : "default"} className="text-xs">
              {action.icon && <action.icon className="h-3 w-3 mr-1" />}
              {action.label}
            </Button>
          )}
          {secondaryAction && (
            <Button
              variant="ghost"
              onClick={secondaryAction.onClick}
              size={compact ? "sm" : "default"}
              className="text-xs"
            >
              {secondaryAction.label}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
