import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format currency with abbreviations for large numbers
 * Displays: $1.5M, $250K, $13.9K, $1,500 (with proper currency symbol)
 * Never rounds small non-zero values to $0
 */
export function formatCurrencyAbbrev(value: number | null | undefined, currency = 'USD'): string {
  if (value == null || isNaN(value)) return 'N/A';
  
  const absValue = Math.abs(value);
  const sign = value < 0 ? '-' : '';
  
  const symbol = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(0).replace(/[0-9]/g, '').trim();
  
  if (absValue >= 1000000) {
    const millions = absValue / 1000000;
    return `${sign}${symbol}${millions >= 10 ? millions.toFixed(1) : millions.toFixed(2)}M`;
  }
  if (absValue >= 1000) {
    const thousands = absValue / 1000;
    return `${sign}${symbol}${thousands >= 100 ? thousands.toFixed(0) : thousands.toFixed(1)}K`;
  }
  if (absValue > 0 && absValue < 1) {
    return `${sign}${symbol}${absValue.toFixed(2)}`;
  }
  return `${sign}${symbol}${absValue.toFixed(0)}`;
}

/**
 * Format currency with full number formatting
 * Displays: $1,500,000
 */
export function formatCurrencyFull(value: number | null | undefined, currency = 'USD'): string {
  if (value == null || isNaN(value)) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Format percentage value
 */
export function formatPercent(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return 'N/A';
  return `${value.toFixed(1)}%`;
}

/**
 * CANONICAL RUNWAY CALCULATION
 * Use this single function everywhere runway is displayed.
 * 
 * @param cashBalance - Current cash on hand
 * @param totalExpenses - Total monthly expenses (opex + payroll + other)
 * @param revenue - Monthly revenue
 * @returns Runway in months, or null if sustainable/infinite
 */
export function calculateRunway(
  cashBalance: number | null | undefined,
  totalExpenses: number | null | undefined,
  revenue: number | null | undefined
): number | null {
  const cash = cashBalance ?? 0;
  const expenses = totalExpenses ?? 0;
  const rev = revenue ?? 0;
  
  const netBurn = expenses - rev;
  
  // If profitable or break-even, runway is infinite
  if (netBurn <= 0) return null;
  
  // If no cash, runway is 0
  if (cash <= 0) return 0;
  
  return cash / netBurn;
}

/**
 * Format runway value for display
 * @param runwayMonths - Runway in months (or null for infinite)
 * @param maxDisplay - Maximum months to display before showing "60+"
 */
export function formatRunway(runwayMonths: number | null | undefined, maxDisplay = 60): string {
  if (runwayMonths === null || runwayMonths === undefined) {
    return 'Sustainable';
  }
  if (isNaN(runwayMonths)) {
    return 'N/A';
  }
  if (runwayMonths > maxDisplay) {
    return `${maxDisplay}+`;
  }
  return `${runwayMonths.toFixed(1)} mo`;
}

/**
 * Safely convert a number for display, handling NaN and null
 */
export function safeNumber(value: number | null | undefined, fallback = 0): number {
  if (value === null || value === undefined || isNaN(value)) {
    return fallback;
  }
  return value;
}

/**
 * Safe toFixed that handles NaN and null
 */
export function safeToFixed(value: number | null | undefined, decimals = 1, fallback = 'N/A'): string {
  if (value === null || value === undefined || isNaN(value)) {
    return fallback;
  }
  return value.toFixed(decimals);
}

/**
 * Format chart tooltip value, safely handling NaN
 */
export function formatChartTooltip(
  value: number | null | undefined, 
  type: 'currency' | 'percent' | 'number' = 'currency',
  currency: string = 'USD'
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return 'N/A';
  }
  
  switch (type) {
    case 'currency':
      return formatCurrencyAbbrev(value, currency);
    case 'percent':
      return formatPercent(value);
    case 'number':
      return value.toLocaleString();
    default:
      return String(value);
  }
}

export type AmountScale = 'UNITS' | 'THOUSANDS' | 'MILLIONS' | 'CRORES';

export const SCALE_MULTIPLIERS: Record<AmountScale, number> = {
  UNITS: 1,
  THOUSANDS: 1e3,
  MILLIONS: 1e6,
  CRORES: 1e7,
};

export const SCALE_LABELS: Record<AmountScale, string> = {
  UNITS: '',
  THOUSANDS: 'K',
  MILLIONS: 'M',
  CRORES: 'Cr',
};

export function parseScaledAmount(inputNumber: number, scale: AmountScale): number {
  return inputNumber * SCALE_MULTIPLIERS[scale];
}

export function formatScaledAmount(
  baseAmount: number | null | undefined,
  currency: string,
  scale: AmountScale,
  options?: { compact?: boolean; decimals?: number }
): string {
  if (baseAmount == null || isNaN(baseAmount)) return 'N/A';
  const displayValue = baseAmount / SCALE_MULTIPLIERS[scale];
  const locale = currency === 'INR' ? 'en-IN' : currency === 'JPY' ? 'ja-JP' : currency === 'EUR' ? 'de-DE' : currency === 'GBP' ? 'en-GB' : 'en-US';
  const decimals = options?.decimals ?? (displayValue >= 100 ? 0 : displayValue >= 1 ? 1 : 2);

  const formatted = new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
  }).format(displayValue);

  const suffix = SCALE_LABELS[scale];
  return suffix ? `${formatted} ${suffix}` : formatted;
}
