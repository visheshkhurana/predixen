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
