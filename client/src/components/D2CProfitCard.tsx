import { useQuery } from '@tanstack/react-query';
import { Link } from 'wouter';
import { ArrowRight, IndianRupee, Coins } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { formatCurrencyAbbrev } from '@/lib/utils';
import { latestProfitSummary } from '@/lib/d2cProfitSummary';

/**
 * Profit per order on the dashboard for goods businesses: the D2C core number
 * (CM2/CM3 per delivered order) or, before any month is entered, the way in.
 */
export function D2CProfitCard({ companyId, currency }: { companyId: number; currency: string }) {
  const { data, isLoading } = useQuery<{ months: any[] }>({
    queryKey: ['/api/companies', companyId, 'd2c/months'],
    enabled: !!companyId,
  });
  if (isLoading) return null;
  const summary = latestProfitSummary(data?.months);
  const money = (v: number | null) => (v === null ? '—' : formatCurrencyAbbrev(v, currency));
  const pct = (v: number | null) => (v === null ? '' : ` (${(v * 100).toFixed(1)}% of net revenue)`);

  return (
    <Card data-testid="card-d2c-profit">
      <CardContent className="p-5 flex flex-col md:flex-row md:items-center gap-4 justify-between">
        <div className="flex items-start gap-3 min-w-0">
          {currency === 'INR' ? (
            <IndianRupee className="h-5 w-5 text-primary shrink-0 mt-0.5" aria-hidden="true" />
          ) : (
            <Coins className="h-5 w-5 text-primary shrink-0 mt-0.5" aria-hidden="true" />
          )}
          {summary.state === 'ready' ? (
            <div className="min-w-0">
              <p className="text-sm font-medium">Profit per order, {summary.period}</p>
              <p className="text-sm text-muted-foreground" data-testid="text-d2c-profit-summary">
                CM2 {money(summary.cm2PerOrder)} per delivered order{pct(summary.cm2Pct)}
                {' · '}CM3 after marketing {money(summary.cm3PerOrder)}{pct(summary.cm3Pct)}
              </p>
            </div>
          ) : (
            <div className="min-w-0">
              <p className="text-sm font-medium">
                {summary.state === 'incomplete'
                  ? `Finish ${summary.period} to see what each order earns`
                  : 'See what each order really earns'}
              </p>
              <p className="text-sm text-muted-foreground">
                Add last month's orders, sales and shipping (or connect Shopify and Shiprocket) to get CM1, CM2
                and CM3 per order after RTO, payments and ads.
              </p>
            </div>
          )}
        </div>
        <Button asChild variant={summary.state === 'ready' ? 'outline' : 'default'} size="sm" className="shrink-0">
          <Link href="/profit" data-testid="link-d2c-profit">
            {summary.state === 'ready' ? 'Open Profit per order' : 'Add order numbers'}
            <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
