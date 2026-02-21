/**
 * Example component showing how to integrate source tracking into data input forms
 *
 * This demonstrates best practices for displaying:
 * - Which fields are manual inputs vs calculated
 * - Where data comes from (connectors, manual entry, calculations)
 * - Help information for each field
 * - Data confidence indicators
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { FieldWithSourceBadge } from '@/components/FieldWithSourceBadge'
import { SourceBadge } from '@/components/ui/source-badge'
import { FieldHelp } from '@/components/ui/field-help'
import { IOLegend } from '@/components/ui/io-legend'
import { getFieldHelp } from '@/lib/field-help-data'
import { AlertCircle, CheckCircle2 } from 'lucide-react'

interface DataInputWithSourcesProps {
  /** Callback when field value changes */
  onFieldChange?: (fieldName: string, value: number | string) => void
  /** Show connector-synced fields as read-only */
  connectorSyncEnabled?: boolean
}

export function DataInputWithSources({
  onFieldChange,
  connectorSyncEnabled = false,
}: DataInputWithSourcesProps) {
  const [formData, setFormData] = React.useState({
    cashOnHand: 500000,
    monthlyRevenue: 45000,
    payrollExpenses: 25000,
    marketingExpenses: 8000,
    operatingExpenses: 5000,
    cogsExpenses: 4500,
  })

  // Simulated data sources - in reality this would come from your backend
  const dataSources = {
    cashOnHand: 'connector' as const, // From bank API
    monthlyRevenue: 'connector' as const, // From Stripe
    payrollExpenses: 'manual' as const, // Manually entered
    marketingExpenses: 'hybrid' as const, // Mix of manual and data
    operatingExpenses: 'manual' as const,
    cogsExpenses: 'calculated' as const, // Derived from revenue
  }

  const handleChange = (field: string, value: string) => {
    const numValue = parseFloat(value) || 0
    setFormData((prev) => ({ ...prev, [field]: numValue }))
    onFieldChange?.(field, numValue)
  }

  // Calculate derived metrics
  const totalExpenses = Object.values(formData).slice(2).reduce((a, b) => a + b, 0)
  const grossMargin = formData.monthlyRevenue > 0
    ? ((formData.monthlyRevenue - formData.cogsExpenses) / formData.monthlyRevenue) * 100
    : 0
  const burnRate = formData.monthlyRevenue - totalExpenses

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header with legend */}
      <div className="space-y-4">
        <h1 className="text-3xl font-bold">Financial Data Input</h1>
        <p className="text-muted-foreground">
          Manage your financial metrics and see where each data point comes from
        </p>
        <IOLegend position="inline" collapsible={false} />
      </div>

      {/* Section 1: Cash and Revenue (Connector-synced) */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span className="text-lg">💳</span>
            Connector-Synced Data
          </CardTitle>
          <CardDescription>
            These fields are automatically synced from your connected accounts
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Cash on Hand */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Label htmlFor="cash">Cash on Hand</Label>
              <FieldHelp
                fieldName="cashOnHand"
                compact={true}
              />
            </div>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <Input
                  id="cash"
                  type="number"
                  value={formData.cashOnHand}
                  onChange={(e) => handleChange('cashOnHand', e.target.value)}
                  disabled={connectorSyncEnabled}
                  className="text-lg font-semibold"
                />
              </div>
              <div className="flex items-center gap-2">
                <SourceBadge
                  source="connector"
                  connectorName="Bank API"
                  tooltip="Synced from your bank connection every 6 hours"
                />
                <Badge variant="outline" className="flex items-center gap-1 ml-2">
                  <CheckCircle2 className="h-3 w-3 text-green-600" />
                  Latest
                </Badge>
              </div>
            </div>
          </div>

          {/* Monthly Revenue */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Label htmlFor="mrr">Monthly Revenue</Label>
              <FieldHelp
                fieldName="monthlyRevenue"
                compact={true}
              />
            </div>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <Input
                  id="mrr"
                  type="number"
                  value={formData.monthlyRevenue}
                  onChange={(e) => handleChange('monthlyRevenue', e.target.value)}
                  disabled={connectorSyncEnabled}
                  className="text-lg font-semibold"
                />
              </div>
              <div className="flex items-center gap-2">
                <SourceBadge
                  source="connector"
                  connectorName="Stripe"
                  tooltip="Automatically synced from Stripe API"
                />
                <Badge variant="outline" className="flex items-center gap-1 ml-2">
                  <CheckCircle2 className="h-3 w-3 text-green-600" />
                  Verified
                </Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Section 2: Manual Expense Entries */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span className="text-lg">✋</span>
            Manual Data Entries
          </CardTitle>
          <CardDescription>
            Fields you maintain manually. Update these regularly for accuracy
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Payroll */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Label htmlFor="payroll">Payroll Expenses</Label>
              <FieldHelp
                fieldName="payrollExpenses"
                compact={true}
              />
            </div>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <Input
                  id="payroll"
                  type="number"
                  value={formData.payrollExpenses}
                  onChange={(e) => handleChange('payrollExpenses', e.target.value)}
                  className="text-lg font-semibold"
                />
              </div>
              <SourceBadge
                source="manual"
                tooltip="Last updated on 2024-02-15"
              />
            </div>
          </div>

          {/* Marketing */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Label htmlFor="marketing">Marketing Expenses</Label>
              <FieldHelp
                fieldName="marketingExpenses"
                compact={true}
              />
            </div>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <Input
                  id="marketing"
                  type="number"
                  value={formData.marketingExpenses}
                  onChange={(e) => handleChange('marketingExpenses', e.target.value)}
                  className="text-lg font-semibold"
                />
              </div>
              <SourceBadge
                source="hybrid"
                tooltip="Mix of manual entries and Mixpanel integration"
              />
            </div>
          </div>

          {/* Operating */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Label htmlFor="operating">Operating Expenses</Label>
              <FieldHelp
                fieldName="operatingExpenses"
                compact={true}
              />
            </div>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <Input
                  id="operating"
                  type="number"
                  value={formData.operatingExpenses}
                  onChange={(e) => handleChange('operatingExpenses', e.target.value)}
                  className="text-lg font-semibold"
                />
              </div>
              <SourceBadge
                source="manual"
                tooltip="Updated monthly by finance team"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Section 3: Calculated/Derived Metrics */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span className="text-lg">⚙️</span>
            Calculated Metrics
          </CardTitle>
          <CardDescription>
            These values are computed from your input data. They update automatically
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* COGS (calculated from revenue % or manual) */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Label htmlFor="cogs">Cost of Goods Sold</Label>
              <FieldHelp
                fieldName="cogsExpenses"
                compact={true}
              />
            </div>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <div className="p-3 bg-muted rounded-md font-semibold text-lg">
                  ${formData.cogsExpenses.toLocaleString()}
                </div>
              </div>
              <SourceBadge
                source="calculated"
                tooltip="10% of Monthly Revenue"
              />
            </div>
          </div>

          {/* Gross Margin */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Label>Gross Margin</Label>
              <FieldHelp
                fieldName="grossMargin"
                compact={true}
              />
            </div>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <div className="p-3 bg-muted rounded-md font-semibold text-lg">
                  {grossMargin.toFixed(1)}%
                </div>
              </div>
              <SourceBadge
                source="calculated"
                tooltip="(Revenue - COGS) / Revenue"
              />
            </div>
          </div>

          {/* Burn Rate */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Label>Monthly Burn Rate</Label>
              <FieldHelp
                fieldName="burnRate"
                compact={true}
              />
            </div>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <div className={`p-3 rounded-md font-semibold text-lg ${
                  burnRate > 0 ? 'bg-red-50 dark:bg-red-950 text-red-600 dark:text-red-400' : 'bg-green-50 dark:bg-green-950 text-green-600 dark:text-green-400'
                }`}>
                  ${burnRate.toLocaleString()}
                </div>
              </div>
              <SourceBadge
                source="calculated"
                tooltip="Revenue - Total Expenses"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Data Quality Summary */}
      <Card className="border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <span>📊</span>
            Data Quality Summary
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-1">
              <div className="text-sm font-medium text-muted-foreground">Manual Inputs</div>
              <div className="text-2xl font-bold">3</div>
              <div className="text-xs text-muted-foreground">Fields you control</div>
            </div>
            <div className="space-y-1">
              <div className="text-sm font-medium text-muted-foreground">Synced Connections</div>
              <div className="text-2xl font-bold">2</div>
              <div className="text-xs text-muted-foreground">Auto-updated daily</div>
            </div>
            <div className="space-y-1">
              <div className="text-sm font-medium text-muted-foreground">Overall Confidence</div>
              <div className="text-2xl font-bold">92%</div>
              <div className="text-xs text-muted-foreground">High confidence</div>
            </div>
          </div>
          <div className="pt-3 border-t">
            <p className="text-sm text-muted-foreground">
              💡 <strong>Tip:</strong> Connect more data sources to automatically populate fields and increase accuracy.
              <a href="/integrations" className="text-primary hover:underline ml-1">View integrations</a>
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Footer Legend */}
      <IOLegend position="bottom" defaultOpen={true} />
    </div>
  )
}

export default DataInputWithSources
