/**
 * A Free (or Starter) founder who runs out of simulations or Copilot messages
 * gets 402 plan_limit_reached from the API (server/core/plan_usage.py). That is
 * the moment they most want more, so instead of a generic error toast the app
 * opens an upgrade dialog. Both request helpers (api/client.ts request() and
 * lib/queryClient.ts apiRequest) call announcePlanLimit on error.
 */

export const PLAN_LIMIT_EVENT = 'fc:plan-limit';

export interface PlanLimitInfo {
  limit: string;
  used: number | null;
  max: number | null;
  currentPlan: string | null;
  message: string;
}

const FALLBACK_MESSAGE =
  "You've used this month's allowance on your plan. Upgrade for more, or wait for the month to reset.";

export function planLimitFromError(status: number, detail: unknown): PlanLimitInfo | null {
  if (status !== 402 || !detail || typeof detail !== 'object') return null;
  const d = detail as Record<string, unknown>;
  if (d.error !== 'plan_limit_reached') return null;
  const num = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) ? v : null);
  return {
    limit: typeof d.limit === 'string' ? d.limit : 'unknown',
    used: num(d.used),
    max: num(d.max),
    currentPlan: typeof d.current_plan === 'string' ? d.current_plan : null,
    message: typeof d.message === 'string' && d.message.trim() ? d.message : FALLBACK_MESSAGE,
  };
}

/** Plain-language name of the allowance, for the dialog title. */
export function planLimitNoun(limit: string): string {
  if (limit === 'max_simulations_per_month') return 'simulations';
  if (limit === 'max_copilot_messages_per_month') return 'Copilot messages';
  if (limit === 'max_connectors') return 'data connectors';
  return 'uses';
}

/** Dialog title. Connectors are a plan size, not a monthly allowance. */
export function planLimitTitle(limit: string): string {
  if (limit === 'max_connectors') return "You've reached your plan's data connectors";
  return `You've used this month's ${planLimitNoun(limit)}`;
}

export function announcePlanLimit(status: number, detail: unknown): void {
  const info = planLimitFromError(status, detail);
  if (!info || typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent<PlanLimitInfo>(PLAN_LIMIT_EVENT, { detail: info }));
}
