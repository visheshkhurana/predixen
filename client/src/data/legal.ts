/**
 * The legal facts every public legal surface names: who operates FounderConsole,
 * where it is registered, who handles grievances, and the refund terms.
 *
 * One file, read by the React pages (terms, privacy, contact, refund policy,
 * marketing footer) AND by server/seo-prerender.ts (the HTML a crawler or a
 * payment-gateway reviewer gets before JavaScript runs). Same rule as
 * ai-citation.ts and runway-industries.ts: no second copy, so the two
 * renderings cannot disagree.
 *
 * ---------------------------------------------------------------------------
 * OWNER: FILL THESE IN.
 *
 * Any value that still starts with "TODO" is treated as unset and is NOT
 * rendered anywhere (see `legalValue`). So a placeholder can never reach a
 * page as a fake address or a fake name; the page simply leaves that line out
 * until the real value is committed here.
 *
 *   LEGAL_ENTITY_ADDRESS     registered office address of the company
 *   GRIEVANCE_OFFICER_NAME   Grievance Officer (IT Rules 2021, rule 3(2))
 *   GRIEVANCE_OFFICER_EMAIL  Grievance Officer contact email
 *
 * Until the Grievance Officer email is set, grievances are routed to
 * SUPPORT_EMAIL so the channel always exists.
 * ---------------------------------------------------------------------------
 */

export const LEGAL_ENTITY_NAME = "ULTRASAFE AI INDIA PRIVATE LIMITED";
export const PRODUCT_NAME = "FounderConsole";
export const PRODUCT_OF_LINE = `${PRODUCT_NAME} is a product of ${LEGAL_ENTITY_NAME}.`;

/** OWNER: registered office address. Left as TODO = not rendered. */
export const LEGAL_ENTITY_ADDRESS = "TODO: registered office address";

/** OWNER: Grievance Officer name. Left as TODO = not rendered. */
export const GRIEVANCE_OFFICER_NAME = "TODO: grievance officer name";

/** OWNER: Grievance Officer email. Left as TODO = SUPPORT_EMAIL is shown instead. */
export const GRIEVANCE_OFFICER_EMAIL = "TODO: grievance officer email";

/** The support address already published on /contact, /privacy and /terms. */
export const SUPPORT_EMAIL = "hello@founderconsole.ai";

/**
 * OWNER DECISION: the refund window after the FIRST payment of a new
 * subscription, in days. A customer who asks within this many days of their
 * first charge gets a full refund. Renewals and partial periods are otherwise
 * non-refundable (duplicate or erroneous charges are always refunded).
 * Change this number and /refund-policy, /terms and the prerendered HTML all
 * follow.
 */
export const FIRST_PAYMENT_REFUND_WINDOW_DAYS = 7;

/** Razorpay's refund timeline to the original payment method, once approved. */
export const REFUND_PROCESSING_TIME = "5–7 business days";

export const LEGAL_PLACEHOLDER_PREFIX = "TODO";

/**
 * The value, or null when it is still the placeholder (or empty). Every
 * renderer goes through this, which is what keeps a "TODO: ..." string off
 * every page.
 */
export function legalValue(value: string): string | null {
  const v = (value || "").trim();
  if (!v || v.toUpperCase().startsWith(LEGAL_PLACEHOLDER_PREFIX)) return null;
  return v;
}

/** Registered address if filled in, else null. */
export function registeredAddress(): string | null {
  return legalValue(LEGAL_ENTITY_ADDRESS);
}

/** Grievance Officer as displayable parts; email falls back to support. */
export function grievanceOfficer(): { name: string | null; email: string } {
  return {
    name: legalValue(GRIEVANCE_OFFICER_NAME),
    email: legalValue(GRIEVANCE_OFFICER_EMAIL) ?? SUPPORT_EMAIL,
  };
}
