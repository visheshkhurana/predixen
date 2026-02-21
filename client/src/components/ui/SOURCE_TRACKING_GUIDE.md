# Data Source Tracking Components

This guide explains the new UI components that help clarify which data is user-input vs system-calculated vs connector-synced.

## Components Overview

### 1. SourceBadge Component

A badge that shows the source of a data point at a glance.

**Location:** `/client/src/components/ui/source-badge.tsx`

**Props:**
- `source`: "manual" | "calculated" | "connector" | "hybrid"
- `connectorName?`: string (e.g., "Stripe", "QuickBooks")
- `tooltip?`: string (detailed tooltip text)
- `compact?`: boolean (icon only vs icon + text)
- `showIcon?`: boolean (show emoji icon)

**Variants:**
- 🟢 **manual**: Green badge, "Manual Input"
- 🔵 **calculated**: Blue badge, "Calculated"
- 🟣 **connector**: Purple badge, connector name (e.g., "Stripe")
- 🟡 **hybrid**: Amber badge, "Manual + Calculated"

**Usage Example:**
```tsx
import { SourceBadge } from '@/components/ui/source-badge'

// Full badge with text
<SourceBadge
  source="manual"
  tooltip="Entered directly by user on 2024-02-15"
/>

// Compact (icon only)
<SourceBadge
  source="connector"
  connectorName="Stripe"
  compact={true}
/>

// With tooltip
<SourceBadge
  source="calculated"
  tooltip="Calculated from Monthly Revenue × 12"
/>
```

---

### 2. FieldHelp Component

An info icon that displays detailed help content about a field in a tooltip.

**Location:** `/client/src/components/ui/field-help.tsx`

**Props:**
- `fieldName`: string (for identifying the field)
- `label?`: string (display name)
- `description?`: string (what the field is)
- `source?`: string | string[] (where data comes from)
- `usedFor?`: string[] (which calculations depend on it)
- `tip?`: string (optional tip/best practice)
- `compact?`: boolean (smaller icon)

**Usage Example:**
```tsx
import { FieldHelp } from '@/components/ui/field-help'
import { getFieldHelp } from '@/lib/field-help-data'

// Using pre-configured help data
const mrrHelp = getFieldHelp('monthlyRevenue')
<FieldHelp
  fieldName="monthlyRevenue"
  label={mrrHelp?.label}
  description={mrrHelp?.description}
  source={mrrHelp?.source}
  usedFor={mrrHelp?.usedFor}
  tip={mrrHelp?.tip}
/>

// Custom help content
<FieldHelp
  fieldName="custom_field"
  label="Custom Metric"
  description="This is a custom field"
  source={["Manual entry", "API integration"]}
  usedFor={["Report generation", "Forecasting"]}
  tip="Enter values in USD currency"
/>
```

---

### 3. IOLegend Component

A collapsible legend showing what each data source indicator means.

**Location:** `/client/src/components/ui/io-legend.tsx`

**Props:**
- `collapsible?`: boolean (default: true)
- `defaultOpen?`: boolean (default: false)
- `position?`: "bottom" | "corner" | "inline" (default: "bottom")

**Usage Example:**
```tsx
import { IOLegend } from '@/components/ui/io-legend'

// At bottom of page (default)
<IOLegend position="bottom" defaultOpen={false} />

// In corner
<IOLegend position="corner" collapsible={true} />

// Inline (e.g., in a section)
<IOLegend position="inline" collapsible={false} />
```

**Display:**
```
🟢 Your Input
🔵 Calculated
🟣 Connector Synced
🟡 Hybrid
```

---

### 4. FieldWithSourceBadge Component

A convenience wrapper that combines a field label, value, help icon, and source badge.

**Location:** `/client/src/components/FieldWithSourceBadge.tsx`

**Props:**
- `fieldName`: string (for fetching help data)
- `label?`: string (override display label)
- `value?`: string | number (field value)
- `source`: "manual" | "calculated" | "connector" | "hybrid"
- `connectorName?`: string (for connector source)
- `showFieldHelp?`: boolean (default: true)
- `compact?`: boolean (compact badge)

**Usage Example:**
```tsx
import { FieldWithSourceBadge } from '@/components/FieldWithSourceBadge'

<FieldWithSourceBadge
  fieldName="monthlyRevenue"
  value="$45,000"
  source="connector"
  connectorName="Stripe"
  showFieldHelp={true}
/>

// Renders:
// [label] [help icon]
// $45,000
//         [🟣 Stripe badge]
```

---

## Field Help Data

Pre-configured help content for common financial fields.

**Location:** `/client/src/lib/field-help-data.ts`

**Available Fields:**
- Core Inputs: `cashOnHand`, `monthlyRevenue`, `totalMonthlyExpenses`
- Expense Breakdown: `payrollExpenses`, `marketingExpenses`, `operatingExpenses`, `cogsExpenses`
- Growth Metrics: `monthlyGrowthRate`, `churnRate`, `totalCustomers`, `headcount`
- Financial Health: `runway`, `burnRate`, `burnMultiple`, `grossMargin`
- Unit Economics: `cac`, `ltv`, `ltvCacRatio`
- Data Quality: `dataConfidenceScore`, `qualityOfGrowthIndex`

**Helper Functions:**

```tsx
import { getFieldHelp, getFieldsBySource } from '@/lib/field-help-data'

// Get help for a specific field
const help = getFieldHelp('monthlyRevenue')
// Returns: { label, description, source, usedFor, tip }

// Get all fields of a type
const manualFields = getFieldsBySource('manual')
const calculatedFields = getFieldsBySource('calculated')
const connectorFields = getFieldsBySource('connector')
```

---

## Integration Patterns

### Pattern 1: Metric Cards with Source Badge

```tsx
import { MetricCard } from '@/components/MetricCard'
import { SourceBadge } from '@/components/ui/source-badge'

<div className="space-y-2">
  <div className="flex items-center gap-2">
    <h3 className="font-semibold">Monthly Revenue</h3>
    <SourceBadge source="connector" connectorName="Stripe" />
  </div>
  <MetricCard
    title="MRR"
    value={formatCurrency(baseData.mrr)}
    // ... other props
  />
</div>
```

### Pattern 2: Form Fields with Help

```tsx
import { FieldWithSourceBadge } from '@/components/FieldWithSourceBadge'
import { Input } from '@/components/ui/input'

<FieldWithSourceBadge
  fieldName="cashOnHand"
  source="manual"
  showFieldHelp={true}
>
  <Input
    type="number"
    value={cashOnHand}
    onChange={(e) => setCashOnHand(e.target.value)}
    placeholder="Enter amount"
  />
</FieldWithSourceBadge>
```

### Pattern 3: Dashboard with Legend

```tsx
<div className="space-y-6">
  {/* Your dashboard content */}

  {/* Add legend at bottom */}
  <IOLegend position="bottom" defaultOpen={false} />
</div>
```

### Pattern 4: Data Quality Indicators

```tsx
// Combine source badge with confidence score
<div className="flex items-center justify-between">
  <span>Cash on Hand: $500,000</span>
  <div className="flex gap-2">
    <Badge>95% Confidence</Badge>
    <SourceBadge source="connector" connectorName="Bank API" />
  </div>
</div>
```

---

## Best Practices

1. **Always label the source**: Use SourceBadge consistently across all metric displays
2. **Provide context with tooltips**: Include tooltips explaining why data has a particular source
3. **Use Help icons for complex fields**: Especially for calculated or derived metrics
4. **Show the legend once per page**: Place IOLegend at the bottom for user reference
5. **Update sources when data changes**: If you change data calculation logic, update the source accordingly
6. **Color consistency**: Follow the standard color scheme (green=manual, blue=calculated, purple=connector, amber=hybrid)

---

## Customization

### Adding New Fields to Help Data

Edit `/client/src/lib/field-help-data.ts`:

```tsx
FIELD_HELP_MAP: Record<string, FieldHelpContent> = {
  // ... existing fields

  myNewField: {
    label: "My New Field",
    description: "What this field represents",
    source: ["Manual entry", "External API"],
    usedFor: ["Calculation A", "Report B"],
    tip: "Optional tip for users",
  },
}
```

### Styling Customization

All components use Tailwind CSS and inherit from the application theme. Modify colors in:
- `source-badge.tsx`: Badge variant colors
- `field-help.tsx`: Tooltip background colors
- `io-legend.tsx`: Legend background and text colors

---

## Accessibility

- All components include proper ARIA labels and keyboard navigation
- Tooltips work with keyboard focus (Tab to trigger)
- Icons include semantic meaning through color + text
- Help icons have proper contrast ratios

---

## Migration Guide

If you have existing metric displays without source information:

1. Identify the source of each metric (manual, calculated, or connector)
2. Add SourceBadge component next to the metric
3. Use getFieldHelp() to populate FieldHelp icons
4. Add IOLegend to the page footer
5. Test with keyboard navigation and screen readers

---

## Examples

See `/client/src/pages/overview.tsx` for live examples of:
- SourceBadge integration with MetricCard
- IOLegend placement at bottom of page
- Provenance data from truth scans
