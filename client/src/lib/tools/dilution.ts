/**
 * HAG-163, tool 2 of 3: dilution.
 *
 * Formula source, transcribed rather than invented — the Quant lane's file:
 *   hive/reports/quant-forge-tools-maths.md, "Tool 2 — Dilution".
 * Its arithmetic is reproduced by the Quant lane's reference script, vendored at
 *   server/tests/quant_forge_tools_check.py (section "2. DILUTION").
 *
 * The card's rule is "do not invent the formulas". So every input to this file that
 * is NOT forced by arithmetic is labelled here, at the point it is applied, exactly
 * as the maths file labels it:
 *
 *   TEXTBOOK  investor_share = raise / (pre_money + raise). Not a choice.
 *   CHOICE    the pool top-up is created PRE-money, so it dilutes existing holders
 *             only and never the new investor (the "option pool shuffle").
 *   CHOICE    pool_target_pct is a percentage of POST-money, and the top-up never
 *             shrinks: `dP >= 0`, because a tool must not quietly cancel options a
 *             company already granted.
 *
 * The model, in the maths file's symbols — F founder shares, E existing pool shares,
 * T = F + E, V_pre pre-money, R raised, p the pool target as a fraction of post-money:
 *
 *   k    = 1 + R / V_pre
 *   dP   = max(0, (p * T * k - E) / (1 - p * k))   new pool shares, issued BEFORE the money
 *   N    = R * (T + dP) / V_pre                    shares the investor buys
 *   post = T + dP + N
 *
 * The headline the page exists to print: `investor_share` is exactly `R / (V_pre + R)`
 * whatever `p` is, while the founders are diluted by more than that — the pool comes
 * out of their side. In the maths file's worked example the founders lose 32 points,
 * not the 20 a simple calculator shows.
 *
 * Every degenerate input resolves to a plain-English reason. This file never returns
 * Infinity, never returns NaN, and never returns a negative share count.
 */

/** The maths file's exact field names and units. */
export interface DilutionInputs {
  /** currency (USD) — the agreed pre-money valuation */
  pre_money_valuation: number;
  /** currency (USD) — new money into the company */
  raise_amount: number;
  /** count, shares — founder/employee shares before the round */
  founder_shares: number;
  /** count, shares — unissued options before the round */
  existing_pool_shares: number;
  /** percent of post-money, 0 <= x < 100 — the pool the round must leave behind */
  pool_target_pct: number;
}

/**
 * `unreachable` is its own outcome rather than `invalid`: the inputs are well formed,
 * there is simply no share count that satisfies them. The maths file is explicit that
 * this must read "pool target unreachable at this raise size" and must NOT emit the
 * negative `dP` the raw formula produces.
 */
export type DilutionOutcome = "ok" | "unreachable" | "invalid";

export interface DilutionShares {
  /** T — shares outstanding before the round */
  preMoneyTotal: number;
  /** dP — new shares issued into the pool before the investment */
  newPoolShares: number;
  /** N — shares the investor buys */
  investorShares: number;
  /** T + dP + N */
  postMoneyTotal: number;
  /** V_pre / T — the price per share this round implies */
  pricePerShare: number;
  /** true when the pool was already at or above target and `dP` was clamped to 0 */
  poolClamped: boolean;
}

export interface DilutionResult {
  outcome: DilutionOutcome;
  /** one plain-English line when there is no share model to print; null otherwise */
  reason: string | null;
  /** null when there is no share model: invalid, unreachable, or a zero pre-money */
  shares: DilutionShares | null;
  /** fraction of post-money; all null exactly when `shares` is null */
  founderPct: number | null;
  poolPct: number | null;
  investorPct: number | null;
  /**
   * The number every simple dilution calculator prints: `R / (V_pre + R)`. Computed even
   * when there is no share model, because it is the figure the page compares against —
   * the gap between it and `founderPct` is the point of the tool.
   */
  simpleInvestorPct: number;
  /** non-fatal warnings: a zero pre-money, a clamped pool, no founder shares entered */
  notes: string[];
}

const INVALID = (reason: string): DilutionResult => ({
  outcome: "invalid",
  reason,
  shares: null,
  founderPct: null,
  poolPct: null,
  investorPct: null,
  simpleInvestorPct: 0,
  notes: [],
});

/** An empty result that still carries the naive figure, for the unreachable case. */
function unreachable(reason: string, simpleInvestorPct: number, notes: string[]): DilutionResult {
  return {
    outcome: "unreachable",
    reason,
    shares: null,
    founderPct: null,
    poolPct: null,
    investorPct: null,
    simpleInvestorPct,
    notes,
  };
}

/**
 * The maths file's edge-case table, resolved in its own order.
 *
 * One apparent conflict in that table is worth naming, because it is the kind of thing a
 * later reader would "fix" wrongly. Row 2 says a zero pre-money takes 100% and should be
 * shown with a warning; row 1 says to require `pre_money_valuation > 0`. Both hold under
 * one rule: reject when `V_pre + R <= 0` — that is row 1's real condition, the
 * denominator of `R / (V_pre + R)` — and when `V_pre` is exactly 0 with money coming in,
 * print the 100% the arithmetic gives and warn loudly. A negative pre-money is rejected
 * outright, per row 3.
 */
export function computeDilution(input: DilutionInputs): DilutionResult {
  const { pre_money_valuation: V, raise_amount: R } = input;
  const raw = [V, R, input.founder_shares, input.existing_pool_shares, input.pool_target_pct];

  if (raw.some((v) => !Number.isFinite(v))) {
    return INVALID("Every field needs a number in it.");
  }
  if (V < 0) {
    return INVALID("A negative pre-money valuation is not a valuation.");
  }
  if (R < 0) {
    return INVALID("The raise cannot be negative.");
  }
  if (input.founder_shares < 0 || input.existing_pool_shares < 0) {
    return INVALID("Share counts cannot be negative.");
  }
  if (input.pool_target_pct < 0 || input.pool_target_pct >= 100) {
    return INVALID("The pool target must be at least 0% and under 100% of post-money.");
  }
  if (V + R <= 0) {
    // Covers V = 0 with R = 0: with no valuation and no money there is no round to model.
    return INVALID("Enter a pre-money valuation above zero, or an amount being raised.");
  }

  const simpleInvestorPct = R / (V + R);

  // A zero pre-money is the one degenerate case the maths file asks to be SHOWN rather
  // than refused: the investor's money buys the whole company. There is no price per
  // share and no meaningful share count, so no share model is printed.
  if (V === 0) {
    return {
      outcome: "ok",
      reason: null,
      shares: null,
      founderPct: 0,
      poolPct: 0,
      investorPct: 1,
      simpleInvestorPct,
      notes: [
        "A pre-money valuation of zero means the investor's money buys 100% of the company. Check that the valuation is really zero and not a blank field.",
      ],
    };
  }

  const F = input.founder_shares;
  const E = input.existing_pool_shares;
  const T = F + E;

  if (T <= 0) {
    return INVALID("Enter the shares outstanding — with no shares there is no price per share.");
  }

  const p = input.pool_target_pct / 100;
  const notes: string[] = [];

  // The maths file: "Only the ratio F : E matters for percentages, so a founder who does
  // not know share counts can enter any two numbers with the right ratio."
  if (F === 0) {
    notes.push(
      "No founder shares entered, so every existing share is in the option pool. The percentages are still correct, but check the entry.",
    );
  }

  const k = 1 + R / V;

  // p * k >= 1 means the denominator is zero or negative: no share count satisfies the
  // target. Refuse, rather than emitting the negative dP the raw formula produces. A
  // real case — asking for a 90% pool on a round that only adds 25% to the share count.
  if (p * k >= 1) {
    notes.push(
      `A round this size adds ${((k - 1) * 100).toFixed(1)}% to the share count, which cannot leave room for a ${input.pool_target_pct}% post-money pool.`,
    );
    return unreachable(
      "Pool target unreachable at this raise size. Lower the pool target or raise more.",
      simpleInvestorPct,
      notes,
    );
  }

  const rawDp = (p * T * k - E) / (1 - p * k);
  // CHOICE 2, second half: the top-up is clamped at zero and never shrinks, so a pool
  // already at or above target is reported, not undone.
  const poolClamped = rawDp < 0;
  const dP = poolClamped ? 0 : rawDp;
  if (poolClamped) {
    notes.push(
      `The option pool is already at or above the ${input.pool_target_pct}% target, so this round creates no new pool shares.`,
    );
  }

  const N = (R * (T + dP)) / V;
  const post = T + dP + N;

  return {
    outcome: "ok",
    reason: null,
    shares: {
      preMoneyTotal: T,
      newPoolShares: dP,
      investorShares: N,
      postMoneyTotal: post,
      pricePerShare: V / T,
      poolClamped,
    },
    founderPct: F / post,
    poolPct: (E + dP) / post,
    investorPct: N / post,
    simpleInvestorPct,
    notes,
  };
}

/**
 * The maths file's worked example, used by the page as its pre-filled default and by the
 * test. Founders lose 32 points here: 20 to the investor, 12 to the pool.
 */
export const WORKED_EXAMPLE: DilutionInputs = {
  pre_money_valuation: 8_000_000,
  raise_amount: 2_000_000,
  founder_shares: 8_000_000,
  existing_pool_shares: 1_000_000,
  pool_target_pct: 12,
};

/**
 * Seed + Series A + Series B at the 2025 medians in `quant-benchmarks.md` Table 6 leaves
 * pre-seed holders 56.5% — the maths file's cumulative-keep figures, `0.81 * 0.82 * 0.85`.
 * Kept as data rather than as a calculator: this tool models ONE round, and a second
 * multi-round model would be a second formula to keep honest.
 */
export const CUMULATIVE_KEEP_2025 = 0.81 * 0.82 * 0.85;
