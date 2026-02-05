import { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
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

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  secondaryAction,
  className,
  compact = false,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center",
        compact ? "py-8 px-4" : "py-16 px-6",
        className
      )}
    >
      <div
        className={cn(
          "rounded-full bg-muted/50 flex items-center justify-center mb-4",
          compact ? "h-12 w-12" : "h-16 w-16"
        )}
      >
        <Icon
          className={cn(
            "text-muted-foreground",
            compact ? "h-6 w-6" : "h-8 w-8"
          )}
        />
      </div>
      <h3
        className={cn(
          "font-semibold mb-2",
          compact ? "text-base" : "text-lg"
        )}
      >
        {title}
      </h3>
      <p
        className={cn(
          "text-muted-foreground max-w-md mb-6",
          compact ? "text-sm" : "text-base"
        )}
      >
        {description}
      </p>
      <div className="flex flex-col sm:flex-row items-center gap-3">
        {action && (
          <Button onClick={action.onClick} data-testid="button-empty-action">
            {action.icon && <action.icon className="h-4 w-4 mr-2" />}
            {action.label}
          </Button>
        )}
        {secondaryAction && (
          <Button
            variant="ghost"
            onClick={secondaryAction.onClick}
            data-testid="button-empty-secondary"
          >
            {secondaryAction.label}
          </Button>
        )}
      </div>
    </div>
  );
}

interface EmptyStateCardProps extends EmptyStateProps {
  showBorder?: boolean;
}

export function EmptyStateCard({
  showBorder = true,
  ...props
}: EmptyStateCardProps) {
  return (
    <div
      className={cn(
        "rounded-lg",
        showBorder && "border border-dashed border-border/60"
      )}
    >
      <EmptyState {...props} />
    </div>
  );
}
