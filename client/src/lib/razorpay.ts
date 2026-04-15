/**
 * Razorpay Checkout integration utilities for FounderConsole.
 * Handles dynamic script loading, checkout modal, and TypeScript types.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface RazorpayOptions {
  key: string;
  amount: number;
  currency: string;
  name: string;
  description: string;
  order_id: string;
  handler: (response: RazorpayResponse) => void;
  prefill?: {
    name?: string;
    email?: string;
    contact?: string;
  };
  notes?: Record<string, string>;
  theme?: {
    color?: string;
    backdrop_color?: string;
  };
  modal?: {
    ondismiss?: () => void;
    escape?: boolean;
    confirm_close?: boolean;
  };
}

export interface RazorpayResponse {
  razorpay_payment_id: string;
  razorpay_order_id: string;
  razorpay_signature: string;
}

export interface RazorpayInstance {
  open: () => void;
  close: () => void;
  on: (event: string, handler: (...args: any[]) => void) => void;
}

// Augment the global Window interface
declare global {
  interface Window {
    Razorpay: new (options: RazorpayOptions) => RazorpayInstance;
  }
}

// ---------------------------------------------------------------------------
// Script loader (singleton)
// ---------------------------------------------------------------------------

const RAZORPAY_SCRIPT_URL = "https://checkout.razorpay.com/v1/checkout.js";

let scriptPromise: Promise<void> | null = null;

export function loadRazorpayScript(): Promise<void> {
  if (scriptPromise) return scriptPromise;

  // If already loaded (e.g. via a <script> tag), resolve immediately
  if (typeof window !== "undefined" && window.Razorpay) {
    scriptPromise = Promise.resolve();
    return scriptPromise;
  }

  scriptPromise = new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = RAZORPAY_SCRIPT_URL;
    script.async = true;

    script.onload = () => resolve();
    script.onerror = () => {
      scriptPromise = null; // allow retry
      reject(new Error("Failed to load Razorpay checkout script"));
    };

    document.head.appendChild(script);
  });

  return scriptPromise;
}

// ---------------------------------------------------------------------------
// Checkout helper
// ---------------------------------------------------------------------------

export async function openRazorpayCheckout(
  options: RazorpayOptions,
): Promise<void> {
  await loadRazorpayScript();

  if (!window.Razorpay) {
    throw new Error("Razorpay SDK failed to initialize");
  }

  const rzp = new window.Razorpay(options);
  rzp.open();
}
