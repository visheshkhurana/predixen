import { describe, it, expect } from 'vitest';
import { calculateRunway, calculateMonthlyBurn, calculateNetBurnRate, clampGrowthRate, calculateCashFlowForecast, formatRunway, normalizeGrossMarginPct } from '../finance';

describe('calculateRunway', () => {
  it('PulsePal: cash=4500, exp=850, rev=520 => ~13.6mo', () => {
    const r = calculateRunway(4500, 850, 520);
    expect(r).not.toBeNull();
    expect(r).toBeCloseTo(13.6, 0);
  });
  it('profitable => null', () => { expect(calculateRunway(4500, 400, 520)).toBeNull(); });
  it('no cash => 0', () => { expect(calculateRunway(0, 850, 520)).toBe(0); });
  it('nulls => null', () => { expect(calculateRunway(null, null, null)).toBeNull(); });
  it('consistent across calls (P0 #2)', () => {
    const a = calculateRunway(4500, 850, 520);
    const b = calculateRunway(4500, 850, 520);
    expect(a).toBe(b);
  });
});

describe('calculateMonthlyBurn', () => {
  it('burning: 850-520=330', () => { expect(calculateMonthlyBurn(850, 520)).toBe(330); });
  it('profitable: 400-520=-120', () => { expect(calculateMonthlyBurn(400, 520)).toBe(-120); });
});

describe('clampGrowthRate (P0 #1)', () => {
  it('5% => 0.05', () => { expect(clampGrowthRate(5)).toBeCloseTo(0.05); });
  it('1268% clamped to 1.0', () => { expect(clampGrowthRate(1268)).toBe(1.0); });
  it('-200% clamped to -0.5', () => { expect(clampGrowthRate(-200)).toBe(-0.5); });
  it('null => 0.05 default', () => { expect(clampGrowthRate(null)).toBeCloseTo(0.05); });
});

describe('calculateCashFlowForecast (P0 #1)', () => {
  it('no explosion at month 12', () => {
    const fc = calculateCashFlowForecast(520, 850, 4500, 5, 12);
    fc.forEach(m => {
      expect(Math.abs(m.cash_balance)).toBeLessThan(1e12);
      expect(Math.abs(m.inflow)).toBeLessThan(1e12);
    });
  });
  it('12 months output', () => {
    const fc = calculateCashFlowForecast(520, 850, 4500);
    expect(fc.length).toBe(12);
  });
  it('extreme growth still bounded', () => {
    const fc = calculateCashFlowForecast(520, 850, 4500, 1268, 12);
    fc.forEach(m => expect(Math.abs(m.cash_balance)).toBeLessThan(1e12));
  });
});

describe('formatRunway', () => {
  it('null => Sustainable', () => { expect(formatRunway(null)).toBe('Sustainable'); });
  it('0 => 0 months', () => { expect(formatRunway(0)).toBe('0 months'); });
  it('13.6 => 13.6 months', () => { expect(formatRunway(13.6)).toContain('13.6'); });
});

describe('normalizeGrossMarginPct (P0 #5)', () => {
  it('0.9 => 90', () => { expect(normalizeGrossMarginPct(0.9)).toBe(90); });
  it('90 stays 90', () => { expect(normalizeGrossMarginPct(90)).toBe(90); });
  it('null => null', () => { expect(normalizeGrossMarginPct(null)).toBeNull(); });
});
