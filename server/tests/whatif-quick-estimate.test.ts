import test from 'node:test';
import assert from 'node:assert/strict';
import { calculateWhatIfImpact, isSustainable, type FinancialState } from '../../client/src/lib/simulation/sensitivityAnalysis';

const burning: FinancialState = {
  monthlyRevenue: 1_000_000, grossMargin: 50, opex: 800_000, payroll: 700_000, otherCosts: 0,
  cashBalance: 10_000_000, churnRate: 0, growthRate: 0, cac: 0, ltv: 0,
};

test('no adjustments means no change', () => {
  const r = calculateWhatIfImpact(burning, {});
  assert.equal(r.runwayChange, 0);
  assert.equal(r.cashChange, 0);
  assert.equal(r.burnChange, 0);
  assert.ok(Math.abs(r.runway - 10) < 0.01, 'flat ₹10L burn on ₹1Cr lasts 10 months');
});

test('the growth slider actually moves runway (it used to be ignored)', () => {
  const faster = calculateWhatIfImpact(burning, { revenueGrowth: 5 });
  assert.ok(faster.runwayChange > 0.5, `growth should extend runway, got ${faster.runwayChange}`);
  const churn = calculateWhatIfImpact(burning, { churnRate: 5 });
  assert.ok(churn.runwayChange < 0, 'churn shortens runway');
});

test('cutting burn lowers monthly burn and extends runway', () => {
  const r = calculateWhatIfImpact(burning, { burnChange: -20 });
  assert.ok(r.burnChange < 0);
  assert.ok(r.runwayChange > 0);
});

test('becoming profitable reads as sustainable without a fake month delta', () => {
  const r = calculateWhatIfImpact(burning, { grossMargin: 200 });
  assert.ok(isSustainable(r.runway));
  assert.equal(r.runwayChange, 0, 'no "gain 890 months"');
});
