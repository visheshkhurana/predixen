import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Wallet } from "lucide-react";

// Prepaid shipping wallet balance (Shiprocket) from
// GET /api/connectors/companies/{id}/shipping-wallet, refreshed at each sync.

interface ShippingWallet {
  provider_id: string;
  balance: number;
  currency: string;
  as_of: string | null;
}

const NAMES: Record<string, string> = { shiprocket: "Shiprocket" };

function inr(v: number): string {
  return `₹${Math.abs(Math.round(v)).toLocaleString("en-IN")}`;
}

function asOf(iso: string | null): string | undefined {
  if (!iso) return undefined;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? undefined : d.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

export function ShippingWalletCard({ companyId }: { companyId: number }) {
  const { data } = useQuery<{ wallets: ShippingWallet[] }>({
    queryKey: [`/api/connectors/companies/${companyId}/shipping-wallet`],
    enabled: !!companyId,
    staleTime: 60_000,
  });
  const wallets = data?.wallets ?? [];
  if (wallets.length === 0) return null;

  return (
    <Card data-testid="card-shipping-wallet">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Wallet className="h-5 w-5 text-muted-foreground" />
          Shipping wallet
        </CardTitle>
        <CardDescription>
          Prepaid balance your shipping partner deducts freight from, as of the last sync.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-3">
        {wallets.map((w) => {
          const owed = w.balance < 0;
          const when = asOf(w.as_of);
          return (
            <div key={w.provider_id} className="rounded-md border p-3" data-testid={`wallet-${w.provider_id}`}>
              <div className="text-xs text-muted-foreground">{NAMES[w.provider_id] ?? w.provider_id}</div>
              <div className={`text-xl font-semibold tabular-nums ${owed ? "text-red-600 dark:text-red-400" : ""}`}>
                {owed ? `−${inr(w.balance)}` : inr(w.balance)}
              </div>
              <div className="text-xs text-muted-foreground">
                {owed ? `You owe ${NAMES[w.provider_id] ?? "them"} ${inr(w.balance)}` : "Available for shipping"}
                {when ? ` · ${when}` : ""}
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
