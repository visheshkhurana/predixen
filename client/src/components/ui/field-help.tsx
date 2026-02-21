import * as React from "react"
import { HelpCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

interface FieldHelpProps extends React.HTMLAttributes<HTMLButtonElement> {
  fieldName: string
  label?: string
  description?: string
  source?: string | string[]
  usedFor?: string[]
  tip?: string
  compact?: boolean
}

function FieldHelp({
  fieldName,
  label,
  description,
  source,
  usedFor,
  tip,
  compact = false,
  className,
  ...props
}: FieldHelpProps) {
  const sourceText = Array.isArray(source)
    ? source.join(", ")
    : source || "Unknown"

  const content = (
    <div className="space-y-3">
      {label && <h4 className="font-semibold text-sm">{label}</h4>}

      {description && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1">About</p>
          <p className="text-xs text-foreground">{description}</p>
        </div>
      )}

      {source && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1">Source</p>
          <p className="text-xs text-foreground">{sourceText}</p>
        </div>
      )}

      {usedFor && usedFor.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1">Used for</p>
          <ul className="text-xs text-foreground space-y-1">
            {usedFor.map((use, idx) => (
              <li key={idx} className="flex gap-2">
                <span className="text-muted-foreground">•</span>
                <span>{use}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {tip && (
        <div className="bg-blue-500/10 border border-blue-200 dark:border-blue-800 rounded p-2">
          <p className="text-xs text-blue-700 dark:text-blue-300">
            <span className="font-medium">Tip:</span> {tip}
          </p>
        </div>
      )}
    </div>
  )

  const triggerContent = (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ring hover:bg-muted",
        compact ? "h-5 w-5" : "h-6 w-6",
        className
      )}
      {...props}
    >
      <HelpCircle className={compact ? "h-3.5 w-3.5" : "h-4 w-4"} />
    </button>
  )

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        {triggerContent}
      </TooltipTrigger>
      <TooltipContent side="right" className="max-w-sm">
        {content}
      </TooltipContent>
    </Tooltip>
  )
}

export { FieldHelp }
export type { FieldHelpProps }
