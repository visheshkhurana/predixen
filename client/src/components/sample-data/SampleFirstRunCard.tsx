import { ArrowRight, FlaskConical, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { formatCurrencyAbbrev } from '@/lib/utils';
import { deriveSampleInsight } from '@/lib/sampleCompany';

type Props = {
  onStart: () => void;
  loading?: boolean;
};

/**
 * Primary labelled path on /onboarding: reach a first insight without
 * entering real financials, with the input → output pair visible up front.
 */
export function SampleFirstRunCard({ onStart, loading = false }: Props) {
  const insight = deriveSampleInsight();
  const money = (n: number) => formatCurrencyAbbrev(n, 'USD');

  return (
    <Card
      className="border-amber-500/40 bg-amber-500/[0.06]"
      data-testid="card-sample-first-run"
    >
      <CardContent className="pt-5 pb-5 space-y-3">
        <div className="flex items-start gap-2">
          <FlaskConical className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1 min-w-0">
            <p className="text-sm font-semibold">See a first insight with sample data</p>
            <p className="text-xs text-muted-foreground">
              Simulated numbers — not your company. You can replace them anytime.
            </p>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto_1fr] gap-2 items-center text-xs">
          <p data-testid="text-sample-preview-inputs">
            <span className="text-muted-foreground">Inputs: </span>
            {money(insight.inputs.cash_balance)} cash · {money(insight.inputs.monthly_revenue)}/mo revenue · {money(insight.inputs.monthly_expenses)}/mo expenses
          </p>
          <ArrowRight className="h-3.5 w-3.5 text-amber-400/80 hidden sm:block justify-self-center" />
          <p data-testid="text-sample-preview-outputs">
            <span className="text-muted-foreground">Insight: </span>
            {money(insight.outputs.monthly_burn)}/mo burn · {insight.outputs.runway_months} months runway
          </p>
        </div>
        <Button
          type="button"
          onClick={onStart}
          disabled={loading}
          className="w-full sm:w-auto"
          data-testid="button-load-sample"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Loading sample insight…
            </>
          ) : (
            <>
              See a sample insight
              <ArrowRight className="w-4 h-4 ml-2" />
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
