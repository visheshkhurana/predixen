import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Store, AlertTriangle } from "lucide-react";

// Monthly marketplace sales and fees (Amazon today) from
// GET /api/connectors/companies/{id}/channel-sales, filled at each sync.
// Kept apart from the blended D2C month so it never overwrites website figures.

interface ChannelMonth {
  period: string; // YYYY-MM-DD (first of the month, IST)
  marketplace?: string;
  orders_shipped: number | null;
  units_shipped: number | null;
  refunded_orders: number | null;
  sales_ex_gst: number | null;
  gst_on_sales: number | null;
  promotions: number | null;
  net_sales_ex_gst: number | null;
  refunds_ex_gst: number | null;
  amazon_fees: number | null;
  fee_breakdown?: Record<string, number | null>;
  amazon_fee_pct: number | null; // fraction, e.g. 0.18
  tax_withheld: number | null;
  sponsored_ads_billed_ex_gst: number | null;
  warnings?: string[];
}

interface Channel {
  channel: string;
  provider_id: string;
  synced_at: string | null;
  months: ChannelMonth[];
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const CHANNEL_NAMES: Record<string, string> = { amazon: "Amazon" };

function monthLabel(period: string): string {
  const [y, m] = period.split("-");
  return `${MONTHS[Number(m) - 1] ?? m} ${y}`;
}

function inr(v: number | null | undefined): string {
  if (v == null) return "—";
  return `₹${Math.round(v).toLocaleString("en-IN")}`;
}

function count(v: number | null | undefined): string {
  return v == null ? "—" : Math.round(v).toLocaleString("en-IN");
}

function feeLabel(key: string): string {
  // Amazon fee types are CamelCase ("FBAPerUnitFulfillmentFee"); split for reading.
  return key.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2");
}

function Tile({ label, value, sub, testId }: { label: string; value: string; sub?: string; testId: string }) {
  return (
    <div className="rounded-md border p-3" data-testid={testId}>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-xl font-semibold tabular-nums">{value}</div>
      {sub && <div className="text-xs text-muted-foreground">{sub}</div>}
    </div>
  );
}

function ChannelBlock({ ch }: { ch: Channel }) {
  const name = CHANNEL_NAMES[ch.channel] ?? ch.channel;
  const latest = ch.months[ch.months.length - 1];
  const fees = Object.entries(latest.fee_breakdown ?? {})
    .filter(([, v]) => v != null && v !== 0)
    .slice(0, 5) as [string, number][];
  const maxSales = Math.max(1, ...ch.months.map((m) => m.net_sales_ex_gst ?? 0));
  const pct = latest.amazon_fee_pct == null ? null : latest.amazon_fee_pct * 100;

  return (
    <div className="space-y-4" data-testid={`channel-${ch.channel}`}>
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold">{name} · {monthLabel(latest.period)}</span>
        {latest.marketplace && <Badge variant="outline" className="font-normal">{latest.marketplace}</Badge>}
      </div>
      {(latest.warnings ?? []).map((w) => (
        <div key={w} className="flex items-start gap-2 text-xs text-amber-700 dark:text-amber-400">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{w}</span>
        </div>
      ))}
      <div className="grid gap-3 sm:grid-cols-4">
        <Tile
          testId="tile-channel-net-sales"
          label="Net sales (ex-GST)"
          value={inr(latest.net_sales_ex_gst)}
          sub={latest.promotions ? `after ${inr(latest.promotions)} promotions` : undefined}
        />
        <Tile
          testId="tile-channel-orders"
          label="Orders shipped"
          value={count(latest.orders_shipped)}
          sub={latest.units_shipped != null ? `${count(latest.units_shipped)} units` : undefined}
        />
        <Tile
          testId="tile-channel-fees"
          label={`${name} fees`}
          value={inr(latest.amazon_fees)}
          sub={pct == null ? undefined : `${pct.toFixed(1)}% of net sales`}
        />
        <Tile
          testId="tile-channel-refunds"
          label="Refunds (ex-GST)"
          value={inr(latest.refunds_ex_gst)}
          sub={latest.refunded_orders ? `${count(latest.refunded_orders)} orders` : undefined}
        />
      </div>
      {fees.length > 0 && (
        <div className="text-xs text-muted-foreground" data-testid="channel-fee-breakdown">
          Biggest fees: {fees.map(([k, v]) => `${feeLabel(k)} ${inr(v)}`).join(" · ")}
        </div>
      )}
      <div className="text-xs text-muted-foreground">
        GST collected {inr(latest.gst_on_sales)} · tax withheld by {name} {inr(latest.tax_withheld)}
        {latest.sponsored_ads_billed_ex_gst ? ` · Sponsored Products billed ${inr(latest.sponsored_ads_billed_ex_gst)}` : ""}
      </div>
      {ch.months.length > 1 && (
        <div className="space-y-1.5" data-testid="channel-months">
          {ch.months.map((m) => (
            <div key={m.period} className="grid grid-cols-[6rem_1fr_auto] items-center gap-3 text-sm">
              <span>{monthLabel(m.period)}</span>
              <div className="h-2 rounded-full bg-muted overflow-hidden">
                <div className="h-full bg-primary" style={{ width: `${((m.net_sales_ex_gst ?? 0) / maxSales) * 100}%` }} />
              </div>
              <span className="tabular-nums text-xs text-muted-foreground">
                {inr(m.net_sales_ex_gst)} · {count(m.orders_shipped)} orders · fees {inr(m.amazon_fees)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ChannelSalesCard({ companyId }: { companyId: number }) {
  const { data } = useQuery<{ channels: Channel[] }>({
    queryKey: [`/api/connectors/companies/${companyId}/channel-sales`],
    enabled: !!companyId,
    staleTime: 60_000,
  });
  const channels = (data?.channels ?? []).filter((c) => c.months.length > 0);
  if (channels.length === 0) return null;

  return (
    <Card data-testid="card-channel-sales">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Store className="h-5 w-5 text-muted-foreground" />
          Marketplace sales
        </CardTitle>
        <CardDescription>
          Last complete month from each connected marketplace, read-only. Shown separately from your
          website's monthly figures so neither overwrites the other.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {channels.map((ch) => (
          <ChannelBlock key={ch.provider_id} ch={ch} />
        ))}
      </CardContent>
    </Card>
  );
}
