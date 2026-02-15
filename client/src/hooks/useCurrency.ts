import { useCallback, useMemo } from 'react';
import { useFounderStore } from '@/store/founderStore';
import { formatCurrencyAbbrev, formatCurrencyFull, AmountScale, SCALE_MULTIPLIERS, SCALE_LABELS, parseScaledAmount, formatScaledAmount } from '@/lib/utils';

const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$', EUR: '\u20AC', GBP: '\u00A3', INR: '\u20B9', JPY: '\u00A5',
  CNY: '\u00A5', KRW: '\u20A9', BRL: 'R$', CHF: 'CHF', SEK: 'kr',
  AED: 'AED', HKD: 'HK$', MXN: 'MX$', ILS: '\u20AA', NGN: '\u20A6',
  KES: 'KSh', ZAR: 'R', SGD: 'S$', AUD: 'A$', CAD: 'C$',
};

export function useCurrency() {
  const { currentCompany } = useFounderStore();
  const currency = (currentCompany as any)?.currency || 'USD';
  const symbol = CURRENCY_SYMBOLS[currency] || currency;
  const scale: AmountScale = (currentCompany as any)?.amount_scale || 'UNITS';
  const scaleLabel = SCALE_LABELS[scale];
  const scaleMultiplier = SCALE_MULTIPLIERS[scale];

  const format = useCallback(
    (value: number | null | undefined) => {
      // P0 FIX #3: Add scale suffix to displayed values
      const formatted = formatCurrencyAbbrev(value, currency);
      if (formatted === 'N/A' || formatted === '$0') return formatted;
      const suffix = scale === 'UNITS' ? '' : scale === 'THOUSANDS' ? 'K' : scale === 'MILLIONS' ? 'M' : scale === 'CRORES' ? 'Cr' : '';
      return suffix ? `${formatted}${suffix}` : formatted;
    },
    [currency, scale]
  );

  const formatFull = useCallback(
    (value: number | null | undefined) => formatCurrencyFull(value, currency),
    [currency]
  );

  const parseInput = useCallback(
    (value: number) => parseScaledAmount(value, scale),
    [scale]
  );

  const formatOutput = useCallback(
    (value: number | null | undefined) => formatScaledAmount(value, currency, scale),
    [currency, scale]
  );

  return useMemo(() => ({
    currency, symbol, format, formatFull,
    scale, scaleLabel, scaleMultiplier, parseInput, formatOutput
  }), [currency, symbol, format, formatFull, scale, scaleLabel, scaleMultiplier, parseInput, formatOutput]);
}
