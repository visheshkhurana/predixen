/**
 * In-order buffer for PostHog calls that arrive before posthog-js has
 * initialized. Kept in its own module so the flush contract can be unit-tested
 * without importing posthog-js or depending on import.meta.env.
 *
 * Not a public API — call sites go through client/src/lib/posthog.ts.
 */

export type PostHogClient = {
  identify: (distinctId: string, traits?: Record<string, unknown>) => void;
  reset: () => void;
  capture: (event: string, properties?: Record<string, unknown>) => void;
};

export type QueuedPostHogCall =
  | { kind: "identify"; distinctId: string; traits: Record<string, unknown> }
  | { kind: "reset" }
  | { kind: "capture"; event: string; properties?: Record<string, unknown> };

export function flushPostHogQueue(
  client: PostHogClient,
  queue: QueuedPostHogCall[],
): void {
  const calls = queue.splice(0, queue.length);
  for (const call of calls) {
    if (call.kind === "identify") {
      client.identify(call.distinctId, call.traits);
    } else if (call.kind === "reset") {
      client.reset();
    } else {
      client.capture(call.event, call.properties);
    }
  }
}
