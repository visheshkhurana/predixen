import { ArrowRight, FlaskConical } from 'lucide-react';
import { formatCurrencyAbbrev } from '@/lib/utils';
import { deriveSampleInsight, type SampleInsight } from '@/lib/sampleCompany';

function money(value: number, currency = 'USD') {
  return formatCurrencyAbbrev(value, currency);
}

type Props = {
  insight?: SampleInsight;
  currency?: string;
};

/**
 * Shows the sample inputs next to the calculated first insight so a new
 * user can see why the dashboard numbers appeared.
 */
export function SampleInsightExplainer({ insight, currency = 'USD' }: Props) {
  const shown = insight ?? deriveSampleInsight();
  const runway =
    shown.outputs.runway_months == null
      ? 'sustainable'
      : `${shown.outputs.runway_months} months`;

  return (
    <div
      className="rounded-xl border border-amber-500/30 bg-amber-500/[0.06] p-4 md:p-5"
      data-testid="card-sample-insight"
    >
      <div className="flex items-center gap-2 mb-3">
        <FlaskConical className="h-4 w-4 text-amber-400 shrink-0" />
        <p className="text-sm font-semibold text-amber-200">How this sample insight was calculated</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto_1fr] gap-3 items-center">
        <div className="rounded-lg bg-background/40 p-3 space-y-1.5">
          <p className="text-[11px] uppercase tracking-wider text-muted-foreground">Sample inputs</p>
          <p className="text-sm" data-testid="text-sample-input-revenue">
            Revenue {money(shown.inputs.monthly_revenue, currency)}/mo
          </p>
          <p className="text-sm" data-testid="text-sample-input-expenses">
            Expenses {money(shown.inputs.monthly_expenses, currency)}/mo
          </p>
          <p className="text-sm" data-testid="text-sample-input-cash">
            Cash {money(shown.inputs.cash_balance, currency)}
          </p>
        </div>
        <ArrowRight className="h-4 w-4 text-amber-400/80 hidden sm:block justify-self-center" />
        <div className="rounded-lg bg-background/40 p-3 space-y-1.5">
          <p className="text-[11px] uppercase tracking-wider text-muted-foreground">Calculated insight</p>
          <p className="text-sm" data-testid="text-sample-output-burn">
            Burn {money(shown.outputs.monthly_burn, currency)}/mo
          </p>
          <p className="text-sm font-medium" data-testid="text-sample-output-runway">
            Runway {runway}
          </p>
          <p className="text-[11px] text-muted-foreground">burn = expenses − revenue · runway = cash ÷ burn</p>
        </div>
      </div>
    </div>
  );
}
