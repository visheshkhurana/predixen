/**
 * Body for POST /api/simulation/v2/run.
 *
 * Only non-null founder metrics are included. Nulls are omitted so the engine
 * applies its own defaults and labels them assumed. Hardcoded client fallbacks
 * (customers: 50, churn_rate: 0.03, mrr ?? 50000, burn ?? 80000, cash ?? 500000,
 * growth ?? 5, headcount || 10) are not sent.
 */

export interface SimulationBaseMetrics {
  mrr?: number | null;
  /** NET burn (total costs incl. COGS minus revenue), as on the dashboard. */
  burnRate?: number | null;
  /** Total monthly costs incl. COGS (gross spend). */
  totalMonthlyExpenses?: number | null;
  cashOnHand?: number | null;
  monthlyGrowthRate?: number | null;
  headcount?: number | null;
}

export interface SimulationControls {
  totalRounds: number;
  fundingClimate: number;
  marketGrowth: number;
  marketVolatility: number;
}

function isFiniteNumber(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

/**
 * Same conversion the Flight Simulator used when a growth figure was present:
 * values above 1 are percentages (10.8 → 0.108); values at or below 1 are
 * already a monthly rate. Clamped to the request schema.
 */
export function growthRateForRequest(monthlyGrowthRate: number): number {
  const raw = monthlyGrowthRate > 1 ? monthlyGrowthRate / 100 : monthlyGrowthRate;
  return Math.min(1.0, Math.max(-0.5, raw));
}

/**
 * monthly_burn on /api/simulation/v2/run is GROSS monthly spend: the engine
 * does `cash += mrr - burn_rate` (server/services/simulation/engine.py), so
 * sending the dashboard's net burn counted revenue twice (AlphaKids demo:
 * MRR 43,949 + net burn 24,109 showed cash GROWING instead of ~21 months).
 *
 * Gross = net burn + MRR whenever the company burns cash, which reproduces
 * the dashboard's net burn exactly. Net burn is clamped at 0 for a profitable
 * company, so there the reported total expenses are used instead. Without
 * MRR there is no way to derive gross from net, so nothing is sent and the
 * engine labels its default as assumed.
 */
export function grossMonthlySpendForRequest(
  baseMetrics: SimulationBaseMetrics | null | undefined,
): number | null {
  const net = baseMetrics?.burnRate;
  const mrr = baseMetrics?.mrr;
  const total = baseMetrics?.totalMonthlyExpenses;
  if (isFiniteNumber(net) && net > 0 && isFiniteNumber(mrr)) return net + Math.max(0, mrr);
  if (isFiniteNumber(total) && total > 0) return total;
  if (isFiniteNumber(net) && isFiniteNumber(mrr)) return net + Math.max(0, mrr);
  return null;
}

export function buildSimulationV2Payload(
  baseMetrics: SimulationBaseMetrics | null | undefined,
  controls: SimulationControls,
): Record<string, number> {
  const body: Record<string, number> = {
    total_rounds: controls.totalRounds,
    funding_climate: controls.fundingClimate,
    market_growth: controls.marketGrowth,
    market_volatility: controls.marketVolatility,
  };

  if (isFiniteNumber(baseMetrics?.mrr)) body.monthly_revenue = baseMetrics.mrr;
  const gross = grossMonthlySpendForRequest(baseMetrics);
  if (gross !== null) body.monthly_burn = gross;
  if (isFiniteNumber(baseMetrics?.cashOnHand)) body.cash_balance = baseMetrics.cashOnHand;
  if (isFiniteNumber(baseMetrics?.monthlyGrowthRate)) {
    body.growth_rate = growthRateForRequest(baseMetrics.monthlyGrowthRate);
  }
  // team_size must be >= 1. A missing or zero headcount is the engine's
  // assumed default (10), not a founder entry of 0.
  if (isFiniteNumber(baseMetrics?.headcount) && baseMetrics.headcount >= 1) {
    body.team_size = baseMetrics.headcount;
  }

  return body;
}
