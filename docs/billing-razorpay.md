# Razorpay billing

FounderConsole is free during beta. Razorpay billing ships switched off and
stays off until every variable below is set. With none set, the product
behaves as before (Stripe path, which is also off without `STRIPE_SECRET_KEY`)
and the billing page shows "Free during beta".

## Prices (final, owner decision 2026-11-12)

| Region | Currency | Monthly | Annual (2 months free) |
|---|---|---|---|
| Company currency INR | INR | ₹3,000 | ₹30,000 |
| Company currency AED | AED | AED 149 | AED 1,490 |
| Anything else (incl. USD) | USD | $39 | $390 |

- Only the Starter tier is sold through Razorpay. Growth and Scale stay in
  config (USD, Stripe) and are hidden from the plan list when Razorpay is the
  provider.
- Annual = monthly × 10 ("2 months free"). The rule lives in
  `server/core/plans.py` (`ANNUAL_MULTIPLIER`). Annual amounts are derived, so
  editing a monthly price in `REGIONAL_MONTHLY_PRICES` updates the annual price.
- The server picks the currency, price and Razorpay plan id. The client sends
  only tier + interval.

### Which currency a user is charged in

Only the user's latest company currency setting decides it: INR → INR,
AED → AED, anything else (or no company) → USD. A currency sent by the client
and geo headers such as `cf-ipcountry` are ignored for the charge, because
either would let a buyer pick the cheaper currency. Signed-out visitors may
pass `?currency=` to `/api/billing/plans` to preview a price; it never reaches
checkout.

Existing companies still on the default `USD` currency are quoted $39 until
they change their currency in settings.

## Environment variables

All of these are required to turn Razorpay on:

| Variable | Value |
|---|---|
| `BILLING_PROVIDER` | `razorpay` (anything else keeps Stripe) |
| `RAZORPAY_KEY_ID` | Dashboard → Account & Settings → API Keys (`rzp_test_…` / `rzp_live_…`) |
| `RAZORPAY_KEY_SECRET` | Shown once when the key is generated |
| `RAZORPAY_WEBHOOK_SECRET` | The secret you type when creating the webhook |

One plan id per (tier, interval, currency). A missing one makes checkout for
that combination return 503:

```
RAZORPAY_PLAN_STARTER_MONTHLY_INR   # ₹3,000 / 1 month
RAZORPAY_PLAN_STARTER_ANNUAL_INR    # ₹30,000 / 1 year
RAZORPAY_PLAN_STARTER_MONTHLY_USD   # $39 / 1 month
RAZORPAY_PLAN_STARTER_ANNUAL_USD    # $390 / 1 year
RAZORPAY_PLAN_STARTER_MONTHLY_AED   # AED 149 / 1 month
RAZORPAY_PLAN_STARTER_ANNUAL_AED    # AED 1,490 / 1 year
```

The plan's amount in the Razorpay dashboard is what customers are charged.
Keep it equal to the table above, or the page and the charge will disagree.

## Razorpay dashboard setup

1. **Subscriptions**: enable Subscriptions on the account (Products → Subscriptions).
2. **International payments**: USD and AED plans only work once international
   payments are enabled on the account (Account & Settings → International
   payments; Razorpay reviews the request). Until then, create the INR plans only.
3. **Plans**: Subscriptions → Plans → Create plan, six times, matching the table
   above (billing frequency 1 month or 1 year, currency INR/USD/AED). Copy each
   `plan_…` id into its env var.
4. **Webhook**: Account & Settings → Webhooks → Add new webhook.
   - URL: `https://founderconsole.ai/api/billing/razorpay/webhook`
     (Express proxies `/api/*` to FastAPI as `/billing/razorpay/webhook`)
   - Secret: a long random string, also set as `RAZORPAY_WEBHOOK_SECRET`
   - Events: `subscription.activated`, `subscription.charged`,
     `subscription.halted`, `subscription.pending`, `subscription.cancelled`,
     `subscription.completed`, `payment.failed`
5. Set the env vars on the server and redeploy. The CSP for
   `checkout.razorpay.com` / `api.razorpay.com` is added only when Razorpay is
   enabled, and `checkout.js` is loaded only when a user starts checkout.

## How it works

- `POST /api/billing/subscribe/starter` `{interval, currency?}` creates a
  Razorpay customer (reused by email) and subscription, stores the mapping in
  `razorpay_subscriptions`, and returns `{subscription_id, key_id}` for Checkout.
- After payment the client posts the Checkout handler response to
  `POST /api/billing/razorpay/verify`. The server checks
  `HMAC_SHA256(payment_id + "|" + subscription_id, key_secret)` in constant time
  against the subscription it created for that user, then re-fetches the
  subscription from Razorpay and grants access only if it is `active`.
- The webhook verifies `X-Razorpay-Signature` (HMAC-SHA256 of the raw body with
  the webhook secret, constant-time compare). It refuses everything when the
  secret is unset. Each `X-Razorpay-Event-Id` is stored in
  `razorpay_webhook_events`, so redeliveries are acknowledged and skipped.
  Older events than the last one applied are ignored.
- Status mapping: active → `active`; pending/halted → `past_due`;
  cancelled/completed/expired → `canceled`; created/authenticated → no change.
  `payment.failed` marks `past_due` only for an already-active subscription.
- The tier comes from the plan id Razorpay charges, never from the client.
- `POST /api/billing/cancel` cancels at the end of the current cycle.
- Both tables are created at boot with `checkfirst=True`.
- `subscriptions.monthly_price` (summed as USD MRR in admin) is written only for
  USD subscriptions. INR/AED amounts are kept in `razorpay_subscriptions`.

## Test mode

1. Generate **test** API keys and create the plans in test mode (test plan ids
   differ from live ones).
2. Set the env vars with the test values on a staging or local server. For a
   local webhook, expose the server with a tunnel (e.g. `cloudflared` or
   `ngrok`) and point a test-mode webhook at
   `https://<tunnel>/api/billing/razorpay/webhook`.
3. Open `/billing`, choose Starter, and pay with a Razorpay test card or the
   test UPI id `success@razorpay` (failure: `failure@razorpay`).
4. Check that the plan shows as active, that `razorpay_webhook_events` has rows,
   and that a webhook resent from the dashboard is reported as a duplicate.
5. Cancel from the billing page and confirm the subscription shows
   "cancel at cycle end" in the Razorpay dashboard.
6. Automated tests: `python -m pytest server/tests/test_razorpay_billing.py`
   (all Razorpay calls are mocked).
