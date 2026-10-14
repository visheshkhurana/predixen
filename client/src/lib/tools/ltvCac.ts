/**
 * HAG-163, tool 3 of 3: LTV:CAC.
 *
 * Formula source, transcribed rather than invented — the Quant lane's file:
 *   hive/reports/quant-forge-tools-maths.md, "Tool 3 — LTV:CAC".
 * Its arithmetic is reproduced by the Quant lane's reference script, vendored at
 *   server/tests/quant_forge_tools_check.py (sections "3. LTV:CAC" and "5. ANNUAL vs
 *   MONTHLY CHURN TRAP").
 *
 * Thresholds are NOT invented here either: they are read from
 *   hive/reports/quant-benchmarks.md, Table 5, and named and dated at the point of use,
 * because that file says in as many words that a tool which grades a founder must say
 * which benchmark it grades against and when that benchmark was written.
 *
 * The card's rule is "do not invent the formulas". Every input to this file that is NOT
 * forced by arithmetic is labelled here, at the point it is applied, exactly as the maths
 * file labels it:
 *
 *   CHOICE    ltv is GROSS-PROFIT based and uses monthly churn as a simple decay rate:
 *             `ltv = arpa_monthly * gm% / churn%`. The alternative — a discounted-cash-flow
 *             LTV, which David Skok himself moved to — needs a discount rate and a
 *             revenue-growth assumption a free tool cannot fairly ask a seed founder for.
 *             The two give DIFFERENT answers, so the form used is stated on the page.
 *   CHOICE    cac is FULLY LOADED sales & marketing over new customers in the same period:
 *             `cac = sm_spend / new_customers`. Ad-spend-only would let a company grade
 *             itself while ignoring the salaries that generated the pipeline.
 *   CHOICE    churn must be greater than zero and is floored at 0.1% per month. `churn = 0`
 *             makes LTV infinite, and an infinite LTV:CAC prints the best possible score
 *             for a business that has simply not been running long enough to lose anyone.
 *   TEXTBOOK  ratio = ltv / cac, and payback_months = cac / (arpa_monthly * gm%).
 *
 * The trap the page must print, from section 5 of the reference script: monthly churn is
 * NOT 12 x monthly. Entering 2%/month into an annual formula as "24%" understates LTV by
 * 11.5%, so this module takes churn in one unit only and reports the compounded annual
 * equivalent of whatever it was given.
 *
 * Every degenerate input resolves to a plain-English reason. This file never returns
 * Infinity, never returns NaN, and never returns a negative figure.
 */

/** The maths file's exact field names and units. */
export interface LtvCacInputs {
  /** currency (USD) per customer per month — average revenue per account */
  arpa_monthly: number;
  /** percent of revenue — revenue less the cost of serving */
  gross_margin_pct: number;
  /** percent PER MONTH — the share of customers lost each month, in one unit only */
  monthly_churn_pct: number;
  /** currency (USD) in the period — FULLY LOADED sales & marketing */
  sm_spend: number;
  /** count in the period — customers won in the SAME period */
  new_customers: number;
}

/**
 * `no_cac` is its own outcome rather than `invalid`: the inputs are well formed but there
 * is no measurable acquisition cost — no customers won, or no spend to divide by them.
 * The maths file is explicit that this is the most common real case in a quiet month and
 * must read "n/a", never "CAC = 0" and never an infinitely good score.
 */
export type LtvCacOutcome = "ok" | "no_cac" | "invalid";

/**
 * The maths file: "The tool should grade the two numbers separately — a good ratio with a
 * bad payback is the classic cash-flow trap." `cashFlowTrap` is that condition, computed
 * rather than left to the reader.
 */
export interface LtvCacGrade {
  /** named and dated at the point of use, as quant-benchmarks.md requires */
  benchmark: string;
  /** one line for the ratio; null exactly when there is no ratio to grade */
  ratioVerdict: string | null;
  /** one line for payback; null exactly when there is no payback to grade */
  paybackVerdict: string | null;
  /** true when the ratio clears the benchmark but the payback does not */
  cashFlowTrap: boolean;
}

export interface LtvCacResult {
  outcome: LtvCacOutcome;
  /** one plain-English line when the inputs are unusable; null otherwise */
  reason: string | null;
  /** gross-profit LTV; null only when the inputs are invalid */
  ltv: number | null;
  /** null when there is no measurable acquisition cost — see `cacUnavailableReason` */
  cac: number | null;
  /** ltv / cac; null whenever cac is null */
  ratio: number | null;
  /**
   * Months to recover CAC. Null when CAC is null, and also when ARPA x gross margin is
   * zero: a business with no gross profit per customer can never pay marketing back, and
   * that is a different statement from "n/a".
   */
  paybackMonths: number | null;
  /** the maths file's own wording for why CAC is n/a; null when there is a CAC */
  cacUnavailableReason: string | null;
  /** the churn actually used, after the floor */
  monthlyChurnUsedPct: number;
  /** true when the entered churn was below the floor and was raised to it */
  churnFloored: boolean;
  /** compounded annual equivalent of the churn actually used — the printed trap */
  annualChurnUsedPct: number;
  grade: LtvCacGrade | null;
  /** non-fatal warnings: the churn floor, no payback at this margin */
  notes: string[];
}

/** The maths file's suggested floor, in percent per month. */
export const CHURN_FLOOR_PCT = 0.1;

/**
 * David Skok, *SaaS Metrics 2.0* — the LTV:CAC benchmark of "above 3x", and the payback
 * lines "5-7 months" for the best and "anemic" beyond 12. `quant-benchmarks.md` Table 5
 * records that the page carries **no clear date**, only an update note of 05/2016, and
 * that Benchmarkit's 2025 median payback of "~12 months" is a decade apart from Skok's
 * view of normal. This tool grades against Skok's pair and says so, rather than blending
 * two benchmarks written ten years apart.
 */
export const SKOK_BENCHMARK =
  "David Skok, SaaS Metrics 2.0 (no clear date on the page; update note 05/2016)";
export const SKOK_RATIO_GOOD = 3;
export const SKOK_PAYBACK_BEST_MONTHS = 7;
export const SKOK_PAYBACK_WEAK_MONTHS = 12;

/** Compounded annual churn from a monthly rate. 2%/month gives 21.5283%, not 24%. */
export function annualChurnPct(monthlyPct: number): number {
  return (1 - Math.pow(1 - monthlyPct / 100, 12)) * 100;
}

const INVALID = (reason: string): LtvCacResult => ({
  outcome: "invalid",
  reason,
  ltv: null,
  cac: null,
  ratio: null,
  paybackMonths: null,
  cacUnavailableReason: null,
  monthlyChurnUsedPct: 0,
  churnFloored: false,
  annualChurnUsedPct: 0,
  grade: null,
  notes: [],
});

/**
 * The maths file's edge-case table, resolved in its own order.
 *
 * Two rows are the ones a naive implementation gets wrong. `new_customers = 0` must read
 * "n/a — no new customers", not "CAC = 0" (which would print an infinitely good score for
 * a month in which nobody was won). `sm_spend = 0` with customers won must read
 * "n/a — no measurable acquisition cost", not infinity. Both are `no_cac`: LTV is real and
 * is still shown, and only the CAC side of the page goes blank.
 */
export function computeLtvCac(input: LtvCacInputs): LtvCacResult {
  const raw = [
    input.arpa_monthly,
    input.gross_margin_pct,
    input.monthly_churn_pct,
    input.sm_spend,
    input.new_customers,
  ];
  if (raw.some((v) => !Number.isFinite(v))) {
    return INVALID("Every field needs a number in it.");
  }
  if (
    input.arpa_monthly < 0 ||
    input.sm_spend < 0 ||
    input.new_customers < 0
  ) {
    return INVALID("Revenue per account, marketing spend and customer count cannot be negative.");
  }
  if (input.gross_margin_pct < 0 || input.gross_margin_pct > 100) {
    return INVALID("Gross margin must be between 0% and 100%.");
  }
  if (input.monthly_churn_pct < 0) {
    return INVALID("Churn cannot be negative. Enter the share of customers lost each month.");
  }
  if (input.monthly_churn_pct >= 100) {
    return INVALID("A monthly churn of 100% or more leaves no customers to measure.");
  }

  const notes: string[] = [];

  // CHOICE 3. A churn of zero would make LTV infinite and print the best possible score for
  // a business that has not been running long enough to lose anyone. Floor it and say so,
  // rather than refusing the calculation or printing a wall of zeroes.
  const churnFloored = input.monthly_churn_pct < CHURN_FLOOR_PCT;
  const churnPct = churnFloored ? CHURN_FLOOR_PCT : input.monthly_churn_pct;
  if (churnFloored) {
    notes.push(
      `Churn was floored at ${CHURN_FLOOR_PCT}% per month. A churn of zero would make LTV infinite, which is not a score any company has earned.`,
    );
  }

  // CHOICE 1: gross-profit LTV with monthly churn as a simple decay rate.
  const grossProfitPerCustomer = input.arpa_monthly * (input.gross_margin_pct / 100);
  const ltv = grossProfitPerCustomer / (churnPct / 100);
  const annualChurnUsedPct = annualChurnPct(churnPct);

  // CHOICE 2: fully loaded S&M over customers won in the same period.
  let cac: number | null = null;
  let cacUnavailableReason: string | null = null;
  if (input.new_customers <= 0) {
    cacUnavailableReason = "n/a — no new customers";
  } else if (input.sm_spend <= 0) {
    cacUnavailableReason = "n/a — no measurable acquisition cost";
  } else {
    cac = input.sm_spend / input.new_customers;
  }

  if (cacUnavailableReason) {
    return {
      outcome: "no_cac",
      reason: null,
      ltv,
      cac: null,
      ratio: null,
      paybackMonths: null,
      cacUnavailableReason,
      monthlyChurnUsedPct: churnPct,
      churnFloored,
      annualChurnUsedPct,
      grade: null,
      notes,
    };
  }

  const ratio = ltv / cac!;

  // A business with no gross profit per customer can never recover marketing spend. That is
  // a real answer, and a different one from "CAC is unknown", so it gets its own wording
  // rather than a null hidden behind the same label.
  let paybackMonths: number | null = null;
  if (grossProfitPerCustomer > 0) {
    paybackMonths = cac! / grossProfitPerCustomer;
  } else {
    notes.push(
      "There is no gross profit per customer at this margin, so no marketing spend can ever pay back.",
    );
  }

  const ratioVerdict =
    ratio >= SKOK_RATIO_GOOD
      ? `Clears the ${SKOK_RATIO_GOOD}x benchmark.`
      : `Below the ${SKOK_RATIO_GOOD}x benchmark.`;

  let paybackVerdict: string | null = null;
  if (paybackMonths === null) {
    paybackVerdict = "No payback at this margin.";
  } else if (paybackMonths <= SKOK_PAYBACK_BEST_MONTHS) {
    paybackVerdict = `Inside the 5–${SKOK_PAYBACK_BEST_MONTHS} month range the best businesses hold.`;
  } else if (paybackMonths <= SKOK_PAYBACK_WEAK_MONTHS) {
    paybackVerdict = `Past the best range, but still inside the ${SKOK_PAYBACK_WEAK_MONTHS}-month line.`;
  } else {
    paybackVerdict = `Beyond ${SKOK_PAYBACK_WEAK_MONTHS} months, which the same source calls anemic.`;
  }

  return {
    outcome: "ok",
    reason: null,
    ltv,
    cac,
    ratio,
    paybackMonths,
    cacUnavailableReason: null,
    monthlyChurnUsedPct: churnPct,
    churnFloored,
    annualChurnUsedPct,
    grade: {
      benchmark: SKOK_BENCHMARK,
      ratioVerdict,
      paybackVerdict,
      // The point of grading them separately: 4.0x clears the ratio benchmark and a 12.5
      // month payback does not clear the payback one. The maths file's own worked example
      // is exactly this case.
      cashFlowTrap:
        ratio >= SKOK_RATIO_GOOD &&
        paybackMonths !== null &&
        paybackMonths > SKOK_PAYBACK_WEAK_MONTHS,
    },
    notes,
  };
}

/**
 * The maths file's worked example: ARPA $500, 80% gross margin, 2%/month churn, $120,000
 * of S&M, 24 customers won. LTV $20,000, CAC $5,000, ratio 4.00, payback 12.5 months — a
 * ratio that clears the benchmark with a payback that does not, which is the whole reason
 * the page grades the two numbers separately.
 */
export const WORKED_EXAMPLE: LtvCacInputs = {
  arpa_monthly: 500,
  gross_margin_pct: 80,
  monthly_churn_pct: 2,
  sm_spend: 120_000,
  new_customers: 24,
};

/**
 * The same LTV identity written in annual terms — `arpa_annual * gm% / annual_churn%` — as
 * section 3 of the reference script prints it alongside the monthly form. This is NOT a
 * second model: it is `arpa_monthly * gm% / churn%` with both rates multiplied by twelve,
 * and it exists here for one reason only, to make the churn trap measurable rather than
 * asserted in prose.
 */
export function ltvFromAnnualChurn(
  arpaAnnual: number,
  grossMarginPct: number,
  annualChurnPct: number,
): number {
  return (arpaAnnual * (grossMarginPct / 100)) / (annualChurnPct / 100);
}

/**
 * The trap the page must print, from section 5 of the reference script, held as inputs plus
 * the three figures derived from them so nothing on the page is a copied number.
 *
 * A founder who moves their churn into a spreadsheet as "24% a year" and one who compounds
 * it properly get the same LTV this module's monthly form gives and a higher one
 * respectively — so the naive route understates by 11.5%, silently, and the monthly form's
 * own answer is the *lower* of the two. That coincidence is exactly why the mistake is
 * invisible, which is why the page prints all three numbers side by side.
 */
export const CHURN_TRAP = {
  arpa_monthly: 500,
  gross_margin_pct: 80,
  monthly_churn_pct: 2,
  /** what multiplying the monthly rate by twelve would give, wrongly */
  naiveAnnualChurnPct: 24,
} as const;

const TRAP_ARPA_ANNUAL = CHURN_TRAP.arpa_monthly * 12;
const TRAP_ANNUAL_CHURN_COMPOUNDED = annualChurnPct(CHURN_TRAP.monthly_churn_pct);

/** The number the correct monthly form gives — and the number the naive 24% also gives. */
export const CHURN_TRAP_LTV_MONTHLY_FORM = ltvFromAnnualChurn(
  TRAP_ARPA_ANNUAL,
  CHURN_TRAP.gross_margin_pct,
  CHURN_TRAP.naiveAnnualChurnPct,
);

/** What the same ARPA and margin give once churn is compounded the way it actually works. */
export const CHURN_TRAP_LTV_COMPOUNDED = ltvFromAnnualChurn(
  TRAP_ARPA_ANNUAL,
  CHURN_TRAP.gross_margin_pct,
  TRAP_ANNUAL_CHURN_COMPOUNDED,
);

/** How much the naive route understates LTV, in percent. 11.5% on a 2%/month churn. */
export const CHURN_TRAP_UNDERSTATEMENT_PCT =
  (CHURN_TRAP_LTV_COMPOUNDED / CHURN_TRAP_LTV_MONTHLY_FORM - 1) * 100;
