export type ActionParams = Record<string, unknown>;

export type ActionResult =
  | { ok: true; [key: string]: unknown }
  | { ok: false; error: string; [key: string]: unknown };

export type ActionHandler = (params: ActionParams) => Promise<ActionResult>;

function getString(params: ActionParams, key: string): string | undefined {
  const value = params[key];
  return typeof value === "string" ? value : undefined;
}

function getNumber(params: ActionParams, key: string): number | undefined {
  const value = params[key];
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return undefined;
}

export const ACTIONS: Record<string, ActionHandler> = {
  ping: async () => ({
    ok: true,
    pong: new Date().toISOString(),
    workspace: "founderconsole",
  }),

  snapshot: async () => ({
    ok: true,
    data: {
      signups_today: 0,
      visitors_today: 0,
      conversion_pct: 0,
      pages_live: 0,
    },
  }),

  list_pages: async () => ({ ok: true, data: [] }),

  list_recent_visitors: async (params) => {
    const rawHours = getNumber(params, "hours") ?? 24;
    const hours = Math.min(rawHours, 168);
    void hours;
    return { ok: true, data: [] };
  },

  get_funnel: async (params) => {
    const pageSlug = getString(params, "page_slug");
    if (!pageSlug) {
      return { ok: false, error: "page_slug required" };
    }
    return { ok: true, data: {} };
  },

  publish_page: async (params) => ({
    ok: true,
    published: getString(params, "page_id") ?? params.page_id ?? null,
  }),

  retire_page: async (params) => ({
    ok: true,
    retired: getString(params, "page_id") ?? params.page_id ?? null,
  }),

  set_page_meta: async (params) => ({
    ok: true,
    page_id: getString(params, "page_id") ?? params.page_id ?? null,
  }),
};

export function getActionNames(): string[] {
  return Object.keys(ACTIONS).sort();
}
