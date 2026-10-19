// Null-safe formatting for the Alerts page. The API sends null for values it
// does not have (runway alerts have no previousValue/changePercent), and a bare
// .toFixed() on null took the whole page down.

export function isNum(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

/** "+3.2%" / "-1.0%", or null when there is no change to show. */
export function formatMetricChange(changePercent: unknown): string | null {
  if (!isNum(changePercent)) return null;
  return `${changePercent >= 0 ? "+" : ""}${changePercent.toFixed(1)}%`;
}

/** Wrap a numeric formatter so a missing value renders "N/A" instead of throwing. */
export function safeFormat(format: (v: number) => string): (v: unknown) => string {
  return (v: unknown) => (isNum(v) ? format(v) : "N/A");
}

/** Value for a metric-health card, keyed by metric name. */
export function formatAlertValue(value: unknown, metric: string): string {
  if (!isNum(value)) return "N/A";
  if (metric.includes("runway")) return `${value.toFixed(1)} mo`;
  if (metric.includes("multiple")) return `${value.toFixed(2)}x`;
  if (metric.includes("margin") || metric.includes("rate") || metric.includes("growth")) {
    return `${(value * 100).toFixed(1)}%`;
  }
  const sign = value < 0 ? "-" : "";
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(1)}K`;
  return `${sign}$${abs.toFixed(0)}`;
}
