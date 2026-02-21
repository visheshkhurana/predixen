import * as React from "react"
import { ChevronDown, ChevronUp } from "lucide-react"
import { cn } from "@/lib/utils"

interface IOLegendProps extends React.HTMLAttributes<HTMLDivElement> {
  collapsible?: boolean
  defaultOpen?: boolean
  position?: "bottom" | "corner" | "inline"
}

function IOLegend({
  collapsible = true,
  defaultOpen = false,
  position = "bottom",
  className,
  ...props
}: IOLegendProps) {
  const [isOpen, setIsOpen] = React.useState(defaultOpen)

  const legendItems = [
    { icon: "🟢", label: "Your Input", color: "text-green-600 dark:text-green-400" },
    { icon: "🔵", label: "Calculated", color: "text-blue-600 dark:text-blue-400" },
    { icon: "🟣", label: "Connector Synced", color: "text-purple-600 dark:text-purple-400" },
    { icon: "🟡", label: "Hybrid", color: "text-amber-600 dark:text-amber-400" },
  ]

  const positionClasses: Record<string, string> = {
    bottom: "fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-auto",
    corner: "fixed bottom-4 right-4",
    inline: "relative",
  }

  return (
    <div
      className={cn(
        "bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border rounded-lg shadow-lg transition-all",
        positionClasses[position],
        !isOpen && collapsible && position !== "inline" && "py-2 px-3",
        className
      )}
      {...props}
    >
      {collapsible && position !== "inline" && (
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full flex items-center justify-between gap-2 text-sm font-medium text-foreground hover:bg-muted rounded px-2 py-1.5 transition-colors"
        >
          <span className="flex items-center gap-2">
            <span className="text-lg">📊</span>
            <span>Data Source Legend</span>
          </span>
          {isOpen ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </button>
      )}

      {(!collapsible || isOpen || position === "inline") && (
        <div className={cn(
          "space-y-2",
          collapsible && position !== "inline" && "pt-2 border-t mt-2"
        )}>
          {!collapsible && position !== "inline" && (
            <div className="flex items-center gap-2 text-sm font-medium text-foreground mb-2">
              <span className="text-lg">📊</span>
              <span>Data Source Legend</span>
            </div>
          )}

          <div className={cn(
            "grid gap-2",
            position === "inline" ? "grid-cols-2 md:grid-cols-4" : "grid-cols-1 sm:grid-cols-2"
          )}>
            {legendItems.map((item, index) => (
              <div
                key={index}
                className="flex items-center gap-2 text-sm text-foreground"
              >
                <span className="text-base">{item.icon}</span>
                <span className="text-xs sm:text-sm">{item.label}</span>
              </div>
            ))}
          </div>

          {position !== "inline" && (
            <div className="pt-2 border-t mt-2">
              <p className="text-xs text-muted-foreground">
                Hover over metric badges to see detailed source information
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export { IOLegend }
export type { IOLegendProps }
