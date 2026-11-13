/**
 * The browser-side "already emitted" guard for `founder_activated`.
 *
 * The server decides "first activation" per user (`has_prior_real_activation`),
 * and the browser keeps its own flag so a page reload does not re-fire the
 * client copy. That flag used to be one browser-wide `fc_founder_activated`,
 * which on a shared browser silenced every account after the first — a MISSING
 * event, not a duplicate, and one the `count()/uniqExact(user_id)` control
 * cannot see, because a dropped event shrinks both numbers and the ratio still
 * reads 1.0.
 *
 * So the flag key carries the user id. Nothing imports this module on purpose,
 * so a test can load it under plain node without the PostHog client or
 * `import.meta.env` (same reason as ./analytics-keys.ts).
 *
 * The legacy browser-wide key is deliberately NOT honoured. It cannot say whose
 * activation it recorded, so reading it would restore exactly the defect this
 * module removes: a second account on that browser would stay silent. Ignoring
 * it costs at most one extra event per existing browser, once, at that account's
 * next activation — an inflation you can see and bound, where the bug was an
 * undercount you could not.
 */

const PREFIX = "fc_founder_activated";

/** Storage surface we need; `window.localStorage` satisfies it. */
export interface FlagStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

/**
 * `window.localStorage`, or null where it is absent (SSR, plain node) or where
 * merely reading it throws (private mode, blocked cookies). The caller treats
 * null as "emit, remember nothing".
 */
export function browserFlagStore(): FlagStore | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

/** The per-user flag key. Literal shape is asserted by a test. */
export function founderActivatedFlagKey(userId: number | string): string {
  return `${PREFIX}:${userId}`;
}

/**
 * True when this user has not fired the client event on this browser yet.
 * A missing or blocked store (private mode, Node, SSR) emits: better a
 * duplicate than a silently lost activation, and the server copy is keyed
 * independently.
 */
export function shouldEmitFounderActivated(
  store: FlagStore | null | undefined,
  userId: number | string,
): boolean {
  if (!store) return true;
  try {
    return !store.getItem(founderActivatedFlagKey(userId));
  } catch {
    return true;
  }
}

/** Record the emission for this user. A blocked store is not an error. */
export function rememberFounderActivated(
  store: FlagStore | null | undefined,
  userId: number | string,
): void {
  if (!store) return;
  try {
    store.setItem(founderActivatedFlagKey(userId), "1");
  } catch {
    // Private mode / blocked storage: this session still emits.
  }
}
