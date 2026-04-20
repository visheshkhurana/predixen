# Lead Gen + Sales Automation

n8n automation for FounderConsole's outbound, inbound, enrichment, and activation flows. Designed to live alongside the product code in this repo so infra + growth are version-controlled together.

All details are in [`docs/SETUP.md`](./docs/SETUP.md). Quick reference below.

---

## What's here

```
lead-gen-automation/
├── README.md                              ← this file
├── .env.example                           ← n8n env vars checklist
├── webhook-tests.sh                       ← curl scripts for end-to-end testing
├── workflows/
│   ├── lead-gen-main.json                 ← main 134-node workflow (4 sub-flows)
│   └── activation-drip.json               ← trial-signup welcome + 48h nudge
├── knowledge-base/                        ← paste each .md into a Google Doc
│   ├── kb-product.md
│   ├── kb-pricing.md
│   ├── kb-objections.md
│   └── kb-onboarding.md
├── templates/
│   ├── prospects-sheet-template.csv       ← import into Google Sheets
│   └── airtable-contacts-schema.md        ← Airtable CRM setup
└── docs/
    ├── SETUP.md                           ← the main guide — read this
    └── original-workflow-walkthrough.md   ← reference: the template we adapted
```

## The 4 sub-workflows

| # | Flow | Trigger | Goal |
|---|---|---|---|
| 1 | Sales Nav scraper | Cron | Pull 50 founder leads/week into Prospects sheet |
| 2 | Lead enrichment | Cron | Fill missing data, draft + send email #1 |
| 3 | Cold outbound drip | Webhook | 4-email sequence ending in trial signup |
| 4 | Inbound AI agent | Gmail Trigger | Classify replies, auto-reply, book demos |
| 5 | Activation drip | Webhook from FC signup | Welcome → check sim → nudge if not activated |

## How it ties to FounderConsole

The activation drip fires when a user signs up on founderconsole.ai. Point your backend's signup handler at:

```
POST https://your-n8n.example.com/webhook/founderconsole-signup
Body: { "email": "...", "first_name": "...", "company_name": "...", "signup_source": "web" }
```

And when a user completes their first simulation, PATCH the Airtable record to set `has_simulated = true` — the 48h nudge check will skip them automatically.

See [`docs/SETUP.md`](./docs/SETUP.md) for the full implementation guide.

## Quick start

1. Read [`docs/SETUP.md`](./docs/SETUP.md) fully — it's the contract
2. Create credentials (Google OAuth, OpenAI, Airtable, Apify, Perplexity, Hunter, Prospeo)
3. Import both workflows into n8n
4. Paste the 4 KB docs into Google Docs, wire doc IDs
5. Create Prospects sheet + Airtable Contacts base
6. Run `bash webhook-tests.sh all` against your own email
7. Activate workflows

## Tooling cost (entry tier, monthly)

~$130/mo + ~$30/mo in per-call AI/enrichment for ~1k leads. Can start leaner by skipping Hunter + Prospeo and using only Skrapp's free tier.

## Safety guardrails

- Cap outbound sends at 30/day from a fresh sending domain; ramp by +10/day/week
- Use a subdomain (`mail.founderconsole.ai`) for outbound to protect the root
- SPF / DKIM / DMARC must be configured before going live
- Hunter status filter is gated to `valid` or `accept_all` only — don't relax this

## Changelog

- **2026-04-20** — initial import; adapted from [n8n-resources/Lead gen Systems.json](https://github.com/visheshkhurana/n8n-resources) template with FounderConsole-specific prompts, ICP filter, and email copy.
