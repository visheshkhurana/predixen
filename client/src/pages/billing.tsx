import { useSubscription, useBillingPortal } from '@/hooks/use-subscription';
import { useToast } from '@/hooks/use-toast';
import { Check, ExternalLink, Gift } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

/**
 * /billing — FounderConsole is free. There are no plans to buy, no trial and no
 * upgrade path. The page is no longer linked from the sidebar; it stays routable
 * so anyone who bought a subscription before the switch can open the Stripe
 * portal and cancel it.
 */
const INCLUDED = [
  'Every feature unlocked',
  'Unlimited companies, simulations and copilot',
  'All data connectors',
  'No credit card required',
];

export default function BillingPage() {
  const { data: sub, isLoading } = useSubscription();
  const portal = useBillingPortal();
  const { toast } = useToast();

  const openPortal = () => {
    portal.mutate(undefined, {
      onSuccess: (data) => {
        if (data.portal_url) window.location.href = data.portal_url;
      },
      onError: (err: Error) => {
        toast({ title: 'Could not open billing portal', description: err.message, variant: 'destructive' });
      },
    });
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-10" data-testid="page-billing">
      <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/[0.03] p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="h-9 w-9 rounded-lg bg-emerald-500/10 flex items-center justify-center">
            <Gift className="h-4 w-4 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white/90" data-testid="text-billing-title">
              FounderConsole is free
            </h1>
            <p className="text-xs text-white/50">All features, no credit card.</p>
          </div>
        </div>
        <ul className="space-y-2">
          {INCLUDED.map((item) => (
            <li key={item} className="flex items-start gap-2 text-sm text-white/70">
              <Check className="h-4 w-4 mt-0.5 shrink-0 text-emerald-400" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>

      {isLoading ? (
        <Skeleton className="h-20 mt-6 rounded-xl" />
      ) : sub?.legacy_paid_subscription ? (
        <div className="mt-6 rounded-xl border border-white/[0.08] bg-white/[0.02] p-5" data-testid="card-legacy-subscription">
          <p className="text-sm text-white/70">
            You still have a paid subscription from before FounderConsole became free. You do not need it any
            more — you can cancel it in the billing portal.
          </p>
          <button
            onClick={openPortal}
            disabled={portal.isPending}
            className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/[0.06] border border-white/[0.08]
              text-white/80 hover:bg-white/[0.1] text-sm font-medium disabled:opacity-50"
            data-testid="button-billing-portal"
          >
            Manage subscription
            <ExternalLink className="h-3.5 w-3.5" />
          </button>
        </div>
      ) : null}
    </div>
  );
}
