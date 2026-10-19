/**
 * /embed/survival's CTA opens /survival-simulator?cash=&burn=&revenue=. The simulator
 * used to ignore the query string, so the visitor re-typed what they had just entered.
 *
 * `burn` is the widget's gross monthly burn, i.e. the simulator's monthly expenses.
 * Only finite, non-negative numbers are taken; anything else keeps the default.
 */
export interface SimulatorPrefill {
  cash_on_hand?: number;
  monthly_expenses?: number;
  monthly_revenue?: number;
}

const PARAMS: Record<string, keyof SimulatorPrefill> = {
  cash: "cash_on_hand",
  burn: "monthly_expenses",
  expenses: "monthly_expenses",
  revenue: "monthly_revenue",
};

export function simulatorPrefillFromSearch(search: string): SimulatorPrefill {
  const params = new URLSearchParams(search);
  const out: SimulatorPrefill = {};
  for (const [param, field] of Object.entries(PARAMS)) {
    const raw = params.get(param);
    if (raw === null || raw.trim() === "") continue;
    const n = Number(raw);
    if (Number.isFinite(n) && n >= 0) out[field] = n;
  }
  return out;
}
