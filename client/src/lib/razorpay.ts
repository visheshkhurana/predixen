// Razorpay Checkout loader. The script is injected only when the billing
// provider is Razorpay and the user starts a checkout, so nothing loads (and
// the CSP stays narrow) while payments are off or Stripe is the provider.

export const RAZORPAY_CHECKOUT_SRC = 'https://checkout.razorpay.com/v1/checkout.js';

export interface RazorpayCheckoutOptions {
  key: string;
  subscription_id: string;
  name: string;
  description?: string;
  prefill?: { email?: string; name?: string };
  theme?: { color?: string };
  handler: (resp: {
    razorpay_payment_id: string;
    razorpay_subscription_id: string;
    razorpay_signature: string;
  }) => void;
  modal?: { ondismiss?: () => void };
}

interface RazorpayInstance {
  open: () => void;
  on: (event: string, cb: (resp: unknown) => void) => void;
}

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayCheckoutOptions) => RazorpayInstance;
  }
}

let loading: Promise<void> | null = null;

export function loadRazorpayCheckout(): Promise<void> {
  if (typeof window === 'undefined') return Promise.reject(new Error('No window'));
  if (window.Razorpay) return Promise.resolve();
  if (loading) return loading;
  loading = new Promise<void>((resolve, reject) => {
    const script = document.createElement('script');
    script.src = RAZORPAY_CHECKOUT_SRC;
    script.async = true;
    script.onload = () => (window.Razorpay ? resolve() : reject(new Error('Razorpay failed to load')));
    script.onerror = () => {
      loading = null;
      script.remove();
      reject(new Error('Could not load Razorpay Checkout'));
    };
    document.head.appendChild(script);
  });
  return loading;
}

export async function openRazorpayCheckout(options: RazorpayCheckoutOptions): Promise<void> {
  await loadRazorpayCheckout();
  if (!window.Razorpay) throw new Error('Razorpay is unavailable');
  const rzp = new window.Razorpay(options);
  rzp.open();
}

/** ₹3,000 / $39 / AED 149. Whole units only; plan prices have no minor part. */
export function formatPlanPrice(amount: number, currency = 'USD'): string {
  const code = (currency || 'USD').toUpperCase();
  try {
    return new Intl.NumberFormat(code === 'INR' ? 'en-IN' : 'en-US', {
      style: 'currency',
      currency: code,
      maximumFractionDigits: 0,
      minimumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `${code} ${amount}`;
  }
}
