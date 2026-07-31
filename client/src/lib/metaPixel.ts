/**
 * Meta (Facebook) Pixel — privacy-scoped loader.
 *
 * Loads ONLY when VITE_META_PIXEL_ID is set, and only fires on public
 * marketing surfaces + the subscription checkout confirmation, per our
 * Privacy Policy. Never active inside the core app.
 */

const PIXEL_ID = import.meta.env.VITE_META_PIXEL_ID || '';

let loaded = false;

function ensureLoaded(): boolean {
  if (!PIXEL_ID) return false;
  if (loaded) return true;
  /* eslint-disable */
  (function (f: any, b: any, e: any, v: any, n?: any, t?: any, s?: any) {
    if (f.fbq) return;
    n = f.fbq = function () {
      n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments);
    };
    if (!f._fbq) f._fbq = n;
    n.push = n; n.loaded = true; n.version = '2.0'; n.queue = [];
    t = b.createElement(e); t.async = true; t.src = v;
    s = b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t, s);
  })(window, document, 'script', 'https://connect.facebook.net/en_US/fbevents.js');
  /* eslint-enable */
  (window as any).fbq('init', PIXEL_ID);
  loaded = true;
  return true;
}

/** PageView on public marketing pages (call from MarketingLayout / auth). */
export function metaPageView() {
  if (!ensureLoaded()) return;
  (window as any).fbq('track', 'PageView');
}

/** Standard or custom event (CompleteRegistration, Subscribe, ...). */
export function metaTrack(event: string, params?: Record<string, any>) {
  if (!ensureLoaded()) return;
  (window as any).fbq('track', event, params || {});
}

export const isMetaPixelEnabled = () => !!PIXEL_ID;
