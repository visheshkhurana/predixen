/**
 * money.ts - SINGLE SOURCE OF TRUTH for money formatting and parsing.
 * All money display and input should go through these functions.
 * Phase 1 fix for P0 #3 (scale not applied) and P0 #6 (AI briefing wrong values).
 */

export type AmountScale = 'units' | 'thousands' | 'millions' | 'crores';

/** Multiplier to convert from input-scale to base (actual) units */
export function scaleMultiplier(scale: AmountScale): number {
  switch (scale) {
    case 'units': return 1;
    case 'thousands': return 1_000;
    case 'millions': return 1_000_000;
    case 'crores': return 10_000_000;
    default: return 1;
  }
}

/** Scale label for display badges */
export function scaleLabel(scale: AmountScale): string {
  switch (scale) {
    case 'units': return 'Units';
    case 'thousands': return 'K (Thousands)';
    case 'millions': return 'M (Millions)';
    case 'crores': return 'Cr (Crores)';
    default: return 'Units';
  }
}

/** Short scale suffix */
export function scaleSuffix(scale: AmountScale): string {
  switch (scale) {
    case 'units': return '';
    case 'thousands': return 'K';
    case 'millions': return 'M';
    case 'crores': return 'Cr';
    default: return '';
  }
}

/**
 * Convert a user-entered value (in the company's input scale) to base units.
 * e.g. parseInputToBase(520, 'thousands') => 520000
 */
export function parseInputToBase(inputValue: number, scale: AmountScale): number {
  return inputValue * scaleMultiplier(scale);
}

/**
 * Convert a base-unit value back to the company's display scale.
 * e.g. baseToDisplayScale(520000, 'thousands') => 520
 */
export function baseToDisplayScale(baseValue: number, scale: AmountScale): number {
  const mult = scaleMultiplier(scale);
  return mult === 0 ? baseValue : baseValue / mult;
}

/**
 * Format a value that's ALREADY in the company's input scale for display.
 * This adds the currency symbol and scale suffix.
 * e.g. formatScaleValue(520, 'USD', 'thousands') => "$520K"
 */
export function formatScaleValue(
  value: number | null | undefined,
  currencyCode: string = 'USD',
  scale: AmountScale = 'units',
  locale: string = 'en-US',
  decimals: number = 0,
): string {
  if (value == null || isNaN(value)) return 'N/A';

  const suffix = scaleSuffix(scale);
  
  try {
    const formatted = new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: currencyCode,
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
      notation: 'standard',
    }).format(value);
    return suffix ? `${formatted}${suffix}` : formatted;
  } catch {
    return `$${value.toFixed(decimals)}${suffix}`;
  }
}

/**
 * Format a BASE value for display, automatically choosing appropriate notation.
 * e.g. formatBaseToDisplay(520000, 'USD') => "$520K"
 *      formatBaseToDisplay(4500000, 'USD') => "$4.5M"
 */
export function formatBaseToDisplay(
  baseValue: number | null | undefined,
  currencyCode: string = 'USD',
  locale: string = 'en-US',
  decimals: number = 1,
): string {
  if (baseValue == null || isNaN(baseValue)) return 'N/A';

  const abs = Math.abs(baseValue);
  const sign = baseValue < 0 ? '-' : '';

  try {
    const formatted = new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: currencyCode,
      minimumFractionDigits: 0,
      maximumFractionDigits: decimals,
      notation: 'compact',
      compactDisplay: 'short',
    }).format(abs);
    return sign + formatted;
  } catch {
    // Fallback for environments without compact notation
    if (abs >= 1_000_000_000) return `${sign}$${(abs / 1_000_000_000).toFixed(decimals)}B`;
    if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(decimals)}M`;
    if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(decimals)}K`;
    return `${sign}$${abs.toFixed(0)}`;
  }
}

/**
 * For alert thresholds: compare in base units.
 * alertThresholdInBase(100, 'thousands') => 100000
 */
export function alertThresholdInBase(thresholdInScale: number, scale: AmountScale): number {
  return parseInputToBase(thresholdInScale, scale);
}

/**
 * Smart unit mismatch detection: checks if a user-entered value
 * seems too large or too small for the given scale.
 */
export function detectUnitMismatch(
  value: number,
  scale: AmountScale,
  fieldType: 'revenue' | 'expense' | 'cash' = 'revenue'
): { warning: boolean; message: string } | null {
  if (scale === 'units') return null;

  const baseValue = parseInputToBase(value, scale);
  
  // If entering in thousands but value looks like it's already in base units
  if (scale === 'thousands' && value > 100_000) {
    return {
      warning: true,
      message: `You entered ${value.toLocaleString()} in Thousands mode. That equals ${formatBaseToDisplay(baseValue)}. Did you mean to enter in Units?`
    };
  }

  if (scale === 'millions' && value > 10_000) {
    return {
      warning: true,
      message: `You entered ${value.toLocaleString()} in Millions mode. That equals ${formatBaseToDisplay(baseValue)}. Did you mean to enter in Thousands?`
    };
  }

  return null;
}

/**
 * Build a context string for AI prompts that includes scale information.
 * This ensures the LLM understands the actual dollar amounts.
 */
export function buildAIMoneyContext(
  values: Record<string, number | null | undefined>,
  scale: AmountScale,
  currencyCode: string = 'USD'
): string {
  const lines: string[] = [];
  lines.push(`IMPORTANT: All financial values below are in ${currencyCode}. Input scale: ${scale.toUpperCase()} (multiply displayed values by ${scaleMultiplier(scale).toLocaleString()} to get actual amounts).`);
  
  for (const [key, val] of Object.entries(values)) {
    if (val == null) continue;
    const baseVal = parseInputToBase(val, scale);
    const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    lines.push(`${label}: ${formatScaleValue(val, currencyCode, scale)} (actual: ${formatBaseToDisplay(baseVal, currencyCode)})`);
  }
  
  return lines.join('\n');
}
