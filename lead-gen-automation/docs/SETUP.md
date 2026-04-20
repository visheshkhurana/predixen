# FounderConsole — Lead Gen + Sales Automation

End-to-end n8n setup for [founderconsole.ai](https://founderconsole.ai) — adapted from the original [Lead gen Systems](https://github.com/visheshkhurana/n8n-resources/blob/main/Lead%20gen%20Systems.json) template, retooled for FounderConsole's free-trial-signup goal.

> **Two files to import:**
> 1. `FounderConsole — Lead Gen + Sales Automation.json` — main workflow (5 sub-flows on one canvas)
> 2. `FounderConsole — Activation Drip.json` — fires on new signup, sends welcome + 48h nudge

---

## What you get

| # | Sub-workflow | Trigger | Goal |
|---|---|---|---|
| 1 | **Sales Nav scraper** | Cron (weekly) | Pull 50 founder leads/week into the Prospects sheet |
| 2 | **Lead enrichment** | Cron (daily) | Fill missing data, draft + send first email |
| 3 | **Cold outbound drip** | Webhook (lead added) | 4-email sequence ending in trial signup or breakup |
| 4 | **Inbound AI agent** | Gmail Trigger | Triage replies, auto-reply, book demos |
| 5 | **Activation drip** | Webhook (new signup) | Welcome → check sim run after 48h → nudge |

All five push toward the same metric: **trial signups at founderconsole.ai**.

---

## ICP — who we're targeting

Encoded in the Apify Sales Nav URL inside the **Apify Config** node. Default filter:

- **Titles:** founder, co-founder, CEO
- **Industries:** Software, IT Services, Internet, Fintech (LinkedIn industry IDs `4, 6, 96, 3133`)
- **Company size:** 2–50 employees
- **Tenure:** 0–5 years at current company (signal of early-stage)
- **Geography:** US + India (`102277331, 103644278`) — edit for your TAM

Tune the URL by going to LinkedIn Sales Navigator, applying filters in the UI, copying the resulting URL, and pasting it into the `salesNavUrl` field of the **Apify Config** node.

---

## Credentials checklist

Create these in n8n (Settings → Credentials → New) **before** importing the workflow.

| Service | Used by | Cost | Where to get |
|---|---|---|---|
| **Google Sheets OAuth2** | Prospects sheet (read/write) | Free | console.cloud.google.com → enable Sheets API → OAuth credentials |
| **Gmail OAuth2** | All outbound + inbound | Free with Workspace | Same Google Cloud project, enable Gmail API |
| **Google Calendar OAuth2** | Demo booking | Free | Same project, enable Calendar API |
| **Google Docs OAuth2** | Knowledge base RAG | Free | Same project, enable Docs API |
| **Apify API Token** | LinkedIn scraping | $49/mo plan covers ~5k profiles | apify.com → Settings → Integrations |
| **Perplexity API Key** | Company research | Pay-per-call (~$0.005/lead) | perplexity.ai/settings/api |
| **Hunter.io API Key** | Email verification | $49/mo (1k verifies) | hunter.io/api |
| **Prospeo API Key** | Email finder (primary) | $25/mo entry | prospeo.io |
| **Skrapp API Key** | Email finder (fallback) | Free tier OK to start | skrapp.io |
| **OpenAI API Key** | All LLM nodes | ~$0.50–2 per 100 emails | platform.openai.com |
| **Airtable PAT** | CRM + activation tracking | Free tier OK | airtable.com/create/tokens |
| **LinkedIn `li_at` cookie** | Apify Sales Nav scraper auth | Free with Sales Nav sub | Chrome DevTools → Application → Cookies → linkedin.com → `li_at` |

Set the LinkedIn cookie as an n8n **environment variable** named `LINKEDIN_LI_AT`. The Apify Config node references it via `{{ $vars.LINKEDIN_LI_AT }}`.

**Total monthly tool cost (entry tier):** ~$130 + per-call AI/Perplexity (~$30 for 1k leads). Skip Hunter + Prospeo if you want to start lean — use only Skrapp (free tier).

---

## Google Sheet schema — `Prospects`

Create one sheet, name it `Prospects`. First row (headers):

```
email | first_name | last_name | company_name | linkedin_url | website | sector |
stage | last_funding | summary | hook | hunter_status | enrichment_status |
sent_email_1_at | sent_email_2_at | sent_email_3_at | sent_email_4_at |
replied_at | unsubscribed_at | trial_signed_up_at | notes
```

Point the **Save Company to Google Sheet** and **Update *** nodes at this sheet.

---

## Airtable schema — `Contacts` (CRM)

| Field | Type |
|---|---|
| email (primary) | Email |
| first_name | Single line text |
| last_name | Single line text |
| company_name | Single line text |
| signup_source | Single select (web, scraper, manual) |
| signed_up_at | Date |
| has_simulated | Checkbox |
| trial_status | Single select (free, pro, team, churned) |
| last_email_at | Date |
| reply_category | Single select (pricing, question, use_case, onboarding, meeting, misc) |
| notes | Long text |

The activation workflow sets `has_simulated` based on a webhook your FounderConsole backend should fire when a user completes their first simulation. Add this to your backend:

```ts
// pseudocode in your simulator-complete handler
await fetch('https://your-n8n.example.com/webhook/founderconsole-activation', {
  method: 'POST',
  body: JSON.stringify({ email: user.email, simulated_at: Date.now() })
});
```

Or just have your DB set `has_simulated = true` directly and let the n8n check on the 48h timer pick it up.

---

## Knowledge Base — Google Docs to create

The inbound AI agent uses 4 Google Docs as its retrieval source. Create these in your Drive and paste the doc IDs into the four `Knowledge Base*` Google Docs Tool nodes.

| Doc | Contents |
|---|---|
| `KB — Product` | What FounderConsole does, list of features (Survival Simulator, runway, P50/P90, cap table, dilution modeling, scenario saves), supported integrations |
| `KB — Pricing` | Free tier (Survival Simulator, basic runway). Pro $29/mo (scenario saves, cap table, exports). Team $99/mo (multi-user, investor-ready PDFs). FAQs about pricing. |
| `KB — Objections` | "I just use Excel" → simulator runs probability not point-estimate. "Too early" → free tier. "We don't share financials" → no signup needed for sim. |
| `KB — Onboarding` | Step-by-step first-simulation guide, common stuck points, where to find runway tab vs cap table tab, video walkthrough link. |

Tip: write these in conversational, founder-to-founder voice. The AI agent will mirror that tone in replies.

---

## Email copy — what the AI writes

### Cold email #1 (hand-written here as a model — actual sends are LLM-generated per prospect)

> **Subject:** acme.io — survival scenarios?
>
> Hey Sarah,
>
> Saw you raised a $1.4M pre-seed for Acme last month — congrats. Hiring two engineers I'd guess from the JD on your site.
>
> Most founders at pre-seed know their runway to the dollar but haven't stress-tested it. "What if growth stalls for 3 months? What if those engineers ramp slower?"
>
> I built FounderConsole to answer those in 10 minutes. Plug in your numbers and it simulates 1000s of futures — runway, P50/P90 survival probability, dilution after your next round, all modeled.
>
> Free at founderconsole.ai. If you run yours, send me back your P50 and I'll compare it against other YC pre-seed founders in our index.
>
> — Vishesh

### Follow-up cadence

| # | Days after #1 | Theme |
|---|---|---|
| 2 | +2 | Single insight (P50 vs P90 gap, or post-round dilution) |
| 3 | +3 | Soft demo offer ("I'll run it on a sample company close to yours") |
| 4 | +4 | Breakup — polite close-out, leave the link |

Reply detection happens between every step via an LLM check on the thread. As soon as a human replies, the drip stops and the inbound agent takes over.

### Welcome email (activation drip)

> **Subject:** welcome to FounderConsole — want me to walk you through it?
>
> hey {first_name},
>
> thanks for signing up. FounderConsole is built so you can run your first survival simulation in under 5 minutes — just plug in your MRR, burn, and cash balance. it'll show you P50 / P90 survival probability and where the sensitivity is.
>
> start here: https://founderconsole.ai/simulator
>
> three things most founders miss on their first run:
> 1. model hiring as a recurring expense, not one-time
> 2. plug in realistic growth variance (not just an average)
> 3. check the dilution tab after the sim — post-round cap table matters
>
> if you want, reply with your P50 and i'll tell you how it compares to other {company}-stage founders in our index.
>
> — Vishesh

### Activation nudge (sent at 48h if no simulation)

> **Subject:** quick nudge on the simulator
>
> noticed you haven't run a simulation yet — no pressure, but the whole value is in seeing your actual P50.
>
> if you got stuck, the three inputs you need are:
> - current cash
> - monthly burn
> - MRR (or 0 if pre-revenue)
>
> takes 90 seconds once you have those: founderconsole.ai/simulator
>
> or reply to this and i'll run one on a sample company close to yours.
>
> — Vishesh

---

## Inbound classifier — what gets auto-replied

The Master AI Agent classifies every inbound reply into one of these. Each has its own LLM-written reply prompt, all already in the JSON.

| Category | What triggers it | What we send back |
|---|---|---|
| `pricing` | "How much does it cost?" / "Do you have enterprise?" | Free + Pro + Team breakdown, link to pricing page |
| `question` | "Does it integrate with QuickBooks?" / "How is data stored?" | Direct answer from KB docs + invite to try free |
| `use case` | "We're a 5-person SaaS doing $20k MRR — would this help?" | Honest fit assessment, point to free Survival Simulator first |
| `onboarding` | "I signed up but can't find the runway tab" | Quick fix from KB, offer to look personally if it's a bug |
| `meeting` | "Let's hop on a call" | 2–3 calendar slots + booking link, books a Google Calendar event |
| `misc` | Friendly response, soft objection, referral, "no thanks" | Warm reply, light CTA to free tool |
| `noop` | Auto-responder, bounce, OOO | Logged, no reply sent |

---

## Import + first-run checklist

1. **Import both JSONs** into n8n (Workflows → Import from File).
2. **Wire credentials** — every node with a red dot needs a credential picked.
3. **Replace placeholders:**
   - Apify Config → paste your Sales Nav search URL
   - Google Sheets nodes → pick your `Prospects` sheet
   - Airtable nodes → pick your `Contacts` table
   - Knowledge Base Google Docs Tool nodes (×4) → paste doc IDs
4. **Set the env var** `LINKEDIN_LI_AT` (your `li_at` cookie value).
5. **Test in isolation:**
   - Run the Schedule Trigger manually → confirm one row appears in Prospects sheet.
   - POST a fake lead to the outbound webhook with curl → confirm enrichment runs and email #1 lands in your inbox (use your own email first).
   - Reply to that email → confirm Gmail Trigger fires and the classifier picks the right category.
   - POST to `/webhook/founderconsole-signup` with `{email, first_name, company_name}` → confirm the welcome email arrives.
6. **Activate workflows** (toggle in top-right of each).
7. **Plug the FounderConsole signup form** into the activation webhook.

---

## Volume + safety guardrails

A few things to avoid blowing up your domain reputation:

- **Cap sends at 30/day from a fresh sending domain.** Ramp by 10/day per week.
- **Use a subdomain** (e.g. `mail.founderconsole.ai`) for outbound to protect the root domain.
- **Set up SPF, DKIM, DMARC** before turning this on.
- **Add an unsubscribe link** to email #1 — the JSON template does NOT include this. Edit the email writer prompt to append: `"If you'd rather not hear from me again, just reply 'no thanks' and I'll mark you as opted-out."`
- **Hunter status filter** — already gated to `valid` or `accept_all` only. Don't relax this.
- **Watch the reply rate.** If reply rate < 5% after 200 sends, the email copy is wrong (not the volume) — iterate the AI Agent prompt before scaling.

---

## Things you'll probably want to change in week 2

- **Move follow-up gaps from days to business days** — hardcoded in the `Wait` nodes.
- **A/B test subjects** by adding a randomizer node before the AI writer.
- **Pipe replies into a Slack #leads channel** — there's already a Slack node hooked up to the "invalid email" path; rewire it to fire on any classified reply too.
- **Score leads by activation likelihood** post-enrichment — add an LLM scoring node and have it write a 1-10 to the sheet.
- **Add a Crunchbase enrichment branch** — the current Perplexity prompt asks for `last_funding_event` but Crunchbase API gives more reliable data; swap when you're ready to spend on it.

---

## Files in this directory

| File | Purpose |
|---|---|
| [`Lead gen Systems.json`](https://github.com/visheshkhurana/n8n-resources/blob/main/Lead%20gen%20Systems.json) | Original template (untouched, for reference) |
| `FounderConsole — Lead Gen + Sales Automation.json` | Main adapted workflow (134 nodes) |
| `FounderConsole — Activation Drip.json` | New signup → welcome + nudge |
| `FounderConsole — SETUP.md` | This file |
| `Lead gen Systems — walkthrough.md` | Node-by-node analysis of the original |
