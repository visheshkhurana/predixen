import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import { Info, Database, Calculator, Clock, GitBranch } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

export interface KPIProvenanceData {
  name: string;
  definition: string;
  formula?: string;
  source: 'truth_scan' | 'simulation' | 'manual' | 'computed' | 'imported';
  sourceLabel?: string;
  timestamp?: string;
  runId?: string;
  scenarioId?: number;
  scenarioName?: string;
  confidence?: number;
}

interface KPIProvenanceProps {
  children: React.ReactNode;
  provenance: KPIProvenanceData;
  showIcon?: boolean;
}

const sourceConfig = {
  truth_scan: { label: 'Truth Scan', color: 'text-emerald-400', bgColor: 'bg-emerald-500/10' },
  simulation: { label: 'Simulation', color: 'text-blue-400', bgColor: 'bg-blue-500/10' },
  manual: { label: 'Manual Entry', color: 'text-amber-400', bgColor: 'bg-amber-500/10' },
  computed: { label: 'Computed', color: 'text-purple-400', bgColor: 'bg-purple-500/10' },
  imported: { label: 'Imported', color: 'text-cyan-400', bgColor: 'bg-cyan-500/10' },
};

export function KPIProvenance({ children, provenance, showIcon = true }: KPIProvenanceProps) {
  const sourceInfo = sourceConfig[provenance.source];
  const timeAgo = provenance.timestamp 
    ? formatDistanceToNow(new Date(provenance.timestamp), { addSuffix: true })
    : null;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div className="inline-flex items-center gap-1 cursor-help group" data-testid={`kpi-provenance-${provenance.name.toLowerCase().replace(/\s/g, '-')}`}>
          {children}
          {showIcon && (
            <Info className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          )}
        </div>
      </TooltipTrigger>
      <TooltipContent side="bottom" className="max-w-xs p-3" data-testid="kpi-provenance-tooltip">
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold text-sm">{provenance.name}</span>
            <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${sourceInfo.bgColor} ${sourceInfo.color}`}>
              {provenance.sourceLabel || sourceInfo.label}
            </Badge>
          </div>
          
          <p className="text-xs text-muted-foreground">{provenance.definition}</p>
          
          {provenance.formula && (
            <div className="flex items-start gap-1.5 text-xs">
              <Calculator className="h-3 w-3 mt-0.5 text-muted-foreground shrink-0" />
              <code className="font-mono text-[10px] bg-muted px-1 py-0.5 rounded break-all">
                {provenance.formula}
              </code>
            </div>
          )}
          
          <div className="flex items-center gap-3 text-[10px] text-muted-foreground pt-1 border-t border-border/50">
            <div className="flex items-center gap-1">
              <Database className={`h-3 w-3 ${sourceInfo.color}`} />
              <span>{provenance.sourceLabel || sourceInfo.label}</span>
            </div>
            
            {timeAgo && (
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                <span>{timeAgo}</span>
              </div>
            )}
            
            {provenance.runId && (
              <div className="flex items-center gap-1">
                <GitBranch className="h-3 w-3" />
                <span className="font-mono">{provenance.runId.slice(0, 8)}</span>
              </div>
            )}
          </div>
          
          {provenance.confidence !== undefined && (
            <div className="text-[10px] text-muted-foreground">
              Confidence: {provenance.confidence}%
            </div>
          )}
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

export const KPI_DEFINITIONS: Record<string, Omit<KPIProvenanceData, 'timestamp' | 'runId' | 'scenarioId' | 'scenarioName' | 'confidence' | 'sourceLabel'>> = {
  runway: {
    name: 'Runway',
    definition: 'The number of months your company can operate before running out of cash.',
    formula: 'Cash Balance / Monthly Net Burn',
    source: 'truth_scan',
  },
  survival_probability: {
    name: 'Survival Probability',
    definition: 'The likelihood your company will have positive cash at horizon, based on Monte Carlo simulation.',
    formula: 'Surviving Simulations / Total Simulations × 100%',
    source: 'simulation',
  },
  net_burn: {
    name: 'Net Burn Rate',
    definition: 'Monthly cash consumption after accounting for revenue. Negative = burning cash, Positive = cash positive.',
    formula: 'Revenue - Total Expenses',
    source: 'truth_scan',
  },
  gross_burn: {
    name: 'Gross Burn Rate',
    definition: 'Total monthly operating expenses before accounting for revenue.',
    formula: 'Payroll + Marketing + Operating + COGS + Other OpEx',
    source: 'truth_scan',
  },
  cash_balance: {
    name: 'Cash Balance',
    definition: 'Current available cash on hand.',
    source: 'truth_scan',
  },
  monthly_revenue: {
    name: 'Monthly Revenue',
    definition: 'Total revenue generated in the current month.',
    source: 'truth_scan',
  },
  growth_rate: {
    name: 'Growth Rate',
    definition: 'Month-over-month revenue growth rate.',
    formula: '(Current Month Revenue / Previous Month Revenue - 1) × 100%',
    source: 'truth_scan',
  },
  p10_runway: {
    name: 'P10 Runway',
    definition: 'Pessimistic runway estimate (10th percentile). 90% of simulations show at least this runway.',
    source: 'simulation',
  },
  p50_runway: {
    name: 'P50 Runway',
    definition: 'Median runway estimate (50th percentile). Half of simulations show more, half show less.',
    source: 'simulation',
  },
  p90_runway: {
    name: 'P90 Runway',
    definition: 'Optimistic runway estimate (90th percentile). Only 10% of simulations show this or more.',
    source: 'simulation',
  },
  burn_multiple: {
    name: 'Burn Multiple',
    definition: 'Efficiency metric showing how much you spend to generate each dollar of new ARR.',
    formula: 'Net Burn / Net New ARR',
    source: 'computed',
  },
  churn_rate: {
    name: 'Churn Rate',
    definition: 'Percentage of customers or revenue lost each month.',
    formula: 'Lost Customers / Starting Customers × 100%',
    source: 'truth_scan',
  },
  cac: {
    name: 'CAC',
    definition: 'Customer Acquisition Cost - the total cost to acquire a new customer.',
    formula: 'Total Sales & Marketing Spend / New Customers Acquired',
    source: 'truth_scan',
  },
  gross_margin: {
    name: 'Gross Margin',
    definition: 'Percentage of revenue remaining after subtracting cost of goods sold.',
    formula: '(Revenue - COGS) / Revenue × 100%',
    source: 'truth_scan',
  },
};
