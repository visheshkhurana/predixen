import React from 'react'
import { SourceBadge } from '@/components/ui/source-badge'
import { FieldHelp } from '@/components/ui/field-help'
import { getFieldHelp } from '@/lib/field-help-data'
import { cn } from '@/lib/utils'

interface FieldWithSourceBadgeProps {
  fieldName: string
  label?: string
  value?: string | number
  source: 'manual' | 'calculated' | 'connector' | 'hybrid'
  connectorName?: string
  showFieldHelp?: boolean
  compact?: boolean
  className?: string
  children?: React.ReactNode
}

/**
 * Wrapper component that displays a field with its source badge and optional help icon
 * Useful for clarifying which data is user-input vs system-calculated vs connector-synced
 */
export function FieldWithSourceBadge({
  fieldName,
  label,
  value,
  source,
  connectorName,
  showFieldHelp = true,
  compact = false,
  className,
  children,
}: FieldWithSourceBadgeProps) {
  const fieldHelp = getFieldHelp(fieldName)
  const displayLabel = label || fieldHelp?.label || fieldName

  return (
    <div className={cn("flex items-center gap-2 group", className)}>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-foreground">
            {displayLabel}
          </span>
          {showFieldHelp && fieldHelp && (
            <FieldHelp
              fieldName={fieldName}
              label={fieldHelp.label}
              description={fieldHelp.description}
              source={fieldHelp.source}
              usedFor={fieldHelp.usedFor}
              tip={fieldHelp.tip}
              compact={true}
            />
          )}
        </div>
        {value !== undefined && !children && (
          <p className="text-lg font-semibold text-foreground mt-1">{value}</p>
        )}
        {children}
      </div>
      <SourceBadge
        source={source}
        connectorName={connectorName}
        compact={compact}
      />
    </div>
  )
}

export default FieldWithSourceBadge
