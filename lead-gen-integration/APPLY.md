# Applying the lead-gen patch to predixen

End-to-end integration: natively embedded admin panel at `/admin/lead-gen` with n8n as the automation engine.

---

## What you're adding

**Backend (Python / FastAPI):**
- `server/api/lead_gen.py` — admin-gated REST API (leads, campaigns, templates, stats, settings)
- `server/webhooks/lead_gen_webhooks.py` — HMAC-signed receivers for n8n pushes
- `server/models/lead_gen.py` — SQLAlchemy models for new tables
- Migration: `migrations/0001_lead_gen.sql` — extends `leads`, creates 4 new tables, seeds 12 email templates

**Frontend (React / TypeScript):**
- `client/src/lib/api/lead-gen.ts` — typed API client with React Query keys
- `client/src/pages/admin/lead-gen/` — 5 pages (Overview, Leads, Campaigns, Templates, Settings)
- Routes into `App.tsx`
- Nav entry into `AdminLayout`

**Shared:**
- `shared/lead-gen-schema.ts` — Drizzle schema additions (merge into `shared/schema.ts`)

---

## Apply in 6 steps

### 1. Merge files into your working copy

From repo root:
```bash
# Backend
cp predixen-integration-patch/server/api/lead_gen.py server/api/lead_gen.py
cp predixen-integration-patch/server/models/lead_gen.py server/models/lead_gen.py
cp predixen-integration-patch/server/webhooks/lead_gen_webhooks.py server/webhooks/lead_gen_webhooks.py

# Frontend
cp predixen-integration-patch/client/src/lib/api/lead-gen.ts client/src/lib/api/lead-gen.ts
mkdir -p client/src/pages/admin/lead-gen
cp predixen-integration-patch/client/src/pages/admin/lead-gen/*.tsx client/src/pages/admin/lead-gen/

# Migration
mkdir -p migrations
cp predixen-integration-patch/migrations/0001_lead_gen.sql migrations/
```

### 2. Extend `shared/schema.ts`

Open `predixen-integration-patch/shared/lead-gen-schema.ts`. The first block **replaces** your existing `leads` table definition in `shared/schema.ts` (it adds ~18 new columns). The remaining 4 tables + relations append at the end.

### 3. Register the routers in `server/main.py`

See `predixen-integration-patch/docs/server_main.py.diff`. Two `include_router` calls in `_register_remaining_routers`.

### 4. Add routes in `client/src/App.tsx`

See `predixen-integration-patch/docs/App.tsx.diff`. One lazy import + one `<Route>`.

### 5. Add the nav entry in `AdminLayout`

See `predixen-integration-patch/docs/AdminNav.diff`. One link/item in the admin sidebar.

### 6. Run the migration

```bash
psql $DATABASE_URL -f migrations/0001_lead_gen.sql
```

Or, if you prefer Drizzle-generated migrations, run `drizzle-kit push` — it'll see the schema diff and prompt you to apply.

---

## Required env vars

Add to your `.env`:

```bash
# 64-hex-char shared secret (generate: openssl rand -hex 32)
# Set the SAME value in n8n's env vars so its HTTP nodes can sign payloads.
LEAD_GEN_WEBHOOK_SECRET=<64-hex-chars>
```

The n8n UI connection (base URL + API key) is configured live via the admin panel at `/admin/lead-gen/settings` — no env var needed.

---

## How predixen ↔ n8n talk

```
┌────────────────────────────┐     webhook (HMAC-signed)     ┌────────────┐
│  predixen                  │ ───────────────────────────▶  │    n8n     │
│   POST /leads/{id}/actions │                               │            │
│   (admin clicks "Send")    │                               │            │
└────────────────────────────┘                               │            │
                                                              │            │
                     ┌── webhook (HMAC-signed) ───────────────│  Runs      │
                     ▼                                        │  workflow  │
┌────────────────────────────┐                                │  (LLM +    │
│  predixen                  │                                │  Gmail +   │
│   POST /webhooks/lead-gen/ │                                │  Apify +   │
│     ingest  (new lead)     │                                │  etc.)     │
│     event   (send/reply)   │◀───────────────────────────────│            │
│     simulation (your app)  │                                │            │
└────────────────────────────┘                                └────────────┘
```

- **Admin panel → n8n**: manual sends/pauses POST to n8n webhook URLs stored in `lead_gen_settings`.
- **n8n → predixen**: scraper, enrichment, email send, and reply events POST back to `/webhooks/lead-gen/ingest` and `/webhooks/lead-gen/event`. HMAC signature verified against `LEAD_GEN_WEBHOOK_SECRET`.
- **predixen (itself) → predixen**: when a user finishes their first simulation, your FastAPI simulation handler should call `/webhooks/lead-gen/simulation` with their email + P50 — this flips `has_simulated=true` so the activation-nudge n8n workflow skips them.

---

## Wiring n8n to call predixen's API

In each n8n HTTP node that talks to predixen, use these settings:

- **URL:** `https://your-predixen-host/webhooks/lead-gen/{ingest|event|simulation}`
- **Method:** POST
- **Body:** JSON (see Pydantic schemas in `server/webhooks/lead_gen_webhooks.py`)
- **Headers:**
  - `Content-Type: application/json`
  - `X-Predixen-Signature: {{ $crypto.hmac('sha256', $env.LEAD_GEN_WEBHOOK_SECRET, JSON.stringify($json)) }}`
  
  (n8n has a built-in `crypto.hmac` Function node helper; you can also use a small Code node.)

For n8n to fetch email templates at send time (so you can edit copy from the admin panel without touching n8n):

- **URL:** `https://your-predixen-host/api/admin/lead-gen/templates/by-key/{key}` (replace `{key}` with e.g. `cold_email_1`)
- **Auth:** pass a session cookie OR add a shared-secret check in `lead_gen.py` — currently gated by `get_current_user`, so create a service-account user for n8n.

---

## First-run test plan

```bash
# 1. Run the migration
psql $DATABASE_URL -f migrations/0001_lead_gen.sql

# 2. Boot the app (server + client)
npm run dev  # or your usual command

# 3. Log in as admin and navigate to /admin/lead-gen
# Should show the Overview dashboard with zero leads and the "Lead-gen is disabled" banner.

# 4. Go to /admin/lead-gen/settings, fill in n8n details, toggle enabled, save.

# 5. Test the ingest webhook (replace SECRET + HOST):
BODY='{"email":"test@example.com","first_name":"Test","company":"TestCo","source":"manual"}'
SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$LEAD_GEN_WEBHOOK_SECRET" -hex | cut -d' ' -f2)
curl -X POST "$PREDIXEN_HOST/webhooks/lead-gen/ingest" \
  -H "Content-Type: application/json" \
  -H "X-Predixen-Signature: $SIG" \
  -d "$BODY"

# 6. Refresh /admin/lead-gen/leads → you should see the test lead.

# 7. Click the lead, then "Send email #1". Check n8n executions tab to confirm
# the outbound webhook fired. If your n8n workflows aren't wired yet, the
# button will 400 with "outbound_webhook_url not configured".
```

---

## Rollback

If anything's broken:

```sql
-- Reverses the migration (destructive)
BEGIN;
DROP TABLE IF EXISTS lead_events;
DROP TABLE IF EXISTS lead_campaigns;
DROP TABLE IF EXISTS lead_templates;
DROP TABLE IF EXISTS lead_gen_settings;

-- To drop the columns we added to `leads`:
ALTER TABLE leads
  DROP COLUMN IF EXISTS first_name,
  DROP COLUMN IF EXISTS last_name,
  DROP COLUMN IF EXISTS linkedin_url,
  DROP COLUMN IF EXISTS website,
  DROP COLUMN IF EXISTS source,
  DROP COLUMN IF EXISTS sector,
  DROP COLUMN IF EXISTS stage,
  DROP COLUMN IF EXISTS last_funding_event,
  DROP COLUMN IF EXISTS status,
  DROP COLUMN IF EXISTS hunter_status,
  DROP COLUMN IF EXISTS summary,
  DROP COLUMN IF EXISTS hook,
  DROP COLUMN IF EXISTS enriched_at,
  DROP COLUMN IF EXISTS last_email_at,
  DROP COLUMN IF EXISTS reply_category,
  DROP COLUMN IF EXISTS trial_signed_up_at,
  DROP COLUMN IF EXISTS has_simulated,
  DROP COLUMN IF EXISTS p50_survival,
  DROP COLUMN IF EXISTS tags,
  DROP COLUMN IF EXISTS notes,
  DROP COLUMN IF EXISTS updated_at;
COMMIT;
```

Remove the new files, revert `shared/schema.ts`, `server/main.py`, `App.tsx`, `AdminLayout`.

---

## What I did NOT build (stretch goals for v2)

- Campaign creation UI (POST exists, UI is read-only for now)
- Segment-builder UI for `target_segment`
- Cadence editor (days editable via API but no inline UI)
- Rich-text email template editor (currently plain textarea)
- Lead import from CSV via drag-drop (use the ingest webhook in the meantime)
- Slack integration for reply notifications (easy follow-up — just add a POST to your existing Slack webhook inside `event` receiver)
