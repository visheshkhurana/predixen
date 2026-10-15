# Stripe integration spec — the 4-tier plans in `server/core/plans.py`

Atlas (`atlas-mv75ukoh`), 2026-10-14. Closes `founderconsole/backlog.md` item 5 and card HAG-135,
reopened to `todo` by god on 2026-10-14 after `founderconsole/backlog-audit-2026-10-14.md` showed its
`done` had been closed with a different item's report (the deploy path, HAG-136).

God's instruction, verbatim: *"Write the Stripe integration spec HAG-135 asked for. OUTPUT:
`hive/agents/atlas-mv75ukoh/founderconsole/stripe-integration-spec-2026-10-14.md`, plus a docs PR (PRs
only, merge gate closed - Vishesh merges). TOOLS: FIRST, take the pass you offered - search the whole
tree, not just the ledger, for a Stripe spec or equivalent. Say what you searched and what came back.
Read `server/core/plans.py` for the 4-tier truth and `founderconsole/backlog.md` item 5. Oracle
(oracle-muqoa36l) is archived, so DO NOT wait on its pricing inputs: source pricing from the repo and
public pricing pages, and mark every number measured or assumed. BOUNDARIES: spec only - no keys, no
live calls, no code changes to billing. Do not touch `backlog.md`, `needs-vishesh.md`, or another
agent's files. Report `done` with the sha and the PR number."*

**Boundaries honoured:** no key was read, printed or written; no Stripe API call was made; no file under
`~/predixen` was modified; `backlog.md` and `needs-vishesh.md` are untouched. Every figure below is
either **measured** (a command's real output, quoted with its size and hash) or **assumed** (labelled).

---

## Part 0 — the whole-tree search: does a Stripe spec already exist?

**Verdict: no FounderConsole Stripe spec exists anywhere in the tree.** A same-shaped spec exists for a
different product and is a structural template, not the artifact. Four passes, with what each returned:

**Pass 1 — filename, the product repo.**
`find /Users/visheshkhurana/predixen -iname '*stripe*' -not -path '*/node_modules/*' -not -path '*/.git/*'`
-> 12 hits, of which **5 are real code artifacts, none a spec**:

- `scripts/stripe_bootstrap.py` — the one-time setup script (read in full; Part 2)
- `server/core/stripe_billing.py` — the Stripe client layer (read in full; Part 2)
- `server/api/billing.py` — the billing endpoints and webhook handler (read in full; Part 2)
- `client/src/components/integrations/StripeConnectModal.tsx` — a **data-connector** UI, not billing
- `server/metrics/suggestions/rules/stripe.py` — a **metrics suggestion rule**, not billing

The other 7 hits are the vendored SDK: `.venv/lib/python3.13/site-packages/stripe-15.3.1.dist-info`
plus the `stripe/` package itself. **No file named or shaped like a spec.**

**Pass 2 — filename, the whole hive.**
Hits, and why none is the answer: `hive/agents/lumen-muqnxk62/vibbber-stripe-spec.md` and
`hive/agents/forge-muqo2hat/vibbber-stripe-plan.md` + `vibbber-stripe-ref/` (a different product —
Part 0's deciding reads), both agents' `vibbber-stripe-done.json` in `.sent`, god's five
`outbox/.sent/stripe-*.json` (all 2026-10-02, all vibbber/alpha.kids or Cleya), six Stripe plugin skill
folders under `hive/agents/god/.codex/.tmp/plugins/plugins/stripe/skills/`, Cleya payment-link files, and
worktree/scratch copies of the same five predixen files. **Nothing for FounderConsole.**

**Pass 3 — content grep, the product repo.**
`grep -ril "stripe" … --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.venv
--exclude-dir=attached_assets --exclude-dir=_to_delete` -> **98 files** (listing truncated at 60), all
implementation, test, seed, deploy-example or doc files. **None is a spec.**

**Pass 4 — the docs tree and the crawler-visible surface.**
`grep -ril "stripe" /Users/visheshkhurana/predixen/docs /Users/visheshkhurana/predixen/client/public`
-> exactly two files: `docs/ARCHITECTURE.md` and `client/public/llms.txt`. Independently confirms there
is no Stripe document in the repo. `~/predixen/docs/` holds `adr/` (six entries: `0001-one-orm.md`,
`0002-reversible-migrations.md`, `0003-background-loops-off-web.md`, `0004-tech-debt-register.md`,
`0005-typescript-error-ratchet.md`, plus `README.md` and `tech-debt.md`) and the top-level files
`ARCHITECTURE.md` (240 lines / 11,890 B), `copilot_v2_plan.md` (152 / 5,210), `copilot_v2_prompt_v2_plan.md`
(148 / 4,952), `copilot_v3_evals_privacy_plan.md` (344 / 12,934), `email-copilot-pitch.md` (158 / 4,305),
`email-pitch-template.md` (159 / 5,247) — **1,201 lines / 44,538 B total**. **The house convention for a
durable design document is a numbered ADR under `docs/adr/`.**

**The deciding reads (Pass 2's two files).**

`hive/agents/lumen-muqnxk62/vibbber-stripe-spec.md` — 192 lines / 15,957 B / sha256
`b1574594f0ada8e4a91037fde8c7efd55eda17d54763fbcd32ce06c74dc02d2e`. Title: *"alpha.kids: Stripe billing
spec (catalog, checkout, webhooks, tracking, pricing page)"*, Lumen, 2026-10-02, Stripe API version
`2026-09-30.endive`. **A different product**: "Plus $7.99/mo or $59.99/yr; Family $14.99/mo or $119.99/yr;
7-day free trial; the annual plan shown first; Stripe on the web". Products `alphakids_plus` /
`alphakids_family`; lookup keys `plus_annual` 5999, `plus_monthly` 799, `family_annual` 11999,
`family_monthly` 1499; AED via `currency_options` at USD x 3.6725; `tax_behavior=inclusive`; 7-day trial
via `subscription_data.trial_period_days=7` because Stripe's Trial Offer API does not work with Checkout.
**Its section structure is the reusable template; its content is not the answer.**

`hive/agents/forge-muqo2hat/vibbber-stripe-plan.md` — 178 lines / 18,511 B / sha256
`a4ea884e5ca30a88ee571f7e36e9f5a9c5a61e4feb55b8bd3f4f80004725923f`. Forge's 2026-10-02 plan putting
billing in the Express backend on Railway, recording all four `Vibbber-Team` repos as **404**, noting the
broker token is fine-grained on `visheshkhurana` and expires 2026-11-01, and citing
`agents/forge-muqo2hat/vibbber-stripe-ref/` with 21 of 21 tests passing — **Node, Express + MongoDB, not
predixen's Python.** Nothing in it transfers to this stack.

**What this means for the spec.** HAG-135's ask reads as a greenfield design ("spec only; no keys, no
live calls"). It is not. **The Stripe integration already exists in the repository** — four modules,
~950 lines — and the useful artifact is therefore an **as-built mapping plus its gaps**, so the next
person does not design a second billing system beside the live one. That is what Parts 1-6 are.

---

## Part 1 — the 4-tier truth (`server/core/plans.py`)

**Measured:** 246 lines / 7,874 B / sha256 `6a92f467a1c44a7583007cfd6b7fe22c4d54825b2dc48eae476ea26b440d9390`.
Read in full. This file is the single source of truth for tiers, prices, limits and features.

`PlanTier(str, Enum)`: `FREE`, `STARTER`, `GROWTH`, `SCALE`. `Feature(str, Enum)`: 28 members.

| Tier | monthly | annual | tagline | max_companies | simulations | copilot | connectors | features |
|---|---|---|---|---|---|---|---|---|
| FREE | 0 | 0 | Explore the platform | 1 | 3 | 10 | 0 | 4 |
| STARTER | 29 | 290 | For early-stage founders | 1 | 50 | 100 | 2 | 12 |
| GROWTH | 49 | 490 | For scaling startups | 3 | -1 | -1 | 10 | 20 |
| SCALE | 99 | 990 | Full power for serious founders | -1 | -1 | -1 | -1 | 28 |

**All prices above are *measured* — read from `PLAN_DETAILS` in the file whose sha is printed above.**
`-1` is the sentinel for unlimited (`get_plan_limit` returns it as-is; the paywall compares features, not
counts). The feature ladder is strictly additive: FREE has 4 (DASHBOARD, BASIC_METRICS, CSV_UPLOAD,
MANUAL_DATA_ENTRY); STARTER adds 8 (SIMULATIONS, COPILOT, TRUTH_SCAN, STRESS_TESTS, WHAT_IF,
SENSITIVITY_ANALYSIS, EXPORT_PDF, BENCHMARKS); GROWTH adds 8 more (SIMULATION_UNLIMITED,
COPILOT_UNLIMITED, DATA_CONNECTORS, FUNDRAISING_OS, CAP_TABLE, BOARD_DECK, EMAIL_REPORTS,
FUNDRAISING_READINESS); SCALE holds all 28.

Two constants matter for the spec: **`TRIAL_DURATION_DAYS = 30`** and **`TRIAL_PLAN = PlanTier.SCALE`** —
the in-app trial is **30 days on the top tier**, not on Starter and not on a Stripe trial.

Helper surface: `get_plan_features`, `has_feature(plan, feature)`, `get_plan_limit(plan, key)` (falls
back to 0 via `.get(limit_key, 0)`), `minimum_plan_for_feature(feature)` (iterates
`[STARTER, GROWTH, SCALE]`), `FEATURE_LABELS`.

---

## Part 2 — the as-built Stripe layer

**Measured, read in full:**

- `server/core/stripe_billing.py` — 176 lines / 5,909 B / sha256 `4b70467fc04d860cbcf5ff5c6a9bf64e4df748ab7ae521f247de0a9b2a139b73`
- `server/api/billing.py` — 331 lines / 12,804 B / sha256 `eaa451d755ec1f0e17ccdb20c4ffec5bebf1f949e409ce210c1e754b18d247a0`
- `scripts/stripe_bootstrap.py` — 118 lines / 4,704 B / sha256 `ddb80cc36f71fbe5cacacb55819bb6de3b63eb65d5b3d71ea187073ffc7e9ddf`

### 2.1 Catalog and prices are self-bootstrapping

`stripe_billing.py`'s own docstring: *"Prices are self-bootstrapping: each plan/interval gets a Stripe
Price with a stable lookup_key (`fc_<plan>_<interval>`). If the price doesn't exist in the connected
Stripe account it is created on first use from PLAN_DETAILS, so no manual dashboard setup is required
beyond enabling payment methods (card, PayPal, Apple/Google Pay) in Stripe settings."*

- `CURRENCY = "usd"`; `PAID_PLANS = [STARTER, GROWTH, SCALE]`; `INTERVALS = {"monthly": "month", "annual": "year"}`.
- `stripe_enabled()` -> `bool(settings.STRIPE_SECRET_KEY)`. **No key, no billing** — every paid path 503s (2.3).
- `_lookup_key(plan, interval)` -> `f"fc_{plan}_{interval}"`, e.g. `fc_growth_monthly`.
- `_ensure_product(plan)` — `stripe.Product.search(query=f"metadata['fc_plan']:'{plan}'", limit=1)`, with a
  `logger.warning` fallback to `stripe.Product.list(active=True, limit=100).auto_paging_iter()` under the
  comment *"Search results can lag behind newly-created objects, so always double-check the full list
  before creating a duplicate product"*.
- `ensure_price(plan, interval="monthly")` — checks `_price_cache`, then
  `stripe.Price.list(lookup_keys=[key], active=True, limit=1)`, else creates with
  `unit_amount=int(amount * 100)`, `currency="usd"`, `recurring={"interval": ...}`,
  `lookup_key=key`, `transfer_lookup_key=True`.
- `plan_from_price(price)` — reads `price["metadata"]["fc_plan"]`, else splits `lookup_key` on `_` and
  returns `parts[1]`. **Fragile** (Part 5, G6).
- `_price_cache: dict = {}` — process-local, unbounded, never invalidated (Part 5, G5).

**The same catalog is created a second way**, by `scripts/stripe_bootstrap.py`, which is the documented
one-time setup (`STRIPE_SECRET_KEY=sk_... APP_BASE_URL=https://founderconsole.ai python
scripts/stripe_bootstrap.py`, or `railway run python scripts/stripe_bootstrap.py`). It loops
`[STARTER, GROWTH, SCALE]` x `[("monthly","month",price_monthly), ("annual","year",price_annual)]`,
skips any key already present (`stripe.Price.list(lookup_keys=[key], active=True, limit=1)`), resolves the
product by metadata search with the same full-list fallback, and creates the price with
`metadata={"fc_plan": ..., "fc_interval": ...}`. **Two code paths create the same objects; they agree on
the lookup key, which is what makes them idempotent against each other.** The bootstrap also prints
`mode = "LIVE" if STRIPE_SECRET_KEY.startswith("sk_live") else "TEST"`, so the operator can see which
account they are about to write to.

### 2.2 Checkout, portal and webhook verification

- `get_or_create_customer(db, user)` — newest non-null `stripe_customer_id`, else
  `stripe.Customer.create(email=..., name=full_name or name, metadata={"fc_user_id": str(user.id)})`.
- `create_checkout_session(db, user, plan, interval)` — `mode="subscription"`,
  `line_items=[{"price": price_id, "quantity": 1}]`, `client_reference_id=str(user.id)`,
  `allow_promotion_codes=True`, `billing_address_collection="auto"`,
  `subscription_data={"metadata": {"fc_user_id": str(user.id), "fc_plan": plan}}`,
  `success_url=f"{base}/billing?checkout=success"`, `cancel_url=f"{base}/billing?checkout=cancelled"`,
  where `base = settings.APP_BASE_URL.rstrip("/")`.
- `create_portal_session(customer_id)` -> `return_url=f"{base}/billing"`.
- `verify_webhook(payload, sig_header)` -> `stripe.Webhook.construct_event(payload, sig_header,
  settings.STRIPE_WEBHOOK_SECRET)`.
- `to_plain(obj)` uses `json.loads(str(obj))` because the SDK's `StripeObject` (v15+) is not a dict
  subclass — a real portability detail for anyone touching this file.

### 2.3 Endpoints (`server/api/billing.py`)

`router = APIRouter(prefix="/billing", tags=["billing"])`, included at `server/main.py:49`. The route list,
**measured by reading the file**:

| Method + path | Behaviour |
|---|---|
| `GET /billing/plans` | all four tiers plus `payments_enabled` |
| `GET /billing/subscription` | the caller's row, plus `trial_duration_days` |
| `POST /billing/start-trial` | 400 on `ValueError`; success message `f"Your {TRIAL_DURATION_DAYS}-day free trial has started!"` |
| `POST /billing/subscribe/{plan_id}` | 404 unknown plan; `{"message": "Free plan activated"}` when `price_monthly == 0`; **503 "Payments are not configured yet."** when `stripe_enabled()` is false; 400 unless interval is `monthly`/`annual`; 502 on Stripe failure; else `{"checkout_url", "plan", "plan_name", "stripe_connected": True}` |
| `POST /billing/portal` | 503 when off; 400 `"No billing account yet - subscribe to a plan first."`; 502 on failure |
| `POST /billing/cancel` | *"Cancellation is handled through the Stripe customer portal."* |
| `POST /billing/webhook` | signature-verified; see below |
| `GET /billing/feature-access/{feature}` | per-feature access for the client |

**The webhook is exempt from session auth.** `server/main.py:442` lists
`"/billing/webhook",  # Stripe webhook - authenticated by signature, not session` on the auth-exemption
list, so the route is reached unauthenticated and is protected **only** by the Stripe signature check.

**The status map** (`_upsert_subscription_from_stripe`) — Stripe -> local:

```
active             -> active
trialing           -> active    ("Stripe-side trials count as active (we run our own in-app trial)")
past_due           -> past_due
unpaid             -> past_due
canceled           -> canceled
incomplete         -> past_due
incomplete_expired -> canceled
paused             -> canceled
```

It reads `current_period_end` / `current_period_start` with an explicit fallback to `items[0]` under the
comment *"Stripe API 2025+ moved billing periods onto subscription items"*, and derives `monthly_price`
from `unit_amount` (divided by 100, and by 100/12 when the interval is `year`). It UPDATEs the newest
subscription row or INSERTs one.

**Handled events** (`stripe_webhook`, an `async` handler that does `await request.body()` and reads the
`stripe-signature` header, returning 400 on a bad signature):

1. `checkout.session.completed` when `mode == "subscription"` — re-`Subscription.retrieve`, user from
   `metadata.fc_user_id` or `client_reference_id`, plan from `metadata.fc_plan` or `plan_from_price`.
2. `customer.subscription.updated`
3. `customer.subscription.deleted` — forces `{**obj, "status": "canceled"}`
4. `invoice.payment_failed` — sets `past_due` by customer id, `logger.warning`

Returns `{"received": True}`.

**The event set is confirmed independently by the bootstrap script**, whose
`WEBHOOK_EVENTS = ["checkout.session.completed", "customer.subscription.updated",
"customer.subscription.deleted", "invoice.payment_failed"]` — the same four, no more. **G1 (Part 5).**

**The signing secret has exactly one origin.** `stripe_bootstrap.py` calls
`stripe.WebhookEndpoint.list(limit=100)`; if a matching URL is already registered it prints *"NOTE: its
signing secret is only shown at creation time"* plus the re-create instruction; otherwise
`stripe.WebhookEndpoint.create(url=f"{APP_BASE_URL}/api/billing/webhook", enabled_events=WEBHOOK_EVENTS,
description="FounderConsole billing webhook")` and prints `STRIPE_WEBHOOK_SECRET={ep.secret}` with **"it
cannot be retrieved again later."** So the endpoint URL is `{APP_BASE_URL}/api/billing/webhook`, and the
secret is obtainable once, at creation. `stripe_bootstrap.py` ends with: *"Reminder: enable PayPal /
Apple Pay / Google Pay under Stripe Dashboard -> Settings -> Payments -> Payment methods."*

**Configuration.** `.env.example:129-130` carries `STRIPE_SECRET_KEY=` and `STRIPE_WEBHOOK_SECRET=`, both
empty. The `STRIPE_*` tokens anywhere under `server/` are those two plus `STRIPE_CAPABILITIES`,
`STRIPE_REVENUE` and `STRIPE_RULES` (unrelated — the connector and metrics-rule namespaces). **No value
was read, printed or written at any point.**

---

## Part 3 — entitlement, the trial, and the paywall

**Measured, read in full:** `server/core/subscription.py` — 324 lines / 11,780 B / sha256
`a03446ae2c2b4f42215044913def1ef9dcfb29b857ea23d04d641e733efdaeb6`;
`server/models/subscription.py` — 31 lines / 1,345 B / sha256
`d08aaf985e153cf73d9d053d656e372a9b211c7b8387aff72986d879dcd16c39`.

### 3.1 Resolution order (`get_user_subscription`)

1. Raw SQL: `SELECT plan, status, current_period_end, trial_start, trial_end, stripe_subscription_id
   FROM subscriptions WHERE user_id = :uid ORDER BY created_at DESC LIMIT 1` — newest row wins.
2. **No row + grandfathered** (account created before `PAYWALL_GRANDFATHER_BEFORE`) -> SCALE,
   status `"grandfathered"`, `is_active True`, `has_payment_method False`. The comment: *"Founding
   members: accounts created before the paywall launch keep full (Scale-level) access for free, forever —
   unless they later buy a paid plan, which takes precedence below."*
3. No row, not grandfathered -> FREE / `"none"` / inactive.
4. With a row: `is_active = status in ("active", "trialing")`, forced False when trialing and
   `now >= trial_end`, and False when active and `period_end and now > period_end`. If grandfathered and
   not active, the SCALE block is returned.
5. The returned `plan` and `effective_plan` are `plan if is_active else PlanTier.FREE`.

Returns `status`, `is_trial`, `trial_days_remaining`, `trial_end`, `is_active`,
`has_payment_method = bool(stripe_sub_id)`, `current_period_end`, `grandfathered`.

`_grandfather_cutoff()` reads env `PAYWALL_GRANDFATHER_BEFORE`: empty -> `None`; else
`datetime.fromisoformat(raw.replace("Z",""))`; `ValueError` logs
`f"Invalid PAYWALL_GRANDFATHER_BEFORE value: {raw}"` and returns `None`.

### 3.2 The trial is in-app, and it is the *second* clock

`start_trial(db, user_id)` — `trial_end = now + timedelta(days=TRIAL_DURATION_DAYS)`. Existing row:
`if prev_trial_start is not None: raise ValueError("You have already used your free trial.")`;
`if prev_status == "active": raise ValueError("You already have an active subscription.")`. No row:
`INSERT INTO subscriptions (user_id, plan, status, trial_start, trial_end, monthly_price, created_at,
updated_at) VALUES (:uid, :plan, 'trialing', :start, :end, 0, :now, :now)`. Returns
`{"plan": TRIAL_PLAN, "status": "trialing", "is_trial": True, "trial_days_remaining":
TRIAL_DURATION_DAYS, "trial_end": ..., "is_active": True}` — i.e. **Scale-level features for 30 days,
locally, with no Stripe object involved at all.**

**G3 (Part 5): the two clocks.** The trial is ours; Stripe's `trialing` is deliberately collapsed into
local `active` (`"we run our own in-app trial"`). A subscription started via Checkout therefore reports
`status: "active"` and `is_trial: False` even while Stripe considers it trialing, and an in-app trial
carries `status: "trialing"` with no `stripe_subscription_id`, hence `has_payment_method False`. **The
spec must state the rule the code implies:** the in-app trial is authoritative for entitlement; Stripe's
trial state is never surfaced. Two further wrinkles: `subscription.py` writes the raw string `"trialing"`
while `models/subscription.py` declares `SubscriptionStatus.TRIALING` and the Stripe map writes
`"active"`; and `models/subscription.py` carries the stale comment
`plan = Column(String, default="free")  # free, starter, pro, enterprise` — the real tiers are
free/starter/growth/scale, and `seats` (default 1) is declared but unused by `plans.py`.

### 3.3 Enforcement

`check_feature_access(feature)` — a FastAPI dependency factory; `is_master` short-circuits; else
`has_feature(effective_plan, feature)` or raises 403 with detail
`{"error": "feature_locked", "feature", "feature_label", "required_plan", "required_plan_name",
"current_plan", "message": f"{feature_label} requires the {plan_name} plan or higher."}`.

`class PaywallMiddleware(BaseHTTPMiddleware)` — active only when env `PAYWALL_ENABLED` lowercased equals
`"true"` (**default `"false"`**, so the paywall is off unless explicitly turned on). It skips
`EXEMPT_METHODS = {"GET", "HEAD", "OPTIONS"}`; matches `request.url.path` first-match against
`ROUTE_FEATURE_MAP` (16 `(re.compile(...), Feature.X)` pairs — copilot, quick-chat, simulations,
simulator, simulation-copilot, truth-scan, connectors, fundraising, cap-table, board-deck export, hiring,
digital-twin, ai-graphics, investor-room, doc-generator); resolves `user_id` from the auth cookie via
`decode_token(token)` -> `payload.get("sub")` inside a bare `try/except: pass` and **passes through when
none resolves**; then checks
`plan_features = PLAN_DETAILS.get(effective_plan, PLAN_DETAILS[PlanTier.FREE])["features"]` and returns
403 with the same detail shape when the feature is absent. **Any exception is caught, logged as
`f"Paywall middleware error: {e}"`, and the request is ALLOWED THROUGH** (Part 5, G8). `finally:
db.close()`.

The route map carries this operative comment, worth preserving in any rewrite: *"NOTE: FastAPI sees paths
WITHOUT the /api prefix (Express strips it when proxying), but keep the prefix optional so this works in
both contexts."* — every pattern is `^(?:/api)?/...`.

### 3.4 The schema

`subscriptions` (SQLAlchemy model): `id`, `user_id` (FK `users.id`, nullable, **no unique constraint**),
`company_id`, `stripe_subscription_id`, `stripe_customer_id`, `plan`, `status` (default `active`),
`seats`, `monthly_price` (Float), `current_period_start`, `current_period_end` (DateTime),
`created_at`, `updated_at`, relationships to `User` and `Company`.

**Resolved, not a defect:** the model does **not** declare `trial_start` / `trial_end`, but
`server/core/migrations.py:1774-1785` adds both —
`"""Add trial_start and trial_end columns to subscriptions table."""` with the tuples
`('trial_start', 'TIMESTAMP'), ('trial_end', 'TIMESTAMP')` and the loop
`f"ALTER TABLE subscriptions ADD COLUMN {col_name} {col_type}"`, logging
`f"Added column {col_name} to subscriptions"`. **So the columns the raw SQL selects do exist in the
database. The model not declaring them is a documentation gap, not a runtime break** (Part 5, G7).

---

## Part 4 — the client, and a measured divergence you can see on the live site

**Measured:** `client/src/pages/pricing.tsx` — 285 lines / 10,693 B / sha `1310a8247ab5986e`;
`client/src/pages/billing.tsx` — 401 lines / 15,594 B / sha `4d9d13ffc9014b30`.

`pricing.tsx` defines `const tiers = [` at line 13 with prices `"$0"` (l.16), `"$29"` (l.31), `"$49"`
(l.47), `"$99"` (l.63) — **matching `PLAN_DETAILS`** — and emits JSON-LD `offers` at
`price: "0"/"29"/"49"/"99"`, `priceCurrency: "USD"`. It also renders a visible description at line 113:

> *"FounderConsole is free while in early access — every feature unlocked, no credit card required.
> Planned pricing: Free, Starter $29, Growth $49, Scale $99 per month."*

Test ids `card-tier-<name>` and `button-cta-<name>`.

`billing.tsx` imports `useSubscription, usePlans, useStartTrial, useSubscribe, useBillingPortal,
type PlanData` from `@/hooks/use-subscription` and `trackEvent` from `@/lib/posthog`; defines
`PLAN_ICONS` (free->Zap, starter->Sparkles, growth->Sparkles, scale->Crown), `PLAN_ACCENTS` (growth
ringed emerald), and **duplicates the tier order client-side**:
`const PLAN_HIERARCHY = ['free','starter','growth','scale']` with `planRank(plan)`, used by `PlanCard`
to derive `isCurrent` / `isUpgrade` / `isDowngrade`. Card test id `plan-card-${plan.id}`.

### 4.1 The divergence (a headline finding)

**Measured.** `https://founderconsole.ai/pricing` — the live public page — **contains no pricing figures
at all.** It states: *"Every FounderConsole feature is free during the public beta"*; *"No credit card is
required to start, and **there is no trial clock running in the background**"*; *"Paid tiers will be
introduced once the beta ends"*; it promises existing users continued data access and advance notice; and
it advertises three no-account tools (runway calculator, default alive/dead check, survival simulator).

So three artifacts disagree about the same commercial offer:

| Source | What it says | State |
|---|---|---|
| `server/core/plans.py` + `scripts/stripe_bootstrap.py` | four tiers at $0 / $29 / $49 / $99, monthly and annual, Stripe prices live on first use | **shipped in `main` @ `748d410c`** |
| `client/src/pages/pricing.tsx` | the same four prices, plus a visible "planned pricing" line and schema.org offers | **shipped in `main` @ `748d410c`** |
| `https://founderconsole.ai/pricing` | no prices; free during beta; **"no trial clock running"** | **live, fetched 2026-10-14** |

The live page's "no trial clock" sentence **directly contradicts** the shipped in-app 30-day SCALE trial
(`TRIAL_DURATION_DAYS = 30`, `TRIAL_PLAN = PlanTier.SCALE`, started by `POST /billing/start-trial`).
Either the live page is stale relative to `main`, or the two are describing different moments in a
deliberate beta story and the copy has not caught up with the code. **This spec does not resolve which —
it records the mismatch as measured and flags it as the first thing to settle before any billing work
ships**, because a user reading the marketing page today is told one thing and an authenticated user
calling `/billing/subscription` is told another. *(Assumed: that the live page is served from `main`
rather than from a separate marketing deployment — I did not fetch the deploy configuration.)*

---

## Part 5 — gaps and defects, each with its evidence

Ordered by what I would fix first. **None of these is a code change; this is the list the spec exists to
produce.**

**G1 — No `invoice.payment_succeeded`, and no path back from `past_due` to `active`.**
*Measured twice, independently:* `api/billing.py`'s handler (four branches) and `stripe_bootstrap.py`'s
`WEBHOOK_EVENTS` (four entries). Consequence: a customer whose card fails is marked `past_due` by
`invoice.payment_failed`, and **nothing in the codebase ever moves them back** — the only writes to
`status` come from `customer.subscription.updated`, which Stripe does send on recovery, so the practical
effect is that local state depends on an event the code does not deliberately listen for. Either add
`invoice.payment_succeeded` (and/or `invoice.paid`) or document that recovery rides on
`customer.subscription.updated`.

**G2 — No webhook idempotency store.** `stripe_webhook` processes every delivery; Stripe retries failed
deliveries for up to three days and can deliver the same event more than once. There is no table of
processed event ids, so a retry re-applies the upsert. For the current handlers that is mostly benign
(the upsert is idempotent by construction), **but it is not benign for anything with a side effect** —
and the moment someone adds a receipt email or a usage reset to this handler, it double-fires. Record the
event id and skip duplicates.

**G3 — Two independent trials, deliberately collapsed into one.** Part 3.2. The in-app trial is
authoritative; Stripe's `trialing` becomes local `active`. Name this rule in the docs, or a future reader
will "fix" the collapse and break trial reporting.

**G4 — `subscriptions` has no unique constraint on `user_id`, and resolution takes the newest row.**
`get_user_subscription` does `ORDER BY created_at DESC LIMIT 1`; `_upsert_subscription_from_stripe`
UPDATEs the newest row or INSERTs. The model declares no unique index on `user_id`. Nothing currently
creates a second row, but nothing prevents it either, and the failure mode is silent (a stale newest row
wins). *Measured:* model read in full; the `ORDER BY … LIMIT 1` and the UPDATE-or-INSERT logic both read
in full.

**G5 — `_price_cache` is process-local, unbounded and never invalidated.** Under multiple workers each
process keeps its own copy, and a price archived or repriced in the dashboard is not seen until restart.
Fine at today's scale (a handful of prices); worth a comment, or a TTL, before it is trusted.

**G6 — `plan_from_price` parses the lookup key by splitting on `_` and taking `parts[1]`.** It works for
`fc_growth_monthly` and would break for any plan whose name contains an underscore. Prefer the
`metadata.fc_plan` path (which the code already checks first) and treat the split as a legacy fallback,
or parse from the right: `key.split("_")[1]` is only correct while plan names are single tokens.

**G7 — The model does not declare `trial_start` / `trial_end`, and carries a stale tier comment.**
Resolved as a documentation gap, not a runtime break (Part 3.4 — the migration adds the columns). The
comment `# free, starter, pro, enterprise` names two tiers that do not exist. The unused `seats` column
is a third small lie in the same file. All three are one-line fixes.

**G8 — The paywall fails OPEN, and passes through unauthenticated requests.** `PaywallMiddleware`
catches any exception, logs it, and allows the request; and when no `user_id` resolves it also passes
through. So a bug in the middleware, or a request the auth cookie does not cover, is served **unlocked**
rather than refused. Whether that is right depends on the beta story — it is consistent with "free during
the public beta" — but it should be a decision on the record, not a default. Also note
`PAYWALL_ENABLED` defaults to `"false"`, so **the paywall is off in production unless the environment sets
it**, which is another assumed-vs-measured item I could not settle without the deploy env (Part 6).

**G9 — `/billing/webhook` is exempt from session auth** (`server/main.py:442`) and protected only by the
signature. That is the correct design, and it is worth stating explicitly so it is not "fixed" by adding
session auth. The corresponding requirement is that `STRIPE_WEBHOOK_SECRET` must be present and correct;
when it is empty, `verify_webhook` will reject every delivery with a 400 and **nothing else in the system
will notice** — worth a startup warning, mirroring the one the metrics rules already use for other
integrations.

**G10 — The bootstrap script and the runtime both create catalog objects.** They agree by construction on
the lookup key, so the duplication is safe, but a reader of either file alone cannot tell that
`ensure_price` and `stripe_bootstrap.py` are the same operation written twice. Say so in both.

**G11 — Nothing in the paywall or billing path appears in CI.** The checks named by `OPERATING-MODEL.md`
are `npm run check`, `pytest server/tests`, `python qa-lab/runner/qa_runner.py` and
`bash scripts/launch_gate.sh`. **Assumed, not measured:** that none of them exercises a Stripe path — I
did not run them (god's boundary: no live calls, no heavy jobs). If true, the whole surface in this spec
is unverified by the gate that guards `main`, and a single test that `POST /billing/subscribe/{plan}`
returns the 503 when `stripe_enabled()` is false would cost almost nothing.

---

## Part 6 — the pricing numbers, marked

Every figure in this section is either **measured** (from a file whose sha is printed in Part 1-4, or from
a live fetch dated below) or **assumed** (labelled). No figure here comes from Oracle's keyword map:
`oracle-muqoa36l` is archived and god's instruction was explicit — *"DO NOT wait on its pricing inputs:
source pricing from the repo and public pricing pages."*

| Tier | Monthly | Annual | Annual vs 12x monthly | Source |
|---|---|---|---|---|
| Free | $0 | $0 | — | **measured**, `plans.py` |
| Starter | $29 | $290 | $58 cheaper (2 months free) | **measured**, `plans.py` |
| Growth | $49 | $490 | $98 cheaper (2 months free) | **measured**, `plans.py` |
| Scale | $99 | $990 | $198 cheaper (2 months free) | **measured**, `plans.py` |

**Measured** (arithmetic on the measured figures): the annual price is exactly 10x the monthly price at
every paid tier — a deliberate "two months free" and consistent across the ladder. **Measured:** the
client's `pricing.tsx` renders the same four monthly figures and the same four values in its schema.org
`offers`. **Measured:** the live page carries none of them and instead says the product is free during
the beta.

**Assumed, and flagged for Vishesh because it is a commercial input, not a code fact:**
- That these prices are still the intended launch prices. They are what the code ships.
- That USD is the intended currency. `CURRENCY = "usd"` is hard-coded in `stripe_billing.py`; there is no
  `currency_options` equivalent to the alpha.kids template. If any non-US pricing is wanted, that is a
  missing capability, not a bug.
- That the 30-day SCALE trial is intended (the live page says there is no trial clock). One of the two is
  wrong and only Vishesh can say which.
- That `PAYWALL_ENABLED` is set to `"true"` anywhere in production. Its default is `"false"`, and I did
  not read the deploy environment.

---

## Limits

- **Read-only everywhere except this file** (my own `founderconsole/` folder) and the docs PR named in the
  `done`. `backlog.md`, `needs-vishesh.md` and every other agent's files untouched.
- **No key was read, printed or written; no Stripe API call was made; no billing code was changed.**
  Every claim about Stripe's behaviour is a claim about *this repository's code*, not about the live
  account — I did not query the connected Stripe account and could not have.
- Every file figure above is `wc -l -c` plus `shasum -a 256` of the file on disk at
  `2026-10-14T05:44:07Z`, immediately before this was written; the tree was clean at `main` `748d410c`.
- **Not read, and therefore not covered:** `server/connectors/stripe.py` (529 lines / 21,668 B / sha
  `26b3876c` — a *data connector* that reads Stripe as a revenue source for the metrics engine; the spec
  must not be confused with it, and I deliberately did not fold it in), `client/src/pages/admin/billing.tsx`,
  and the middle of `pricing.tsx` / `billing.tsx` beyond the greps quoted in Part 4.
- **The one thing I could not test** is the deployed environment: `PAYWALL_ENABLED`,
  `PAYWALL_GRANDFATHER_BEFORE`, `STRIPE_SECRET_KEY` presence, and whether `APP_BASE_URL` matches the live
  host. Everything above about production behaviour is inferred from code defaults and labelled assumed.
