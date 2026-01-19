import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { HelpCircle, Flame } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Legend, Cell } from 'recharts';
import { formatCurrencyAbbrev } from '@/lib/utils';

interface ExpenseBreakdown {
  cogs: number;
  payroll: number;
  marketing: number;
  rd: number;
  ga: number;
  total: number;
}

interface BurnBreakdownChartProps {
  breakdown: ExpenseBreakdown | null;
  currency?: string;
}

const EXPENSE_COLORS = {
  cogs: '#ef4444',      // Red
  payroll: '#3b82f6',   // Blue
  marketing: '#22c55e', // Green
  rd: '#a855f7',        // Purple
  ga: '#f59e0b',        // Amber
};

const EXPENSE_LABELS = {
  cogs: 'COGS',
  payroll: 'Payroll',
  marketing: 'Marketing',
  rd: 'R&D',
  ga: 'G&A',
};

export function BurnBreakdownChart({ breakdown, currency = 'USD' }: BurnBreakdownChartProps) {
  if (!breakdown) {
    return (
      <Card className="overflow-visible">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Flame className="h-4 w-4 text-destructive" />
            Monthly Burn Breakdown
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No expense data available</p>
        </CardContent>
      </Card>
    );
  }

  const formatCurrency = (value: number) => formatCurrencyAbbrev(value, currency);

  // Prepare data for stacked bar chart
  const chartData = [
    {
      name: 'Monthly Burn',
      cogs: breakdown.cogs,
      payroll: breakdown.payroll,
      marketing: breakdown.marketing,
      rd: breakdown.rd,
      ga: breakdown.ga,
    }
  ];

  // Prepare data for breakdown list
  const breakdownList = [
    { key: 'cogs', label: 'COGS', value: breakdown.cogs, color: EXPENSE_COLORS.cogs },
    { key: 'payroll', label: 'Payroll', value: breakdown.payroll, color: EXPENSE_COLORS.payroll },
    { key: 'marketing', label: 'Marketing', value: breakdown.marketing, color: EXPENSE_COLORS.marketing },
    { key: 'rd', label: 'R&D', value: breakdown.rd, color: EXPENSE_COLORS.rd },
    { key: 'ga', label: 'G&A', value: breakdown.ga, color: EXPENSE_COLORS.ga },
  ].sort((a, b) => b.value - a.value);

  return (
    <Card className="overflow-visible">
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Flame className="h-4 w-4 text-destructive" />
          Monthly Burn Breakdown
          <Tooltip>
            <TooltipTrigger asChild>
              <button type="button" className="p-0.5">
                <HelpCircle className="h-3 w-3 text-muted-foreground" />
              </button>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p className="text-sm">
                Breakdown of monthly expenses by category. Identifies the largest cost drivers.
              </p>
            </TooltipContent>
          </Tooltip>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Bar Chart */}
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical">
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="name" hide />
                <Bar dataKey="cogs" stackId="a" fill={EXPENSE_COLORS.cogs} name="COGS" />
                <Bar dataKey="payroll" stackId="a" fill={EXPENSE_COLORS.payroll} name="Payroll" />
                <Bar dataKey="marketing" stackId="a" fill={EXPENSE_COLORS.marketing} name="Marketing" />
                <Bar dataKey="rd" stackId="a" fill={EXPENSE_COLORS.rd} name="R&D" />
                <Bar dataKey="ga" stackId="a" fill={EXPENSE_COLORS.ga} name="G&A" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Breakdown List */}
          <div className="space-y-2">
            {breakdownList.map((item) => (
              <div key={item.key} className="flex items-center justify-between" data-testid={`burn-${item.key}`}>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: item.color }} />
                  <span className="text-sm">{item.label}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-mono font-medium">{formatCurrency(item.value)}</span>
                  <span className="text-xs text-muted-foreground">
                    ({((item.value / breakdown.total) * 100).toFixed(0)}%)
                  </span>
                </div>
              </div>
            ))}
            <div className="pt-2 border-t flex items-center justify-between font-semibold">
              <span className="text-sm">Total</span>
              <span className="text-sm font-mono">{formatCurrency(breakdown.total)}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
