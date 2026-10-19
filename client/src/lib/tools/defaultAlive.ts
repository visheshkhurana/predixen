/**
 * Paul Graham's "default alive" test, shared by /default-alive and its test.
 * Moved out of the page so the verdict can be unit tested.
 */

export const HORIZON = 60;

export type Verdict = {
  alive: boolean;
  profitableMonth: number | null;
  outOfCashMonth: number | null;
  lowestCash: number;
  series: { month: number; cash: number; rev: number; exp: number }[];
};

/**
 * Paul Graham's default alive test: at your current growth rate and current
 * expenses, do you reach profitability before the money runs out?
 *
 * The honest caveat, which most calculators of this shape omit: PG's original
 * framing holds expenses flat, and almost nobody's expenses stay flat while
 * revenue compounds. The expenseGrowth toggle exists so a founder can see how
 * fragile the "alive" verdict is once hiring is included — it very often flips.
 */
export function computeVerdict(
  cash: number,
  revenue: number,
  expenses: number,
  growthPct: number,
  expenseGrowthPct: number,
): Verdict {
  const g = growthPct / 100;
  const eg = expenseGrowthPct / 100;

  let remaining = cash;
  let profitableMonth: number | null = null;
  let outOfCashMonth: number | null = null;
  let lowestCash = cash;
  const series: Verdict["series"] = [];

  for (let m = 0; m <= HORIZON; m++) {
    const rev = revenue * Math.pow(1 + g, m);
    const exp = expenses * Math.pow(1 + eg, m);

    if (profitableMonth === null && rev >= exp) profitableMonth = m;

    series.push({ month: m, cash: remaining, rev, exp });
    if (remaining < lowestCash) lowestCash = remaining;
    // Out of cash: the balance went negative, or it is empty and this month still
    // burns. A profitable company with $0 in the bank is not out of cash — the old
    // `remaining <= 0` check called it dead at month 0.
    if (outOfCashMonth === null && (remaining < 0 || (remaining <= 0 && rev < exp))) {
      outOfCashMonth = m;
    }

    remaining += rev - exp;
  }

  // Alive means you cross into profit while there is still money in the bank.
  const alive =
    profitableMonth !== null &&
    (outOfCashMonth === null || profitableMonth < outOfCashMonth);

  return { alive, profitableMonth, outOfCashMonth, lowestCash, series };
}
