/**
 * An empty month on the Profit page starts from the sales and product cost
 * the founder already gave us (onboarding or an upload). The values only
 * fill the form; nothing is saved until the founder presses Save.
 */
export interface BaselineSuggestion {
  gross_sales: number | null;
  cogs: number | null;
  period: string;
}

export function monthIsEmpty(inputs: Record<string, number | null> | undefined): boolean {
  if (!inputs) return true;
  return Object.values(inputs).every((v) => v == null);
}

/** Form strings to prefill, or an empty object when nothing should change. */
export function prefillFromBaseline(
  inputs: Record<string, number | null> | undefined,
  baseline: BaselineSuggestion | null | undefined,
): Record<string, string> {
  if (!baseline || !monthIsEmpty(inputs)) return {};
  const out: Record<string, string> = {};
  if (baseline.gross_sales != null && baseline.gross_sales > 0) out.gross_sales = String(Math.round(baseline.gross_sales));
  if (baseline.cogs != null && baseline.cogs > 0 && out.gross_sales) out.cogs = String(Math.round(baseline.cogs));
  return out;
}
