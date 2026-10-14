/**
 * The property bag for the `purchase_subscription` event.
 *
 * Its own module, with no imports, for one reason: the purchase conversion is the only
 * event this product is directly paid for, and the thing that was wrong with it — no
 * value, no currency — was wrong inside a React effect where nothing could test it.
 * Here it is a pure function over four nullable inputs, so the case that matters (the
 * server has not answered yet) is a unit test rather than a hope.
 *
 * Why `value` and `currency` are not optional: GA4 will not treat an event as a revenue
 * key event without both, and an ad platform cannot value a conversion it cannot price.
 * The event fired for months with neither, so no spend could be turned into a cost per
 * purchase and no bid strategy could optimise toward one.
 */

export interface PurchasePropertiesInput {
  /** The plan the visitor picked, read back from the checkout round trip. */
  planId?: string | null;
  /** A local correlation id for one checkout attempt. NOT a Stripe session id. */
  checkoutId?: string | null;
  /** `plan_price` from the subscription the server reports. The authoritative number. */
  subscriptionPrice?: number | null;
  /** `price_monthly` from the plan catalogue. Used only if the server has not answered. */
  cataloguePrice?: number | null;
}

export type ValueSource = 'subscription' | 'catalogue' | 'unavailable';

export interface PurchaseProperties {
  method: 'stripe_checkout';
  plan: string;
  value: number;
  currency: string;
  value_source: ValueSource;
  transaction_id: string;
}

/** `true` only for a usable number — rejects null, undefined, NaN and non-numbers. */
function isPrice(v: unknown): v is number {
  return typeof v === 'number' && Number.isFinite(v);
}

export function buildPurchaseProperties(input: PurchasePropertiesInput): PurchaseProperties {
  const fromSubscription = isPrice(input.subscriptionPrice) ? input.subscriptionPrice : null;
  const fromCatalogue = isPrice(input.cataloguePrice) ? input.cataloguePrice : null;

  return {
    method: 'stripe_checkout',
    plan: input.planId ?? 'unknown',
    // A stated zero when neither source has a price beats both alternatives: an absent
    // `value` (which GA4 drops from revenue) and a guessed one (which is a fabricated
    // number in a revenue report). `value_source` says which case this is.
    value: fromSubscription ?? fromCatalogue ?? 0,
    currency: 'USD',
    value_source:
      fromSubscription != null ? 'subscription' : fromCatalogue != null ? 'catalogue' : 'unavailable',
    transaction_id: input.checkoutId ?? '',
  };
}

/**
 * Whether the purchase event may fire yet. It must not fire before a price is known, and
 * it must not wait forever if neither query ever produces one.
 */
export function isPurchaseResolvable(input: PurchasePropertiesInput, queriesSettled: boolean): boolean {
  if (isPrice(input.subscriptionPrice) || isPrice(input.cataloguePrice)) return true;
  return queriesSettled;
}
