import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Info } from "lucide-react"
import { cn } from "@/lib/utils"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

const sourceBadgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-xs font-medium transition-colors whitespace-nowrap",
  {
    variants: {
      variant: {
        manual: "bg-green-500/15 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800",
        calculated: "bg-blue-500/15 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800",
        connector: "bg-purple-500/15 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800",
        hybrid: "bg-amber-500/15 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800",
      },
      size: {
        compact: "px-1.5 py-0.5",
        full: "px-2 py-1",
      },
    },
    defaultVariants: {
      variant: "manual",
      size: "full",
    },
  }
)

interface SourceBadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof sourceBadgeVariants> {
  source: "manual" | "calculated" | "connector" | "hybrid"
  connectorName?: string
  tooltip?: string
  compact?: boolean
  showIcon?: boolean
}

const sourceLabels: Record<string, string> = {
  manual: "Manual Input",
  calculated: "Calculated",
  connector: "Synced",
  hybrid: "Manual + Calculated",
}

const sourceIcons: Record<string, React.ReactNode> = {
  manual: "✋",
  calculated: "⚙️",
  connector: "🔗",
  hybrid: "⚡",
}

function SourceBadge({
  source,
  connectorName,
  tooltip,
  compact = false,
  showIcon = true,
  className,
  ...props
}: SourceBadgeProps) {
  const size = compact ? "compact" : "full"
  const variant = source as VariantProps<typeof sourceBadgeVariants>["variant"]

  const label = source === "connector" && connectorName ? connectorName : sourceLabels[source]
  const icon = showIcon ? sourceIcons[source] : null

  const badgeContent = (
    <div className={cn(sourceBadgeVariants({ variant, size }), className)} {...props}>
      {icon && <span className="text-sm">{icon}</span>}
      {!compact && <span>{label}</span>}
    </div>
  )

  if (tooltip) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          {badgeContent}
        </TooltipTrigger>
        <TooltipContent side="right" className="max-w-xs">
          <p>{tooltip}</p>
        </TooltipContent>
      </Tooltip>
    )
  }

  return badgeContent
}

export { SourceBadge, sourceBadgeVariants }
export type { SourceBadgeProps }
