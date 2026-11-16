/**
 * The API writes datetimes as naive UTC ISO strings ("2026-11-16T21:40:44").
 * `new Date()` reads those as LOCAL time, so a founder in India saw data
 * entered a moment ago as "about 5 hours ago". Treat a timestamp with no
 * zone as UTC; strings that already carry a zone (Z / +05:30) are unchanged.
 */
export function parseServerDate(value: string | number | Date): Date {
  if (value instanceof Date || typeof value === 'number') return new Date(value);
  const s = value.trim();
  const isDateTime = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/.test(s);
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/i.test(s);
  return new Date(isDateTime && !hasZone ? `${s.replace(' ', 'T')}Z` : s);
}
