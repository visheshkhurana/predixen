import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format currency with abbreviations for large numbers
 * Displays: $1.5M, $250K, $1,500 (with proper currency symbol)
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
    return `${sign}${symbol}${(absValue / 1000000).toFixed(1)}M`;
  }
  if (absValue >= 1000) {
    return `${sign}${symbol}${(absValue / 1000).toFixed(0)}K`;
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
