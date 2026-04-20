# Predixen — Lead Gen Integration Patch

Native lead-gen feature for founderconsole.ai (predixen).

**What this adds:**
- Admin panel at `/admin/lead-gen` with 5 pages: Overview, Leads, Campaigns, Templates, Settings
- Backend REST API under `/api/admin/lead-gen/*` (Python / FastAPI)
- HMAC-signed webhooks at `/webhooks/lead-gen/*` for n8n ↔ predixen communication
- 4 new Postgres tables + extends existing `leads` table
- 12 seeded email templates (editable live from admin UI)
- React Query-based client with TypeScript types matching the Python schemas

**Philosophy:** predixen owns the data (Postgres is source of truth for leads, events, campaigns, templates). n8n is the stateless execution engine — it reads/writes via predixen's REST API and fires webhooks. You can edit email copy, pause campaigns, see funnel metrics, and trigger manual sends without leaving founderconsole.ai.

---

## Folder structure

```
predixen-integration-patch/
├── README.md                                (this file)
├── APPLY.md                                 ← step-by-step integration guide
├── shared/
│   └── lead-gen-schema.ts                   Drizzle schema additions
├── server/
│   ├── api/
│   │   └── lead_gen.py                      REST API (admin-gated)
│   ├── models/
│   │   └── lead_gen.py                      SQLAlchemy models
│   └── webhooks/
│       └── lead_gen_webhooks.py             HMAC-signed receivers
├── client/
│   └── src/
│       ├── lib/api/
│       │   └── lead-gen.ts                  typed API client
│       └── pages/admin/lead-gen/
│           ├── index.tsx                    /admin/lead-gen — overview
│           ├── leads.tsx                    /admin/lead-gen/leads
│           ├── campaigns.tsx                /admin/lead-gen/campaigns
│           ├── templates.tsx                /admin/lead-gen/templates
│           └── settings.tsx                 /admin/lead-gen/settings
├── migrations/
│   └── 0001_lead_gen.sql                    full SQL migration (idempotent)
└── docs/
    ├── App.tsx.diff                         route addition
    ├── AdminNav.diff                        nav sidebar addition
    └── server_main.py.diff                  router registration
```

## Start here

1. Read [`APPLY.md`](./APPLY.md) — 6-step integration guide
2. Apply the patch to your working copy
3. Run the migration
4. Boot the app, navigate to `/admin/lead-gen`
5. Wire n8n to call the webhooks (instructions in APPLY.md)

## Lines of code

- Python: ~750 lines (routes + models + webhooks)
- TypeScript: ~900 lines (pages + API client)
- SQL: ~120 lines (migration + seeds)
- **Total: ~1770 lines of production code**

All code follows existing predixen patterns: `require_platform_admin` for admin gating, `log_audit` for action logging, `CredentialEncryption` for API key storage, wouter for routing, shadcn/ui for components, React Query for state.
