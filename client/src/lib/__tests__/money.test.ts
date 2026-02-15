import { describe, it, expect } from 'vitest';
import {
  scaleMultiplier,
  parseInputToBase,
  baseToDisplayScale,
  formatScaleValue,
  formatBaseToDisplay,
  alertThresholdInBase,
  detectUnitMismatch,
  scaleSuffix,
} from '../money';

describe('money.ts - P0 #3 Regression Tests', () => {
  describe('scaleMultiplier', () => {
    it('units = 1', () => expect(scaleMultiplier('units')).toBe(1));
    it('thousands = 1000', () => expect(scaleMultiplier('thousands')).toBe(1000));
    it('millions = 1000000', () => expect(scaleMultiplier('millions')).toBe(1000000));
    it('crores = 10000000', () => expect(scaleMultiplier('crores')).toBe(10000000));
  });

  describe('parseInputToBase', () => {
    it('520 in thousands = 520000', () => {
      expect(parseInputToBase(520, 'thousands')).toBe(520000);
    });
    it('4.5 in millions = 4500000', () => {
      expect(parseInputToBase(4.5, 'millions')).toBe(4500000);
    });
    it('100 in units = 100', () => {
      expect(parseInputToBase(100, 'units')).toBe(100);
    });
  });

  describe('baseToDisplayScale', () => {
    it('520000 in thousands = 520', () => {
      expect(baseToDisplayScale(520000, 'thousands')).toBe(520);
    });
  });

  describe('formatScaleValue', () => {
    it('adds K suffix for thousands', () => {
      const result = formatScaleValue(520, 'USD', 'thousands');
      expect(result).toContain('520');
      expect(result).toContain('K');
    });
    it('no suffix for units', () => {
      const result = formatScaleValue(520, 'USD', 'units');
      expect(result).toContain('520');
      expect(result).not.toContain('K');
    });
    it('returns N/A for null', () => {
      expect(formatScaleValue(null)).toBe('N/A');
    });
  });

  describe('alertThresholdInBase', () => {
    it('100K threshold in thousands = 100000 in base', () => {
      expect(alertThresholdInBase(100, 'thousands')).toBe(100000);
    });
    it('PulsePal: cash 4500K (4.5M) should NOT trigger <100K alert', () => {
      const cashInBase = parseInputToBase(4500, 'thousands'); // 4,500,000
      const thresholdInBase = alertThresholdInBase(100, 'thousands'); // 100,000
      expect(cashInBase).toBeGreaterThan(thresholdInBase);
    });
  });

  describe('detectUnitMismatch', () => {
    it('warns when entering large values in thousands', () => {
      const result = detectUnitMismatch(500000, 'thousands');
      expect(result?.warning).toBe(true);
    });
    it('no warning for reasonable values', () => {
      const result = detectUnitMismatch(520, 'thousands');
      expect(result).toBeNull();
    });
  });
});
