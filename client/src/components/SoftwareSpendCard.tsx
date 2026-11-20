import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCurrencyAbbrev } from "@/lib/utils";
import { AppWindow, AlertTriangle } from "lucide-react";

// Software spend reported by connectors (server/services/software_spend.py):
// 1Password seat cost, plus software-category card spend from Ramp and Brex.
// Kept apart from opex, so it never replaces the company's burn figures.

interface VendorLine {
  vendor: string;
  source: string;
  basis: "card" | "seats" | string;
  amount: number;
  currency: string | null;
  amount_company: number | null;
  transactions: number | null;
  seats: number | null;
  active_users: number | null;
  unused_seats: number | null;
}

interface SpendMonth {
  period: string;
  total_company: number;
  unconverted: { vendor: string; amount: number; currency: string | null }[];
  vendors: VendorLine[];
}

interface SoftwareSpendResponse {
  currency: string | null;
  months: SpendMonth[];
  sources: string[];
}

const SOURCE_LABELS: Record<string, string> = { onepassword: "1Password", ramp: "Ramp", brex: "Brex" };

function money(v: number | null | undefined, currency: string): string {
  if (v == null) return "—";
  try {
    return formatCurrencyAbbrev(v, currency);
  } catch {
    return `${currency} ${Math.round(v).toLocaleString()}`;
  }
}

function monthLabel(period: string): string {
  const d = new Date(`${period}T00:00:00`);
  return Number.isNaN(d.getTime()) ? period : d.toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

export function SoftwareSpendCard({ companyId }: { companyId: number }) {
  const { data } = useQuery<SoftwareSpendResponse>({
    queryKey: [`/api/connectors/companies/${companyId}/software-spend`],
    enabled: !!companyId,
    staleTime: 60_000,
  });
  if (!data || data.months.length === 0) return null;

  const currency = data.currency || "USD";
  const latest = data.months[0];
  const unused = latest.vendors.filter((v) => (v.unused_seats ?? 0) > 0);

  return (
    <Card data-testid="card-software-spend">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AppWindow className="h-5 w-5 text-muted-foreground" />
          Software spend
        </CardTitle>
        <CardDescription>
          From {data.sources.map((s) => SOURCE_LABELS[s] || s).join(", ")}. Card lines only count software bought on that card,
          so this is a floor, not your full software bill. It is shown here and not added to opex.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-3">
          {data.months.slice(0, 3).map((m) => (
            <div key={m.period} className="rounded-md border p-3 min-w-[8rem]" data-testid={`tile-software-${m.period}`}>
              <div className="text-xs text-muted-foreground">{monthLabel(m.period)}</div>
              <div className="text-xl font-semibold tabular-nums">{money(m.total_company, currency)}</div>
            </div>
          ))}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="table-software-spend">
            <thead className="text-xs text-muted-foreground">
              <tr className="border-b text-left">
                <th className="py-1.5 pr-3 font-normal">Vendor · {monthLabel(latest.period)}</th>
                <th className="py-1.5 pr-3 font-normal">Basis</th>
                <th className="py-1.5 text-right font-normal">Amount</th>
              </tr>
            </thead>
            <tbody>
              {latest.vendors.map((v) => (
                <tr key={`${v.source}-${v.vendor}`} className="border-b last:border-0">
                  <td className="py-1.5 pr-3">
                    <div>{v.vendor}</div>
                    <div className="text-xs text-muted-foreground">{SOURCE_LABELS[v.source] || v.source}</div>
                  </td>
                  <td className="py-1.5 pr-3 text-xs text-muted-foreground">
                    {v.basis === "seats" ? (
                      <span>
                        {v.seats != null ? `${v.seats} seats` : "active users"}
                        {v.active_users != null && ` · ${v.active_users} active`}
                      </span>
                    ) : (
                      <span>{v.transactions ?? 0} card {v.transactions === 1 ? "charge" : "charges"}</span>
                    )}
                  </td>
                  <td className="py-1.5 text-right tabular-nums">
                    <div>{money(v.amount, v.currency || currency)}</div>
                    {v.currency && v.currency !== currency && (
                      <div className="text-xs text-muted-foreground">
                        {v.amount_company != null ? `≈ ${money(v.amount_company, currency)}` : "not converted"}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {unused.length > 0 && (
          <div className="flex flex-wrap gap-2" data-testid="software-unused-seats">
            {unused.map((v) => (
              <Badge key={v.vendor} variant="outline">
                {v.vendor}: {v.unused_seats} unused {v.unused_seats === 1 ? "seat" : "seats"}
              </Badge>
            ))}
          </div>
        )}

        {latest.unconverted.length > 0 && (
          <div className="flex items-start gap-2 rounded-md border border-destructive/40 p-3 text-xs" data-testid="software-unconverted">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
            <span>
              {latest.unconverted.map((u) => `${u.vendor} (${u.currency})`).join(", ")} {latest.unconverted.length === 1 ? "is" : "are"} billed
              in another currency with no stored exchange rate for the month, so {latest.unconverted.length === 1 ? "it is" : "they are"} not in the total.
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
