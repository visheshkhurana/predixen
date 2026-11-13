// Run: npx tsx --test client/src/lib/__tests__/finance.test.ts
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  calculateRunway,
  calculateMonthlyBurn,
  clampGrowthRate,
  calculateCashFlowForecast,
  formatRunway,
  normalizeGrossMarginPct,
} from '../finance';

const closeTo = (actual: number, expected: number, digits = 2) =>
  assert.ok(
    Math.abs(actual - expected) < Math.pow(10, -digits) / 2,
    `expected ${actual} to be close to ${expected} (${digits} digits)`,
  );

describe('calculateRunway', () => {
  it('PulsePal: cash=4500, exp=850, rev=520 => ~13.6mo', () => {
    const r = calculateRunway(4500, 850, 520);
    assert.notEqual(r, null);
    closeTo(r as number, 13.6, 0);
  });
  it('profitable => null', () => { assert.equal(calculateRunway(4500, 400, 520), null); });
  it('no cash => 0', () => { assert.equal(calculateRunway(0, 850, 520), 0); });
  it('nulls => null', () => { assert.equal(calculateRunway(null, null, null), null); });
  it('consistent across calls (P0 #2)', () => {
    assert.equal(calculateRunway(4500, 850, 520), calculateRunway(4500, 850, 520));
  });
});

describe('calculateMonthlyBurn', () => {
  it('burning: 850-520=330', () => { assert.equal(calculateMonthlyBurn(850, 520), 330); });
  it('profitable: 400-520=-120', () => { assert.equal(calculateMonthlyBurn(400, 520), -120); });
});

describe('clampGrowthRate (P0 #1)', () => {
  it('5% => 0.05', () => { closeTo(clampGrowthRate(5), 0.05); });
  it('1268% clamped to 1.0', () => { assert.equal(clampGrowthRate(1268), 1.0); });
  it('-200% clamped to -0.5', () => { assert.equal(clampGrowthRate(-200), -0.5); });
  it('null => 0.05 default', () => { closeTo(clampGrowthRate(null), 0.05); });
});

describe('calculateCashFlowForecast (P0 #1)', () => {
  it('no explosion at month 12', () => {
    const fc = calculateCashFlowForecast(520, 850, 4500, 5, 12);
    for (const m of fc) {
      assert.ok(Math.abs(m.cash_balance) < 1e12);
      assert.ok(Math.abs(m.inflow) < 1e12);
    }
  });
  it('12 months output', () => {
    assert.equal(calculateCashFlowForecast(520, 850, 4500).length, 12);
  });
  it('extreme growth still bounded', () => {
    const fc = calculateCashFlowForecast(520, 850, 4500, 1268, 12);
    for (const m of fc) assert.ok(Math.abs(m.cash_balance) < 1e12);
  });
});

describe('formatRunway', () => {
  it('null => Sustainable', () => { assert.equal(formatRunway(null), 'Sustainable'); });
  it('0 => 0 months', () => { assert.equal(formatRunway(0), '0 months'); });
  it('13.6 => 13.6 months', () => { assert.ok(formatRunway(13.6).includes('13.6')); });
});

describe('normalizeGrossMarginPct (P0 #5)', () => {
  it('0.9 => 90', () => { assert.equal(normalizeGrossMarginPct(0.9), 90); });
  it('90 stays 90', () => { assert.equal(normalizeGrossMarginPct(90), 90); });
  it('null => null', () => { assert.equal(normalizeGrossMarginPct(null), null); });
});
