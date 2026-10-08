// Once-per-attachment visibility. The React hook in use-viewed-once.ts is a
// thin wrapper so this can be exercised without a DOM or the PostHog client.

export type ViewedOnceEmit = (event: string, properties?: Record<string, any>) => void;

export const VIEWED_ONCE_THRESHOLD = 0.5;

/**
 * Call `onView` the first time `element` is at least `threshold` visible,
 * then disconnect. A later callback — including one already queued — does
 * not call `onView` again. Missing IntersectionObserver is a no-op.
 */
export function observeViewedOnce(
  element: Element,
  onView: () => void,
  threshold = VIEWED_ONCE_THRESHOLD,
): () => void {
  if (typeof IntersectionObserver === "undefined") return () => {};

  let fired = false;
  let active = true;
  const observer = new IntersectionObserver(
    (entries) => {
      if (!active || fired) return;
      const visible = entries.some(
        (entry) => entry.isIntersecting && entry.intersectionRatio >= threshold,
      );
      if (!visible) return;
      fired = true;
      active = false;
      observer.disconnect();
      onView();
    },
    { threshold },
  );
  observer.observe(element);
  return () => {
    active = false;
    observer.disconnect();
  };
}

/**
 * The once-guard `useViewedOnce` installs for a single mount.
 * Re-attaching the same ref after a fire, or delivering another
 * intersection on the old observer, does not emit again.
 */
export function createViewedOnceController(options: {
  event: string;
  getProperties: () => Record<string, any> | undefined;
  emit: ViewedOnceEmit;
  threshold?: number;
}) {
  const threshold = options.threshold ?? VIEWED_ONCE_THRESHOLD;
  let fired = false;
  let stop: (() => void) | null = null;

  return {
    ref(node: Element | null) {
      stop?.();
      stop = null;
      if (!node || fired) return;
      stop = observeViewedOnce(
        node,
        () => {
          if (fired) return;
          fired = true;
          options.emit(options.event, options.getProperties());
        },
        threshold,
      );
    },
    disconnect() {
      stop?.();
      stop = null;
    },
  };
}
