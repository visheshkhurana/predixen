/**
 * Meta (Facebook) Pixel events.
 *
 * The pixel script is not injected here. client/src/lib/consentTracking.ts
 * is the only loader, and it injects the pixel only on marketing pages after
 * cookie-consent === "accepted". Calling these helpers from the core app
 * (billing, and any route outside MarketingLayout) must not fetch the script.
 */

function pixelReady(): boolean {
  if (typeof window === "undefined") return false;
  const w = window as unknown as {
    __fcConsentMetaPixel?: boolean;
    fbq?: (...args: unknown[]) => void;
  };
  return w.__fcConsentMetaPixel === true && typeof w.fbq === "function";
}

/** PageView on public marketing pages (call from MarketingLayout). */
export function metaPageView() {
  if (!pixelReady()) return;
  (window as unknown as { fbq: (...args: unknown[]) => void }).fbq("track", "PageView");
}

/** Standard or custom event (CompleteRegistration, Subscribe, ...). */
export function metaTrack(event: string, params?: Record<string, unknown>) {
  if (!pixelReady()) return;
  (window as unknown as { fbq: (...args: unknown[]) => void }).fbq(
    "track",
    event,
    params || {},
  );
}

/** True only after the consent loader has actually installed the pixel. */
export const isMetaPixelEnabled = () => pixelReady();
