/**
 * One set of thresholds for everything /overview says about health.
 *
 * Testers saw the briefing say "All clear." next to a runway figure, a KPI
 * tile in amber and a "Critical Issues" box — because the briefing only
 * counted the client-side risk alerts, the cash card, the KPI grid and the
 * risk alerts each had their own runway cut-offs, and truth-scan flags were
 * never counted. Every runway colour and the briefing's verdict now come from
 * here.
 *
 * Runway bands (months of cash at current net burn):
 *   < 6        critical
 *   6 – 12     warning
 *   12 – 18    watch (start preparing a raise)
 *   >= 18      healthy
 *   Infinity   profitable (not burning)
 *   NaN        unknown (no cash, or nothing to score)
 */

export const RUNWAY_CRITICAL_MONTHS = 6;
export const RUNWAY_WARNING_MONTHS = 12;
export const RUNWAY_WATCH_MONTHS = 18;

export type RunwayBand = 'critical' | 'warning' | 'watch' | 'healthy' | 'profitable' | 'unknown';

export function runwayBand(months: number): RunwayBand {
  if (months === Infinity) return 'profitable';
  if (typeof months !== 'number' || !Number.isFinite(months)) return 'unknown';
  if (months < RUNWAY_CRITICAL_MONTHS) return 'critical';
  if (months < RUNWAY_WARNING_MONTHS) return 'warning';
  if (months < RUNWAY_WATCH_MONTHS) return 'watch';
  return 'healthy';
}

/** MetricCard variant for a runway band (cash card subtitle colour). */
export function runwayCardVariant(band: RunwayBand): 'danger' | 'warning' | 'success' | undefined {
  switch (band) {
    case 'critical':
      return 'danger';
    case 'warning':
    case 'watch':
      return 'warning';
    case 'healthy':
    case 'profitable':
      return 'success';
    default:
      return undefined;
  }
}

export type KpiStatus = 'green' | 'yellow' | 'red';

/** KPI tile status for a runway band. */
export function runwayKpiStatus(band: RunwayBand): KpiStatus {
  switch (band) {
    case 'critical':
      return 'red';
    case 'warning':
    case 'watch':
    case 'unknown':
      return 'yellow';
    default:
      return 'green';
  }
}

export type StatusLevel = 'critical' | 'warning' | 'watch';

export type DashboardStatusInput = {
  /** Revenue or expenses exist, so there is something to score. */
  hasData: boolean;
  /** Months of runway; Infinity = not burning, NaN = unknown. */
  runwayMonths: number;
  /** Risk alerts shown on the page (keyed by metric so a KPI on the same metric is not counted twice). */
  alerts: Array<{ type: 'critical' | 'warning' | 'info'; metric: string; title?: string }>;
  /** Number of high-severity truth-scan flags shown in the "Critical Issues" box. */
  highSeverityFlagCount: number;
  /** KPI tiles shown on the page; `status` null when the tile shows N/A. */
  kpis: Array<{ name: string; metric: string; status: KpiStatus | null }>;
};

export type DashboardStatus = {
  kind: 'not_scored' | 'critical' | 'warning' | 'watch' | 'all_clear';
  criticalCount: number;
  warningCount: number;
  watchCount: number;
  /** Human names of the metrics at "watch" level, for the briefing sentence. */
  watchNames: string[];
};

/** KPI keys and alert keys name the same metric differently. */
const METRIC_ALIASES: Record<string, string> = {
  ltv_cac: 'ltvCac',
  ltvCacRatio: 'ltvCac',
};

const RANK: Record<StatusLevel, number> = { watch: 1, warning: 2, critical: 3 };

/**
 * The briefing's verdict. "All clear" only when every metric shown on the
 * page is healthy; never for a company with nothing to score.
 */
export function dashboardStatus(input: DashboardStatusInput): DashboardStatus {
  if (!input.hasData) {
    return { kind: 'not_scored', criticalCount: 0, warningCount: 0, watchCount: 0, watchNames: [] };
  }

  const items = new Map<string, { level: StatusLevel; name: string }>();
  const raise = (key: string, level: StatusLevel, name: string) => {
    const k = METRIC_ALIASES[key] ?? key;
    const prev = items.get(k);
    if (!prev || RANK[level] > RANK[prev.level]) items.set(k, { level, name: prev?.name ?? name });
  };

  for (const a of input.alerts) {
    if (a.type === 'critical') raise(a.metric, 'critical', a.title ?? a.metric);
    else if (a.type === 'warning') raise(a.metric, 'warning', a.title ?? a.metric);
  }

  const band = runwayBand(input.runwayMonths);
  if (band === 'critical' || band === 'warning' || band === 'watch') raise('runway', band, 'Runway');

  for (const k of input.kpis) {
    if (k.status === 'red') raise(k.metric, 'warning', k.name);
    else if (k.status === 'yellow') raise(k.metric, 'watch', k.name);
  }

  for (let i = 0; i < input.highSeverityFlagCount; i++) raise(`flag:${i}`, 'critical', 'Critical issue');

  let criticalCount = 0;
  let warningCount = 0;
  const watchNames: string[] = [];
  items.forEach((it) => {
    if (it.level === 'critical') criticalCount++;
    else if (it.level === 'warning') warningCount++;
    else watchNames.push(it.name);
  });
  const watchCount = watchNames.length;

  const kind: DashboardStatus['kind'] =
    criticalCount > 0 ? 'critical' : warningCount > 0 ? 'warning' : watchCount > 0 ? 'watch' : 'all_clear';
  return { kind, criticalCount, warningCount, watchCount, watchNames };
}

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** Closing sentence of the morning briefing. */
export function dashboardStatusSentence(s: DashboardStatus): string {
  switch (s.kind) {
    case 'not_scored':
      return 'Not scored yet — add your revenue, expenses and cash balance to get health alerts.';
    case 'critical':
      return s.warningCount > 0
        ? `${plural(s.criticalCount, 'critical alert')} and ${plural(s.warningCount, 'warning')} detected.`
        : `${plural(s.criticalCount, 'critical alert')} detected.`;
    case 'warning':
      return `${plural(s.warningCount, 'warning')} to review.`;
    case 'watch':
      return `${plural(s.watchCount, 'metric')} to watch: ${s.watchNames.join(', ')}.`;
    default:
      return 'All clear.';
  }
}
