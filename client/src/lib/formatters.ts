export function formatPercent(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined || isNaN(value)) return 'N/A';
  const fixed = Number(value).toFixed(decimals);
  const clean = fixed.includes('.') ? fixed.replace(/\.?0+$/, '') : fixed;
  return `${clean}%`;
}

export { formatCurrencyAbbrev } from '@/lib/utils';

export function formatCurrency(value: number | null | undefined, prefix = '$'): string {
  if (value === null || value === undefined || isNaN(value)) return 'N/A';
  const absValue = Math.abs(value);
  const sign = value < 0 ? '-' : '';
  if (absValue >= 1_000_000) {
    const f = (absValue / 1_000_000).toFixed(1).replace(/\.0$/, '');
    return `${sign}${prefix}${f}M`;
  }
  if (absValue >= 1_000) {
    const f = (absValue / 1_000).toFixed(1).replace(/\.0$/, '');
    return `${sign}${prefix}${f}K`;
  }
  if (absValue > 0 && absValue < 1) return `${sign}${prefix}${absValue.toFixed(2)}`;
  return `${sign}${prefix}${absValue.toFixed(0)}`;
}

export function formatMonths(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) return 'N/A';
  return `${value.toFixed(1).replace(/\.0$/, '')} mo`;
}

export function formatRatio(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) return 'N/A';
  return `${value.toFixed(1).replace(/\.0$/, '')}x`;
}

export function formatMetricName(snakeCaseName: string): string {
  return snakeCaseName
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export function safeRatio(numerator: number | null | undefined, denominator: number | null | undefined): number | null {
  if (
    numerator === null || numerator === undefined || isNaN(numerator) || numerator === 0 ||
    denominator === null || denominator === undefined || isNaN(denominator) || denominator === 0
  ) {
    return null;
  }
  return numerator / denominator;
}
