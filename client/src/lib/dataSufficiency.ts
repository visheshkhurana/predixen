/**
 * When is there enough data to say something about a company?
 *
 * A brand-new company has no revenue, no expenses and no cash on file. Every
 * derived number is then 0, and arithmetic on zeros reads as good news:
 * 0 burn becomes "Sustainable" runway, no flags becomes "Financial Health is
 * Looking Good", a 0 score is painted red as if it were a verdict. These
 * helpers decide when the honest answer is "not enough data yet".
 */

/** Below this Data Confidence Score a health verdict is not shown. */
export const MIN_CONFIDENCE_TO_JUDGE = 20;

export type FinancialFigures = {
  mrr?: number | null;
  cashOnHand?: number | null;
  totalMonthlyExpenses?: number | null;
  netBurn?: number | null;
};

const pos = (v: number | null | undefined): boolean =>
  typeof v === 'number' && Number.isFinite(v) && v > 0;

/** True when at least one real financial figure (revenue, cash, spend) is on file. */
export function hasFinancialData(m: FinancialFigures | null | undefined): boolean {
  if (!m) return false;
  return (
    pos(m.mrr) ||
    pos(m.cashOnHand) ||
    pos(m.totalMonthlyExpenses) ||
    (typeof m.netBurn === 'number' && Number.isFinite(m.netBurn) && m.netBurn !== 0)
  );
}

/**
 * A positive or negative health verdict needs real figures AND a data
 * confidence score at or above MIN_CONFIDENCE_TO_JUDGE. A missing score
 * (no scan yet) is not enough to judge.
 */
export function canJudgeHealth(input: {
  hasData: boolean;
  confidence: number | null | undefined;
}): boolean {
  const { hasData, confidence } = input;
  if (!hasData) return false;
  if (typeof confidence !== 'number' || !Number.isFinite(confidence)) return false;
  return confidence >= MIN_CONFIDENCE_TO_JUDGE;
}

/** What to add so the health check can say something. Plain-language list. */
export function missingDataHints(m: FinancialFigures | null | undefined): string[] {
  const hints: string[] = [];
  if (!pos(m?.mrr)) hints.push('monthly revenue');
  if (!pos(m?.totalMonthlyExpenses)) hints.push('monthly expenses');
  if (!pos(m?.cashOnHand)) hints.push('cash in the bank');
  return hints;
}

/** "a, b and c" */
export function joinWithAnd(items: string[]): string {
  if (items.length <= 1) return items[0] ?? '';
  return `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`;
}

export const NOT_SCORED_LABEL = 'Not scored yet';

export type ScoreDisplay =
  | { scored: true; value: number }
  | { scored: false; label: typeof NOT_SCORED_LABEL };

/**
 * A score of 0 (or no score) when there is no data behind it is not a
 * verdict. Render it as a neutral "Not scored yet", never as a red 0.
 * A real low score with data behind it is still shown as a number.
 */
export function scoreDisplay(
  score: number | null | undefined,
  opts: { hasData: boolean },
): ScoreDisplay {
  if (typeof score !== 'number' || !Number.isFinite(score)) {
    return { scored: false, label: NOT_SCORED_LABEL };
  }
  // Without data any score is a default, not a judgement (an empty company
  // used to show "Quality of Growth 45/100").
  if (!opts.hasData) {
    return { scored: false, label: NOT_SCORED_LABEL };
  }
  return { scored: true, value: Math.round(score) };
}

/**
 * "Sustainable" runway means revenue covers costs. Zero burn from zero
 * revenue and zero expenses (nothing entered) is not sustainable, it is
 * unknown. Returns:
 *  - 'sustainable' when the server/derived figures say runway is unlimited
 *    and there is real revenue behind it;
 *  - 'unknown' when runway is unlimited only because nothing is on file;
 *  - 'finite' otherwise (the caller shows months).
 */
export function runwayKind(input: {
  sustainableFlag?: boolean | null;
  runway?: number | null;
  revenue?: number | null;
  expenses?: number | null;
  cash?: number | null;
}): 'sustainable' | 'unknown' | 'finite' {
  const { sustainableFlag, runway, revenue, expenses, cash } = input;
  const unlimited =
    sustainableFlag === true ||
    runway === Infinity ||
    (typeof runway === 'number' && runway >= 900);
  const noFigures = !pos(revenue) && !pos(expenses) && !pos(cash);
  if (noFigures) {
    // Nothing on file: 0 months, ∞, or 999 are all artefacts of zeros.
    if (unlimited || !pos(runway)) return 'unknown';
  }
  if (unlimited) return pos(revenue) ? 'sustainable' : 'unknown';
  return 'finite';
}
