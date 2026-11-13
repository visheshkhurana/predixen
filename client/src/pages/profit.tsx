import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useFounderStore } from "@/store/founderStore";
import { formatCurrencyAbbrev } from "@/lib/utils";
import { Loader2, IndianRupee, Truck, Megaphone, Package, AlertTriangle } from "lucide-react";

// Contribution margin per order for a D2C brand (server/core/d2c.py):
// CM1 after product cost, CM2 after shipping/RTO/payments, CM3 after marketing.

interface UnitEconomics {
  delivered_orders: number;
  net_revenue: number;
  aov: number | null;
  rto_rate: number | null;
  rto_cost: number | null;
  cm1: number | null;
  cm2: number | null;
  cm3: number | null;
  cm1_pct: number | null;
  cm2_pct: number | null;
  cm3_pct: number | null;
  cm1_per_order: number | null;
  cm2_per_order: number | null;
  cm3_per_order: number | null;
  mer: number | null;
  break_even_mer: number | null;
  cac: number | null;
  missing: string[];
}

type Inputs = Record<string, number | null>;

interface AdAccount {
  source: string;
  source_label: string;
  account_id: string;
  account_name: string | null;
  currency: string | null;
  spend: number;
  spend_company: number | null;
  fx_rate: number | null;
  fx_rate_date: string | null;
  purchases: number | null;
  purchase_value: number | null;
  platform_roas: number | null;
  currency_mismatch: boolean;
}

interface AdSpend {
  company_currency: string | null;
  accounts: AdAccount[];
  sources: Array<{ source: string; source_label: string; spend: number | null; platform_purchase_value: number | null; platform_roas: number | null }>;
  total: number | null;
  currency_mismatch: Array<{ source_label: string; account_id: string; currency: string | null; spend: number }>;
  marketing_spend_source: string | null;
  manual_override: boolean;
}

interface MonthView {
  period: string;
  inputs: Inputs;
  sources: Record<string, string>;
  unit_economics: UnitEconomics | null;
  ad_spend?: AdSpend;
  missing?: string[];
  error: string | null;
}

const SOURCE_LABELS: Record<string, string> = {
  manual: "typed",
  shopify: "Shopify",
  shiprocket: "Shiprocket",
  meta_ads: "Meta Ads",
  google_ads: "Google Ads",
};

function sourceLabel(source: string): string {
  return source.split("+").map((s) => SOURCE_LABELS[s] ?? s).join(" + ");
}

type FieldKind = "money" | "count" | "percent";

const FIELD_GROUPS: Array<{ title: string; icon: typeof Package; fields: Array<{ key: string; label: string; kind: FieldKind; hint?: string }> }> = [
  {
    title: "Orders & sales",
    icon: IndianRupee,
    fields: [
      { key: "orders_shipped", label: "Orders shipped", kind: "count" },
      { key: "gross_sales", label: "Sales, ex-GST", kind: "money", hint: "Before discounts" },
      { key: "discounts", label: "Discounts", kind: "money" },
      { key: "rto_orders", label: "RTO orders", kind: "count", hint: "Shipped, came back undelivered" },
      { key: "customer_returns_value", label: "Customer returns value", kind: "money" },
      { key: "customer_returns_orders", label: "Customer returns (orders)", kind: "count" },
      { key: "cod_share", label: "COD share", kind: "percent" },
    ],
  },
  {
    title: "Product & fulfilment",
    icon: Truck,
    fields: [
      { key: "cogs", label: "COGS (landed)", kind: "money", hint: "For delivered, kept orders" },
      { key: "forward_shipping_per_order", label: "Shipping per order", kind: "money" },
      { key: "rto_shipping_per_order", label: "RTO return leg per order", kind: "money" },
      { key: "packaging_per_order", label: "Packaging per order", kind: "money" },
      { key: "return_shipping_per_order", label: "Return pickup per order", kind: "money" },
      { key: "payment_gateway_pct", label: "Gateway fee", kind: "percent", hint: "On prepaid orders" },
      { key: "cod_fee_per_order", label: "COD fee per order", kind: "money" },
    ],
  },
  {
    title: "Marketing",
    icon: Megaphone,
    fields: [
      { key: "marketing_spend", label: "Marketing spend", kind: "money" },
      { key: "new_customers", label: "New customers", kind: "count" },
    ],
  },
];

const MISSING_COPY: Record<string, string> = {
  cogs: "Add COGS to see CM1",
  forward_shipping_per_order: "Add shipping per order to see CM2",
  rto_shipping_per_order: "Add the RTO return-leg cost to see CM2",
  payment_costs: "Add COD share and gateway/COD fees to see CM2",
  marketing_spend: "Add marketing spend to see CM3",
};

function currentMonth(): string {
  const d = new Date();
  d.setDate(1);
  d.setMonth(d.getMonth() - 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function pct(v: number | null | undefined): string {
  return v == null ? "—" : `${(v * 100).toFixed(1)}%`;
}

function money(v: number | null | undefined, currency = "USD"): string {
  if (v == null) return "—";
  try {
    return formatCurrencyAbbrev(v, currency);
  } catch {
    return `${currency} ${Math.round(v).toLocaleString()}`; // unknown ISO code
  }
}

function ratio(v: number | null | undefined): string {
  return v == null ? "—" : `${v.toFixed(2)}x`;
}

function toForm(inputs: Inputs | undefined): Record<string, string> {
  const out: Record<string, string> = {};
  for (const group of FIELD_GROUPS) {
    for (const f of group.fields) {
      const v = inputs?.[f.key];
      out[f.key] = v == null ? "" : f.kind === "percent" ? String(+(v * 100).toFixed(2)) : String(v);
    }
  }
  return out;
}

function fromForm(form: Record<string, string>, original: Record<string, string>): Inputs {
  // Only send what changed, so a sync-filled field the founder did not touch
  // stays owned by its source.
  const body: Inputs = {};
  for (const group of FIELD_GROUPS) {
    for (const f of group.fields) {
      if (form[f.key] === original[f.key]) continue;
      const raw = form[f.key].trim();
      if (raw === "") {
        body[f.key] = null;
        continue;
      }
      const n = Number(raw);
      if (!Number.isFinite(n)) continue;
      body[f.key] = f.kind === "percent" ? n / 100 : f.kind === "count" ? Math.round(n) : n;
    }
  }
  return body;
}

function MarginStep({ label, perOrder, share, total, currency }: { label: string; perOrder: number | null; share: number | null; total: number | null; currency: string }) {
  const width = share == null ? 0 : Math.max(0, Math.min(100, share * 100));
  const negative = (perOrder ?? 0) < 0;
  return (
    <div className="space-y-1.5" data-testid={`profit-${label.toLowerCase()}`}>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm font-medium">{label}</span>
        <span className={`text-lg font-semibold tabular-nums ${negative ? "text-destructive" : ""}`}>
          {perOrder == null ? "—" : `${money(perOrder, currency)} / order`}
        </span>
      </div>
      <div className="h-2 rounded-full bg-muted overflow-hidden">
        <div className={`h-full ${negative ? "bg-destructive" : "bg-primary"}`} style={{ width: `${width}%` }} />
      </div>
      <div className="flex justify-between text-xs text-muted-foreground tabular-nums">
        <span>{pct(share)} of net revenue</span>
        <span>{money(total, currency)} total</span>
      </div>
    </div>
  );
}

function AdSpendCard({ ad, ue, currency }: { ad: AdSpend | undefined; ue: UnitEconomics | null; currency: string }) {
  const meta = ad?.sources.find((s) => s.source === "meta_ads");
  const mer = ue?.mer ?? null;
  const breakEven = ue?.break_even_mer ?? null;
  const belowBreakEven = mer != null && breakEven != null && mer < breakEven;
  return (
    <Card data-testid="card-ad-spend">
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Megaphone className="h-5 w-5 text-muted-foreground" />Ad spend & efficiency</CardTitle>
        <CardDescription>
          MER divides your store's net revenue by all marketing spend. Meta ROAS is Meta's own attribution: it counts sales Meta thinks its ads caused, overlaps with other channels, and is not revenue.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-md border p-3" data-testid="tile-mer">
            <div className="text-xs text-muted-foreground">MER (from store net revenue)</div>
            <div className={`text-xl font-semibold tabular-nums ${belowBreakEven ? "text-destructive" : ""}`}>{ratio(mer)}</div>
          </div>
          <div className="rounded-md border p-3" data-testid="tile-meta-roas">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              Meta ROAS <Badge variant="outline" className="h-4 px-1 text-[10px] font-normal">platform-reported</Badge>
            </div>
            <div className="text-xl font-semibold tabular-nums">{ratio(meta?.platform_roas)}</div>
          </div>
          <div className="rounded-md border p-3" data-testid="tile-break-even-mer">
            <div className="text-xs text-muted-foreground">Break-even MER</div>
            <div className="text-xl font-semibold tabular-nums">{ratio(breakEven)}</div>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          {breakEven == null
            ? "Break-even MER needs CM2 (product, shipping and payment costs)."
            : belowBreakEven
              ? "MER is below break-even: marketing is costing more than the margin it brings in (CM3 is negative)."
              : `Below ${ratio(breakEven)} MER, marketing costs more than the margin it brings in.`}
        </p>

        {ad && ad.accounts.length > 0 ? (
          <div className="space-y-2">
            <div className="text-sm font-semibold">Spend by source</div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="table-ad-spend">
                <thead className="text-xs text-muted-foreground">
                  <tr className="border-b text-left">
                    <th className="py-1.5 pr-3 font-normal">Account</th>
                    <th className="py-1.5 pr-3 text-right font-normal">Spend</th>
                    <th className="py-1.5 text-right font-normal">Platform ROAS</th>
                  </tr>
                </thead>
                <tbody>
                  {ad.accounts.map((a) => (
                    <tr key={`${a.source}-${a.account_id}`} className="border-b last:border-0">
                      <td className="py-1.5 pr-3">
                        <div>{a.account_name || a.account_id}</div>
                        <div className="text-xs text-muted-foreground">{a.source_label} · {a.account_id}</div>
                      </td>
                      <td className="py-1.5 pr-3 text-right tabular-nums">
                        <div>{money(a.spend, a.currency || currency)}</div>
                        {a.currency && a.currency !== currency && (
                          <div className="text-xs text-muted-foreground">
                            {a.spend_company != null ? `≈ ${money(a.spend_company, currency)} at ${a.fx_rate?.toFixed(4)} (${a.fx_rate_date})` : "not converted"}
                          </div>
                        )}
                      </td>
                      <td className="py-1.5 text-right tabular-nums">{ratio(a.platform_roas)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="font-semibold">
                    <td className="pt-2">Total ad spend</td>
                    <td className="pt-2 pr-3 text-right tabular-nums">{money(ad.total, currency)}</td>
                    <td />
                  </tr>
                </tfoot>
              </table>
            </div>
            {ad.currency_mismatch.length > 0 && (
              <div className="flex items-start gap-2 rounded-md border border-destructive/40 p-3 text-xs" data-testid="ad-currency-mismatch">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
                <span>
                  {ad.currency_mismatch.map((m) => `${m.source_label} ${m.account_id} is billed in ${m.currency}`).join("; ")}, and your company currency is {currency}. No exchange rate is stored for this month, so ad spend is not added up (CM3 and MER stay empty rather than mixing currencies). Type the month's total marketing spend in {currency} below, or switch the ad account currency.
                </span>
              </div>
            )}
            {ad.manual_override && (
              <p className="text-xs text-muted-foreground">
                You typed this month's marketing spend, so CM3 and MER use your number, not the ad platforms' total. Clear the field to use the total.
              </p>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Connect <Link href="/integrations" className="underline">Meta Ads</Link> to bring in monthly ad spend, or type marketing spend below.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export default function ProfitPage() {
  const { currentCompany } = useFounderStore();
  const { toast } = useToast();
  const companyId = currentCompany?.id;
  const currency = (currentCompany?.currency || "USD").toUpperCase();
  const [period, setPeriod] = useState(currentMonth());

  const { data, isLoading } = useQuery<{ months: MonthView[] }>({
    queryKey: ["/api/companies", companyId, "d2c/months"],
    enabled: !!companyId,
  });
  const months = data?.months ?? [];
  const selected = months.find((m) => m.period.startsWith(period));
  const original = useMemo(() => toForm(selected?.inputs), [selected]);
  const [form, setForm] = useState<Record<string, string>>(original);
  useEffect(() => setForm(original), [original]);

  const save = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("PUT", `/api/companies/${companyId}/d2c/months/${period}`, fromForm(form, original));
      return (await res.json()) as MonthView;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/companies", companyId, "d2c/months"] });
      toast({ title: "Saved", description: `Inputs for ${period} updated.` });
    },
    onError: (err: Error) => toast({ title: "Not saved", description: err.message, variant: "destructive" }),
  });

  if (!companyId) {
    return <div className="p-6 text-muted-foreground">Select a company to see its profit per order.</div>;
  }

  const ue = selected?.unit_economics ?? null;
  const missing = ue?.missing ?? selected?.missing ?? [];
  const adCurrency = selected?.ad_spend?.company_currency || currency;

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight" data-testid="text-profit-title">Profit per order</h1>
        <p className="text-sm text-muted-foreground">
          What you keep on a delivered order after product cost (CM1), shipping, RTO and payments (CM2), and marketing (CM3). All figures ex-GST.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <Label htmlFor="profit-period">Month</Label>
          <Input id="profit-period" type="month" value={period} onChange={(e) => setPeriod(e.target.value)} className="w-44" data-testid="input-profit-period" />
        </div>
        {months.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {months.map((m) => (
              <Button key={m.period} size="sm" variant={m.period.startsWith(period) ? "default" : "outline"} onClick={() => setPeriod(m.period.slice(0, 7))}>
                {m.period.slice(0, 7)}
              </Button>
            ))}
          </div>
        )}
      </div>

      {isLoading ? (
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      ) : (
        <div className="grid gap-6 lg:grid-cols-5">
          <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Contribution margin</CardTitle>
              <CardDescription>
                {ue ? `${ue.delivered_orders.toLocaleString("en-IN")} delivered orders · AOV ${money(ue.aov, currency)}` : "Add orders and sales to start"}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <MarginStep label="CM1" perOrder={ue?.cm1_per_order ?? null} share={ue?.cm1_pct ?? null} total={ue?.cm1 ?? null} currency={currency} />
              <MarginStep label="CM2" perOrder={ue?.cm2_per_order ?? null} share={ue?.cm2_pct ?? null} total={ue?.cm2 ?? null} currency={currency} />
              <MarginStep label="CM3" perOrder={ue?.cm3_per_order ?? null} share={ue?.cm3_pct ?? null} total={ue?.cm3 ?? null} currency={currency} />
              <div className="grid grid-cols-2 gap-3 border-t pt-4 text-sm">
                <div><div className="text-muted-foreground">RTO rate</div><div className="font-semibold tabular-nums">{pct(ue?.rto_rate)}</div></div>
                <div><div className="text-muted-foreground">Lost to RTO</div><div className="font-semibold tabular-nums">{money(ue?.rto_cost, currency)}</div></div>
                <div><div className="text-muted-foreground">MER (blended ROAS)</div><div className="font-semibold tabular-nums">{ratio(ue?.mer)}</div></div>
                <div><div className="text-muted-foreground">CAC</div><div className="font-semibold tabular-nums">{money(ue?.cac, currency)}</div></div>
              </div>
              {missing.length > 0 && (
                <ul className="space-y-1 rounded-md bg-muted/50 p-3 text-xs text-muted-foreground" data-testid="profit-missing">
                  {missing.map((m) => <li key={m}>{MISSING_COPY[m] ?? `Add ${m.replace(/_/g, " ")}`}</li>)}
                </ul>
              )}
              {selected?.error && <p className="text-sm text-destructive">{selected.error}</p>}
            </CardContent>
          </Card>
          <AdSpendCard ad={selected?.ad_spend} ue={ue} currency={adCurrency} />
          </div>

          <Card className="lg:col-span-3">
            <CardHeader>
              <CardTitle>Inputs for {period}</CardTitle>
              <CardDescription>
                Numbers from <Link href="/integrations" className="underline">Shopify, Shiprocket and Meta Ads</Link> fill in automatically. Anything you type here is kept, even after the next sync.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form
                className="space-y-6"
                onSubmit={(e) => {
                  e.preventDefault();
                  save.mutate();
                }}
              >
                {FIELD_GROUPS.map((group) => (
                  <fieldset key={group.title} className="space-y-3">
                    <legend className="flex items-center gap-2 text-sm font-semibold">
                      <group.icon className="h-4 w-4 text-muted-foreground" />
                      {group.title}
                    </legend>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {group.fields.map((f) => (
                        <div key={f.key} className="space-y-1">
                          <Label htmlFor={`d2c-${f.key}`} className="flex items-center gap-2 text-xs">
                            {f.label}
                            {f.kind === "percent" && <span className="text-muted-foreground">(%)</span>}
                            {selected?.sources[f.key] && (
                              <Badge variant="secondary" className="h-4 px-1.5 text-[10px] font-normal">{sourceLabel(selected.sources[f.key])}</Badge>
                            )}
                          </Label>
                          <Input
                            id={`d2c-${f.key}`}
                            inputMode="decimal"
                            value={form[f.key] ?? ""}
                            onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                            placeholder={f.hint}
                            data-testid={`input-d2c-${f.key}`}
                          />
                        </div>
                      ))}
                    </div>
                  </fieldset>
                ))}
                <Button type="submit" disabled={save.isPending} data-testid="button-profit-save">
                  {save.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Save {period}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
