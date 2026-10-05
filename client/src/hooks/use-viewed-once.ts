import { useRef, type RefCallback } from "react";
import { trackEvent } from "@/lib/posthog";
import { createViewedOnceController, VIEWED_ONCE_THRESHOLD } from "./viewed-once";

/**
 * Fire `event` through PostHog `trackEvent` once, the first time the
 * attached element is about half on screen.
 *
 * PostHog only. The funnel helper also sends GA4 and X Ads conversions, and
 * a form impression is not a conversion. Once per mount, so scrolling away and
 * back does not book a second view. If the element mounts later (the
 * survival form only exists after a simulation), the callback ref
 * observes it then. React calls the ref with null on unmount, which
 * disconnects an observer that has not fired yet.
 */
export function useViewedOnce<T extends Element = HTMLFormElement>(
  event: string,
  properties?: Record<string, any>,
  threshold = VIEWED_ONCE_THRESHOLD,
): RefCallback<T> {
  const propsRef = useRef(properties);
  propsRef.current = properties;

  const controllerRef = useRef<ReturnType<typeof createViewedOnceController> | null>(null);
  if (controllerRef.current === null) {
    controllerRef.current = createViewedOnceController({
      event,
      threshold,
      getProperties: () => propsRef.current,
      emit: trackEvent,
    });
  }

  return controllerRef.current.ref as RefCallback<T>;
}
