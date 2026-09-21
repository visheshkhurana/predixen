/**
 * Truth Scan → Scenarios prefill (product bet #4).
 *
 * Suggested Actions on /truth-scan deep-link into the live /simulate route
 * with wizard-native query params so the founder lands ready to run.
 * Modeling (server/truth/truth_scan.py) is intentionally not involved —
 * red metrics come from the Truth Scan payload the page already has.
 */

export const TRUTH_SCAN_SIM_SOURCE = 'truth_scan';
export const TRUTH_SCAN_SIM_FROM = 'truth_scan_suggested_action';
export const SIM_ATTRIBUTION_KEY = 'fc_sim_attribution';
export const SUGGESTED_ACTIONS_MAX = 3;

export type SuggestedActionType =
  | 'retention'
  | 'runway'
  | 'burn'
  | 'margin'
  | 'growth'
  | 'acquisition';

export type SimulationGoal = 'extend_runway' | 'accelerate_growth' | 'balance';

export type ScenarioWizardParams = {
  name: string;
  pricing_change_pct: number;
  growth_uplift_pct: number;
  burn_reduction_pct: number;
  gross_margin_delta_pct: number;
  churn_change_pct: number;
  cac_change_pct: number;
  fundraise_month: number | null;
  fundraise_amount: number;
  tags: string[];
};

export type SuggestedAction = {
  id: string;
  title: string;
  description: string;
  metricIssue: string;
  actionType: SuggestedActionType;
  scenarioName: string;
  scenarioParams: Record<string, string | number | null>;
  priority: 'high' | 'medium' | 'low';
  goal: SimulationGoal;
  strategyId: string;
  templateId: string;
  wizardParams: Omit<ScenarioWizardParams, 'name' | 'tags'>;
};

export type SimulationAttribution = {
  source: typeof TRUTH_SCAN_SIM_SOURCE;
  from: typeof TRUTH_SCAN_SIM_FROM;
  action_id: string;
  action_type: SuggestedActionType;
};

export type ScenarioPrefill = {
  from: typeof TRUTH_SCAN_SIM_SOURCE;
  actionId: string;
  actionType: SuggestedActionType;
  name: string;
  goal: SimulationGoal;
  strategyId: string;
  templateId: string;
  params: Omit<ScenarioWizardParams, 'name' | 'tags'>;
};

function getMetricValue(metric: unknown): number | null {
  if (metric === null || metric === undefined) return null;
  if (typeof metric === 'number') return Number.isFinite(metric) ? metric : null;
  if (typeof metric === 'object' && metric !== null && 'value' in metric) {
    return getMetricValue((metric as { value: unknown }).value);
  }
  return null;
}

function asChurnRate(raw: number | null): number | null {
  if (raw === null) return null;
  return raw > 1 ? raw / 100 : raw;
}

const EMPTY_WIZARD_PARAMS: Omit<ScenarioWizardParams, 'name' | 'tags'> = {
  pricing_change_pct: 0,
  growth_uplift_pct: 0,
  burn_reduction_pct: 0,
  gross_margin_delta_pct: 0,
  churn_change_pct: 0,
  cac_change_pct: 0,
  fundraise_month: null,
  fundraise_amount: 0,
};

function wizardQueryParams(action: SuggestedAction): Record<string, string | number | null> {
  const p = action.wizardParams;
  return {
    from: TRUTH_SCAN_SIM_SOURCE,
    action: action.id,
    action_type: action.actionType,
    goal: action.goal,
    strategy: action.strategyId,
    scenario: action.templateId,
    name: action.scenarioName,
    pricing_change_pct: p.pricing_change_pct,
    growth_uplift_pct: p.growth_uplift_pct,
    burn_reduction_pct: p.burn_reduction_pct,
    gross_margin_delta_pct: p.gross_margin_delta_pct,
    churn_change_pct: p.churn_change_pct,
    cac_change_pct: p.cac_change_pct,
    fundraise_month: p.fundraise_month,
    fundraise_amount: p.fundraise_amount,
  };
}

/**
 * 2–3 CTAs from the reddest Truth Scan metrics. Prefills use the same lever
 * names ScenarioWizard / StrategicScenarioBuilder already persist.
 */
export function generateSuggestedActions(metrics: any, _flags: any[] = []): SuggestedAction[] {
  const actions: SuggestedAction[] = [];

  const runwayP50 = getMetricValue(metrics?.runway_p50);
  const burnMultiple = getMetricValue(metrics?.burn_multiple);
  const grossMargin = getMetricValue(metrics?.gross_margin);
  const churnRate = asChurnRate(
    getMetricValue(metrics?.churn_rate_customer) ||
      getMetricValue(metrics?.churn_rate_revenue) ||
      getMetricValue(metrics?.churn_rate),
  );
  const runwaySustainable = metrics?.runway_sustainable === true;

  if (runwayP50 != null && runwayP50 < 12 && !runwaySustainable) {
    actions.push({
      id: 'action-runway',
      title: 'Model Fundraising Round',
      description: `With ${runwayP50.toFixed(1)} months of runway, model a $500K bridge in month 3 and run it.`,
      metricIssue: `Runway is ${runwayP50.toFixed(1)} months`,
      actionType: 'runway',
      scenarioName: 'Truth Scan · Bridge Round',
      priority: 'high',
      goal: 'balance',
      strategyId: 'balance_bridge',
      templateId: 'bridge-round',
      wizardParams: {
        ...EMPTY_WIZARD_PARAMS,
        growth_uplift_pct: 10,
        fundraise_month: 3,
        fundraise_amount: 500000,
      },
      scenarioParams: {},
    });
  }

  if (burnMultiple != null && burnMultiple > 2.5) {
    actions.push({
      id: 'action-burn',
      title: 'Run Cost Optimization Scenario',
      description: 'Test a 15% operating-expense cut (conservative cost cutting) to extend runway.',
      metricIssue: `Burn multiple is ${burnMultiple.toFixed(1)}x (target: <1.5x)`,
      actionType: 'burn',
      scenarioName: 'Truth Scan · Cost Optimization',
      priority: 'high',
      goal: 'extend_runway',
      strategyId: 'extend_conservative',
      templateId: 'conservative-cut',
      wizardParams: {
        ...EMPTY_WIZARD_PARAMS,
        burn_reduction_pct: 15,
      },
      scenarioParams: {},
    });
  } else if (runwayP50 != null && runwayP50 < 12 && !runwaySustainable) {
    // Short runway without a burn-multiple signal still gets a cost-cut companion.
    actions.push({
      id: 'action-burn',
      title: 'Run Cost Optimization Scenario',
      description: 'Pair the raise with a 15% expense cut so the round lasts longer.',
      metricIssue: `Runway is ${runwayP50.toFixed(1)} months`,
      actionType: 'burn',
      scenarioName: 'Truth Scan · Cost Optimization',
      priority: 'high',
      goal: 'extend_runway',
      strategyId: 'extend_conservative',
      templateId: 'conservative-cut',
      wizardParams: {
        ...EMPTY_WIZARD_PARAMS,
        burn_reduction_pct: 15,
      },
      scenarioParams: {},
    });
  }

  if (grossMargin != null && grossMargin < 65) {
    actions.push({
      id: 'action-margin',
      title: 'Test Pricing Optimization',
      description: 'Model a 12% price increase and +8pp gross margin, then run the scenario.',
      metricIssue: `Gross margin is ${grossMargin.toFixed(0)}% (target: 70%+)`,
      actionType: 'margin',
      scenarioName: 'Truth Scan · Price Increase',
      priority: 'high',
      goal: 'extend_runway',
      strategyId: 'extend_pricing',
      templateId: 'price-increase',
      wizardParams: {
        ...EMPTY_WIZARD_PARAMS,
        pricing_change_pct: 12,
        growth_uplift_pct: -5,
        gross_margin_delta_pct: 8,
        churn_change_pct: -3,
      },
      scenarioParams: {},
    });
  }

  if (churnRate != null && churnRate > 0.08) {
    actions.push({
      id: 'action-churn',
      title: 'Run Retention Improvement Scenario',
      description: 'Model a 5pp churn reduction (better onboarding / CS) and run it.',
      metricIssue: `Monthly churn is ${(churnRate * 100).toFixed(1)}% (benchmark: 3–5%)`,
      actionType: 'retention',
      scenarioName: 'Truth Scan · Retention',
      priority: 'high',
      goal: 'balance',
      strategyId: 'balance_efficient',
      templateId: 'unit-economics',
      wizardParams: {
        ...EMPTY_WIZARD_PARAMS,
        pricing_change_pct: 5,
        growth_uplift_pct: 10,
        burn_reduction_pct: 10,
        gross_margin_delta_pct: 5,
        churn_change_pct: -5,
        cac_change_pct: -15,
      },
      scenarioParams: {},
    });
  }

  const sliced = actions.slice(0, SUGGESTED_ACTIONS_MAX);
  return sliced.map((action) => ({
    ...action,
    scenarioParams: wizardQueryParams(action),
  }));
}

export function buildSimulateUrl(
  action: SuggestedAction,
  companyId?: string | number,
): string {
  const params = new URLSearchParams();
  Object.entries(action.scenarioParams).forEach(([key, value]) => {
    if (value !== null && value !== undefined) {
      params.append(key, String(value));
    }
  });
  if (companyId != null && companyId !== '') {
    params.set('company', String(companyId));
  }
  const qs = params.toString();
  return `/simulate${qs ? `?${qs}` : ''}`;
}

function parseNumber(raw: string | null, fallback = 0): number {
  if (raw == null || raw === '' || raw === 'null') return fallback;
  const n = Number(raw);
  return Number.isFinite(n) ? n : fallback;
}

function parseOptionalInt(raw: string | null): number | null {
  if (raw == null || raw === '' || raw === 'null') return null;
  const n = parseInt(raw, 10);
  return Number.isFinite(n) ? n : null;
}

const GOALS: SimulationGoal[] = ['extend_runway', 'accelerate_growth', 'balance'];

function asGoal(raw: string | null): SimulationGoal {
  if (raw && (GOALS as string[]).includes(raw)) return raw as SimulationGoal;
  return 'extend_runway';
}

export function parseSimulatePrefill(search: string): ScenarioPrefill | null {
  const raw = search.startsWith('?') ? search.slice(1) : search;
  const params = new URLSearchParams(raw);
  if (params.get('from') !== TRUTH_SCAN_SIM_SOURCE) return null;

  const actionId = params.get('action') || 'action-unknown';
  const actionType = (params.get('action_type') || 'runway') as SuggestedActionType;
  const name = params.get('name') || 'Truth Scan Scenario';

  return {
    from: TRUTH_SCAN_SIM_SOURCE,
    actionId,
    actionType,
    name,
    goal: asGoal(params.get('goal')),
    strategyId: params.get('strategy') || 'extend_conservative',
    templateId: params.get('scenario') || 'baseline',
    params: {
      pricing_change_pct: parseNumber(params.get('pricing_change_pct')),
      growth_uplift_pct: parseNumber(params.get('growth_uplift_pct')),
      burn_reduction_pct: parseNumber(params.get('burn_reduction_pct')),
      gross_margin_delta_pct: parseNumber(params.get('gross_margin_delta_pct')),
      churn_change_pct: parseNumber(params.get('churn_change_pct')),
      cac_change_pct: parseNumber(params.get('cac_change_pct')),
      fundraise_month: parseOptionalInt(params.get('fundraise_month')),
      fundraise_amount: parseNumber(params.get('fundraise_amount')),
    },
  };
}

export function attributionFromPrefill(prefill: ScenarioPrefill): SimulationAttribution {
  return {
    source: TRUTH_SCAN_SIM_SOURCE,
    from: TRUTH_SCAN_SIM_FROM,
    action_id: prefill.actionId,
    action_type: prefill.actionType,
  };
}

export function rememberSimulationAttribution(attr: SimulationAttribution): void {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(SIM_ATTRIBUTION_KEY, JSON.stringify(attr));
  } catch {
    // private mode / blocked storage
  }
}

export function peekSimulationAttribution(): SimulationAttribution | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(SIM_ATTRIBUTION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as SimulationAttribution;
    if (parsed?.source !== TRUTH_SCAN_SIM_SOURCE) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function consumeSimulationAttribution(): SimulationAttribution | null {
  const attr = peekSimulationAttribution();
  if (typeof window === 'undefined') return attr;
  try {
    window.sessionStorage.removeItem(SIM_ATTRIBUTION_KEY);
  } catch {
    // ignore
  }
  return attr;
}

export function clearSimulationAttribution(): void {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.removeItem(SIM_ATTRIBUTION_KEY);
  } catch {
    // ignore
  }
}
