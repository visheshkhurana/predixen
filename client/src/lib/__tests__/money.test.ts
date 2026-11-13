// Run: npx tsx --test client/src/lib/__tests__/money.test.ts
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  scaleMultiplier,
  parseInputToBase,
  baseToDisplayScale,
  formatScaleValue,
  alertThresholdInBase,
  detectUnitMismatch,
} from '../money';

describe('money.ts - P0 #3 Regression Tests', () => {
  describe('scaleMultiplier', () => {
    it('units = 1', () => assert.equal(scaleMultiplier('units'), 1));
    it('thousands = 1000', () => assert.equal(scaleMultiplier('thousands'), 1000));
    it('millions = 1000000', () => assert.equal(scaleMultiplier('millions'), 1000000));
    it('crores = 10000000', () => assert.equal(scaleMultiplier('crores'), 10000000));
  });

  describe('parseInputToBase', () => {
    it('520 in thousands = 520000', () => {
      assert.equal(parseInputToBase(520, 'thousands'), 520000);
    });
    it('4.5 in millions = 4500000', () => {
      assert.equal(parseInputToBase(4.5, 'millions'), 4500000);
    });
    it('100 in units = 100', () => {
      assert.equal(parseInputToBase(100, 'units'), 100);
    });
  });

  describe('baseToDisplayScale', () => {
    it('520000 in thousands = 520', () => {
      assert.equal(baseToDisplayScale(520000, 'thousands'), 520);
    });
  });

  describe('formatScaleValue', () => {
    it('adds K suffix for thousands', () => {
      const result = formatScaleValue(520, 'USD', 'thousands');
      assert.ok(result.includes('520'), result);
      assert.ok(result.includes('K'), result);
    });
    it('no suffix for units', () => {
      const result = formatScaleValue(520, 'USD', 'units');
      assert.ok(result.includes('520'), result);
      assert.ok(!result.includes('K'), result);
    });
    it('returns N/A for null', () => {
      assert.equal(formatScaleValue(null), 'N/A');
    });
  });

  describe('alertThresholdInBase', () => {
    it('100K threshold in thousands = 100000 in base', () => {
      assert.equal(alertThresholdInBase(100, 'thousands'), 100000);
    });
    it('PulsePal: cash 4500K (4.5M) should NOT trigger <100K alert', () => {
      const cashInBase = parseInputToBase(4500, 'thousands'); // 4,500,000
      const thresholdInBase = alertThresholdInBase(100, 'thousands'); // 100,000
      assert.ok(cashInBase > thresholdInBase);
    });
  });

  describe('detectUnitMismatch', () => {
    it('warns when entering large values in thousands', () => {
      const result = detectUnitMismatch(500000, 'thousands');
      assert.equal(result?.warning, true);
    });
    it('no warning for reasonable values', () => {
      assert.equal(detectUnitMismatch(520, 'thousands'), null);
    });
  });
});
