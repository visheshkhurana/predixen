/**
 * Display rules for /overview: how net burn and runway are put into words,
 * and when unit economics are real enough to show as numbers.
 *
 * Net burn here is signed: total expenses minus revenue. A negative number is
 * a monthly surplus (revenue covers costs), and it must never be shown as a
 * "negative burn" or badged as an AI estimate — it is arithmetic on figures
 * the founder entered, uploaded or connected.
 */

export type MetricSourceKind = 'reported' | 'computed' | 'estimated';

/**
 * Source badge for net burn. It is computed whenever there is revenue or
 * expense data to compute it from, whatever its sign. Only with neither is
 * there nothing behind it.
 */
export function netBurnSource(input: {
  netBurn: number;
  mrr: number;
  totalExpenses: number;
}): MetricSourceKind {
  const { netBurn, mrr, totalExpenses } = input;
  if (!Number.isFinite(netBurn)) return 'estimated';
  if (mrr > 0 || totalExpenses > 0) return 'computed';
  return 'estimated';
}

export type BurnCardDisplay = {
  title: string;
  /** Always a non-negative amount; the title carries the direction. */
  amount: number;
  subtitle: string;
  isSurplus: boolean;
  variant?: 'success';
};

/** Burn card: a surplus is shown as "Monthly Surplus", never as a negative burn. */
export function burnCardDisplay(netBurn: number): BurnCardDisplay {
  if (Number.isFinite(netBurn) && netBurn < 0) {
    return {
      title: 'Monthly Surplus',
      amount: Math.abs(netBurn),
      subtitle: '/month · revenue covers costs',
      isSurplus: true,
      variant: 'success',
    };
  }
  return {
    title: 'Burn Rate',
    amount: Number.isFinite(netBurn) ? netBurn : 0,
    subtitle: '/month',
    isSurplus: false,
  };
}

/** Briefing sentence about burn. `fmt` formats a currency amount. */
export function briefingBurnSentence(
  netBurn: number,
  mrr: number,
  fmt: (n: number) => string,
): string {
  if (!Number.isFinite(netBurn)) {
    return 'Burn cannot be worked out yet — add your revenue and expenses.';
  }
  if (netBurn > 0) {
    return netBurn < mrr
      ? `Burn is below revenue — you are burning efficiently at ${fmt(netBurn)}/mo.`
      : `Burn is above revenue — monitor spending closely at ${fmt(netBurn)}/mo.`;
  }
  if (mrr > 0) {
    return netBurn < 0
      ? `You are not burning cash — revenue exceeds costs by ${fmt(Math.abs(netBurn))}/mo.`
      : 'You are not burning cash — revenue covers costs exactly.';
  }
  return 'Burn cannot be worked out yet — add your revenue and expenses.';
}

/**
 * Briefing sentence about runway.
 *
 * @param runwayMonths months of runway; Infinity when not burning, NaN when
 *   cash was never provided.
 * @param fmt formats a month count, e.g. "14.2 months".
 */
export function briefingRunwaySentence(
  runwayMonths: number,
  fmt: (months: number) => string,
): string {
  if (runwayMonths === Infinity) {
    return 'Runway is not a constraint while revenue covers costs.';
  }
  if (!Number.isFinite(runwayMonths)) {
    return 'Runway is unknown — add your cash balance to see it.';
  }
  const m = fmt(runwayMonths);
  if (runwayMonths >= 18) return `Runway is comfortably above 18 months at ${m}.`;
  if (runwayMonths >= 12) return `Runway is worth watching at ${m} — 12–18 months is when to plan the next raise.`;
  if (runwayMonths >= 6) return `Runway is getting tight at ${m} — consider extending.`;
  return `Runway is critically low at ${m} — immediate action needed.`;
}

export type UnitEconomicsAvailability = {
  cacKnown: boolean;
  ltvKnown: boolean;
  ratioKnown: boolean;
};

/**
 * Whether CAC, LTV and LTV:CAC rest on real inputs. A value the truth scan
 * filled from defaults (no marketing spend, no customer data) is flagged
 * 'estimated' and is not shown as a number — the card says what is needed.
 */
export function unitEconomicsAvailability(input: {
  cac: number;
  ltv: number;
  ltvCacRatio: number;
  sources: Record<string, MetricSourceKind | undefined>;
}): UnitEconomicsAvailability {
  const { cac, ltv, ltvCacRatio, sources } = input;
  const cacKnown = cac > 0 && sources['cac'] !== 'estimated';
  const ltvKnown = ltv > 0 && sources['ltv'] !== 'estimated';
  const ratioKnown =
    cacKnown && ltvKnown && ltvCacRatio > 0 && sources['ltvCacRatio'] !== 'estimated';
  return { cacKnown, ltvKnown, ratioKnown };
}
