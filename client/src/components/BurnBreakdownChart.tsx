import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { HelpCircle, Flame } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Legend, Cell, Tooltip as RechartsTooltip } from 'recharts';
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

const EXPENSE_LABELS: Record<string, string> = {
  cogs: 'COGS',
  payroll: 'Payroll',
  marketing: 'Marketing',
  rd: 'R&D',
  ga: 'G&A',
};

const EXPENSE_IMPACTS: Record<string, { meaning: string; benchmark: string; guidance: string }> = {
  cogs: {
    meaning: 'Cost of Goods Sold - Direct costs to deliver your product/service including hosting, infrastructure, and customer support.',
    benchmark: 'Best-in-class SaaS companies keep COGS under 20% of revenue.',
    guidance: 'High COGS reduces gross margin and limits funds available for growth investments.',
  },
  payroll: {
    meaning: 'Team salaries, benefits, and contractor payments. Usually the largest expense for startups.',
    benchmark: 'Healthy startups spend 50-70% of burn on payroll.',
    guidance: 'Higher payroll often indicates investment in growth. Monitor revenue per employee for efficiency.',
  },
  marketing: {
    meaning: 'Customer acquisition costs including advertising, content, events, and sales tools.',
    benchmark: 'Efficient SaaS spends $1-2 on marketing for every $1 of new ARR.',
    guidance: 'High marketing spend is healthy if it generates efficient customer acquisition (CAC payback under 12 months).',
  },
  rd: {
    meaning: 'Research & Development - Product development, engineering, and innovation investments.',
    benchmark: 'Growth-stage SaaS typically spends 20-30% of revenue on R&D.',
    guidance: 'R&D investment builds competitive moats. Balance with near-term revenue generation.',
  },
  ga: {
    meaning: 'General & Administrative - Legal, accounting, office, insurance, and administrative costs.',
    benchmark: 'Target G&A under 15% of total expenses for efficient operations.',
    guidance: 'G&A should scale slower than revenue. Rising G&A percentage signals operational inefficiency.',
  },
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

  // Custom tooltip for bar chart with detailed explanations
  const CustomChartTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const item = payload[0];
      const key = item.dataKey as string;
      const value = item.value as number;
      const pct = ((value / breakdown.total) * 100).toFixed(1);
      const impact = EXPENSE_IMPACTS[key];
      
      return (
        <div className="bg-popover border rounded-lg p-3 shadow-lg text-sm max-w-xs">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: EXPENSE_COLORS[key as keyof typeof EXPENSE_COLORS] }} />
            <span className="font-semibold">{EXPENSE_LABELS[key]}</span>
            <span className="font-mono ml-auto">{formatCurrency(value)}</span>
          </div>
          <p className="text-muted-foreground text-xs mb-2">{pct}% of total burn</p>
          {impact && (
            <div className="space-y-2 pt-2 border-t">
              <p className="text-xs"><span className="font-medium">What it is:</span> {impact.meaning}</p>
              <p className="text-xs"><span className="font-medium text-primary">Benchmark:</span> {impact.benchmark}</p>
              <p className="text-xs"><span className="font-medium text-amber-500">Impact:</span> {impact.guidance}</p>
            </div>
          )}
        </div>
      );
    }
    return null;
  };

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
                Breakdown of monthly expenses by category. Identifies the largest cost drivers. Hover over each segment for detailed impact analysis.
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
                <RechartsTooltip content={<CustomChartTooltip />} cursor={{ fill: 'transparent' }} />
                <Bar dataKey="cogs" stackId="a" fill={EXPENSE_COLORS.cogs} name="COGS" />
                <Bar dataKey="payroll" stackId="a" fill={EXPENSE_COLORS.payroll} name="Payroll" />
                <Bar dataKey="marketing" stackId="a" fill={EXPENSE_COLORS.marketing} name="Marketing" />
                <Bar dataKey="rd" stackId="a" fill={EXPENSE_COLORS.rd} name="R&D" />
                <Bar dataKey="ga" stackId="a" fill={EXPENSE_COLORS.ga} name="G&A" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Breakdown List with tooltips */}
          <div className="space-y-2">
            {breakdownList.map((item) => {
              const impact = EXPENSE_IMPACTS[item.key];
              return (
                <Tooltip key={item.key}>
                  <TooltipTrigger asChild>
                    <div className="flex items-center justify-between cursor-help hover:bg-secondary/50 rounded px-1 -mx-1 transition-colors" data-testid={`burn-${item.key}`}>
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
                  </TooltipTrigger>
                  <TooltipContent side="left" className="max-w-xs">
                    <div className="space-y-2">
                      <p className="font-medium">{item.label} - {formatCurrency(item.value)}</p>
                      {impact && (
                        <>
                          <p className="text-xs">{impact.meaning}</p>
                          <p className="text-xs text-primary">{impact.benchmark}</p>
                          <p className="text-xs text-amber-400">{impact.guidance}</p>
                        </>
                      )}
                    </div>
                  </TooltipContent>
                </Tooltip>
              );
            })}
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
