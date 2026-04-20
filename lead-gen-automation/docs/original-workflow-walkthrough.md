# Lead gen Systems — node-by-node walkthrough

**Source:** [Pranathirai/n8n-resources → Lead gen Systems.json](https://github.com/Pranathirai/n8n-resources/blob/main/Lead%20gen%20Systems.json)
**Your fork:** [visheshkhurana/n8n-resources](https://github.com/visheshkhurana/n8n-resources) — file: [Lead gen Systems.json](https://github.com/visheshkhurana/n8n-resources/blob/main/Lead%20gen%20Systems.json)

**Size:** 134 nodes · 4 independent sub-workflows (each with its own trigger) packed into one canvas.

---

## What you're actually getting

This is not one workflow — it's four separate lead-gen automations sharing a canvas:

1. **Sales Navigator scraper** (Schedule Trigger) — harvests LinkedIn Sales Nav search results into Google Sheets.
2. **Lead enrichment** (Schedule Trigger1) — fills in missing company descriptions + emails for rows already in the sheet, then drafts & sends a first-touch Gmail.
3. **Cold-email drip engine** (Webhook) — fires when a new lead lands in GoHighLevel, verifies the email, scrapes the lead's website/LinkedIn/Instagram, writes a personalized 4-email sequence with reply-detection between each step.
4. **Inbound AI email agent** (Gmail Trigger) — watches your inbox, classifies replies into pricing / question / use-case / onboarding / meeting / misc, auto-replies with the right prompt, and books calendar events when someone wants a meeting.

They don't talk to each other in the JSON — you can safely import all four, then disable the ones you don't want.

---

## 1. Sales Navigator scraper (Schedule Trigger)

Runs on a cron you set. 3 nodes total.

| # | Node | Type | What it does |
|---|---|---|---|
| 1 | **Schedule Trigger** | `scheduleTrigger` | Fires on an interval (default: editable cron in the n8n UI). |
| 2 | **Apify Config** | `set` | Hard-codes the Apify actor input — Sales Navigator search URL, cookies, max results. You edit this to target a different search. |
| 3 | **Apify Linkedin Sales Navigator Scraper** | `httpRequest` | POSTs to `api.apify.com/v2/acts/curious_coder~linkedin-sales-navigator-search-scraper`. Returns up to N leads per page. |
| 4 | **Save Company to Google Sheet** | `googleSheets` (append) | Appends each lead as a new row (name, company, title, LinkedIn URL, etc.). |

**Credentials needed:** Apify API token, Google Sheets OAuth, a LinkedIn session cookie for the Apify actor, and a Sales Navigator subscription.

---

## 2. Lead enrichment + first-touch email (Schedule Trigger1)

Scans your Google Sheet for rows that are missing a company description, then enriches & emails them. 12 nodes.

```
Schedule Trigger1
 └─ Company Description Empty Record  (googleSheets — search for blank rows)
    └─ Limit  (cap the batch, default ~10)
       └─ Perplexity Get Company Background  (HTTP → api.perplexity.ai/chat/completions)
          └─ Format JSON  (LangChain informationExtractor — turns Perplexity prose into {summary, website_url})
             └─ Update Company Desc  (googleSheets — write description back to sheet)
                └─ Check If Website Not Found  (IF: website_url == "NULL")
                   ├─ FALSE (website found) → Prospeo Email Search  (api.prospeo.io/email-finder)
                   │    └─ Update Email And Status  (googleSheets — write email)
                   │       └─ Save Email  (set)
                   │          └─ Draft Email  (LangChain chainLlm — writes cold email body)
                   │             └─ Send Gmail  (gmail.send)
                   │                └─ Update Status  (googleSheets — mark "sent")
                   └─ TRUE (no website) → Get Email Search  (api.skrapp.io/api/v2/find — fallback email finder)
                        └─ Update Email And Status 2  (googleSheets — write email/status, no send)
```

**Why two email finders:** Prospeo is the primary (higher accuracy on known-domain). Skrapp is fallback when Perplexity couldn't find the website.

**Credentials needed:** Google Sheets, Perplexity, Prospeo, Skrapp, Gmail, plus the OpenAI/Anthropic model creds wired to the `Draft Email` and `Format JSON` nodes.

---

## 3. Cold-email drip engine (Webhook from GoHighLevel)

This is the big one — ~60 nodes. It receives a lead via webhook, enriches it heavily, writes a bespoke 4-email sequence, and drips those emails over time while watching for replies.

### 3a. Trigger + qualification

| # | Node | What it does |
|---|---|---|
| 1 | **Webhook** | Receives a payload (expected: GHL new-contact event). |
| 2 | **HighLevel** | Enriches via the GoHighLevel API — pulls full contact record. |
| 3 | **Merge** | Merges webhook payload + GHL record. |
| 4 | **Basic LLM Chain7** | LLM cleans/normalizes the lead (extracts name, company, email into a tidy object). |
| 5 | **Hunter** | Verifies the email via Hunter.io's `emailVerifier`. |
| 6 | **If6** | Status == `valid` OR `accept_all` → continue. Else → Slack notify + `Edit Fields` (dead-end log). |

### 3b. Enrichment fan-out (runs if email is valid)

After `If6`, the workflow forks into two parallel enrichment chains that each feed back into the email-writing step:

**Chain A — website scrape:**
```
Enrich Lead  (HTTP — endpoint left blank in template, you fill it)
 └─ If7  (catches 404/400 errors)
    └─ Extract domain or company  (LLM)
       └─ Full Domain or just company  (LLM — decides if we have a URL or just a name)
          └─ If2  (True = need to scrape)
             └─ HTTP Request4 → apify.com/acts/apify~website-content-crawler
                └─ Aggregate9 → Basic LLM Chain6  (summarize the website)
```

**Chain B — social scrape:**
```
Get social media urls  (Apify: apioracle~company-domain)
 └─ Extract company linkedin url  (LLM)
    └─ extract personal linkedin from company  (Apify: linkedin-company-employees-scraper)
       └─ Aggregate1 → Extract personal linkedin url  (LLM picks best match)
          └─ extract personal linkedin details  (Apify: linkedin-profile-detail)
             ├─ HTTP Request1  (website-content-crawler again on their personal site)
             │    └─ Aggregate4
             ├─ Extract Instagram  (LLM → HTTP3: apify instagram-scraper → Aggregate2)
             └─ HTTP Request6  (apify linkedin-batch-profile-posts-scraper — grabs recent posts)
                  └─ Aggregate3
```

Both chains converge at **Merge1 → Aggregate5 → Basic LLM Chain1 → Basic LLM Chain2 → AI Agent**. This is where the LLM stack takes everything — website summary, LinkedIn bio, recent posts, Instagram — and writes the personalized first email.

### 3c. The 4-email drip with reply detection

Once the AI Agent writes email #1:

```
Gmail9          → send email #1
 └─ Gmail10    → add tracking label
    └─ Wait    → (~1 day)
       └─ Gmail11 → get thread (did they reply?)
          └─ Aggregate6 → Basic LLM Chain3 → If3  ("did they reply?" true/false)
             ├─ TRUE  → No Operation  (stop — they replied, hand off to inbound agent)
             └─ FALSE → AI Agent1 → Gmail12 (reply with follow-up #2)
                        └─ Wait1 → Aggregate7 → Basic LLM Chain4 → If4
                           ├─ TRUE  → No Operation1
                           └─ FALSE → AI Agent2 → Gmail13 (follow-up #3)
                                      └─ Wait3 → Aggregate8 → Basic LLM Chain5 → If5
                                         ├─ TRUE  → No Operation2
                                         └─ FALSE → AI Agent3 → Gmail14 (follow-up #4, usually the "breakup" email)
```

Each step: check inbox → LLM decides if there was a reply → either stop or send next touch. 4 emails across ~4 days is the default cadence (the Wait nodes are where you tune days/hours).

**Credentials needed:** GoHighLevel, Hunter.io, Apify (multiple actors), Gmail, Slack, OpenAI/Anthropic/OpenRouter/Gemini (the template mixes models across the LLM nodes).

---

## 4. Inbound AI email agent (Gmail Trigger)

Watches Gmail for new messages, classifies them, and auto-replies with context from a Google Docs knowledge base. ~25 nodes.

| # | Node | What it does |
|---|---|---|
| 1 | **Gmail Trigger** | Fires on new inbound email. |
| 2 | **Gmail2** (get) | Pulls full message body + thread. |
| 3 | **Airtable** (search) | Looks up the sender in your CRM/contacts base. |
| 4 | **Google Calendar2** (getAll) | Grabs your upcoming availability (used later if the reply is a meeting request). |
| 5 | **Aggregate** | Bundles email + contact + calendar into one item. |
| 6 | **Basic LLM Chain** | First-pass filter: "is this an email I should auto-reply to?" returns `true`/`false`. |
| 7 | **If** (`text != "true"`) | Gate: if LLM said no, skip. |

**If the gate opens `false` (LLM said no / not in scope):**
- **Airtable1** (update) — logs the touch
- **Gmail** (removeLabels thread) — clears the "needs reply" label

**If the gate opens `true` (handle it):**
- **Master AI Agent** (LangChain agent) — classifies the email into one of 7 buckets (pricing / question / use case / onboarding / meeting / misc / ignore). The agent has access to:
  - **Knowledge Base**, **Knowledge Base1**, **Knowledge Base2**, **Knowledge Base3** — 4 Google Docs it can query as tools (product docs, pricing, FAQs, etc.).
- **Google Docs** (get) — fetches the main knowledge doc.
- **Switch** — routes on `Master AI Agent.output`:

| Route | Next node | Then |
|---|---|---|
| `pricing` | **Pricing** (LLM) | **Gmail1** — reply |
| `question` | **Question** (LLM) | **Gmail3** — reply |
| `use case` | **Use Case** (LLM) | **Gmail4** — reply |
| `onboarding` | **Onboarding** (LLM) | **Gmail6** — reply |
| `meeting` | **Meeting** (LLM) | **If1** — decide if we should book vs. suggest times |
| | ├─ book | **Google Calendar** (create event) → **Gmail8** reply with confirmation |
| | └─ suggest | **Google Calendar1** (list) → **Gmail5** reply with 2–3 slots |
| `misc` | **Misc** (LLM) | **Gmail7** — reply |
| (none) | **No Operation** | do nothing |

**Credentials needed:** Gmail, Airtable, Google Calendar, Google Docs, OpenAI/Anthropic (each reply chain has its own LLM node).

---

## Models used across the canvas

- `lmChatOpenAi` × 17 (most reply chains)
- `lmChatAnthropic` × 1 (one of the follow-up writers)
- `lmChatGoogleGemini` × 1 (one extractor)
- `lmChatOpenRouter` × 1 (labeled "GPT 5" — probably a placeholder/test)

Each LLM node has its own model credential — you can standardize on one provider when you import.

---

## Before you run it

Things you'll need to fill in before this template is usable:

1. **Credentials** — every external service above needs an OAuth/API-key credential created in n8n first.
2. **Apify actor inputs** — the `Apify Config` set node has a hard-coded Sales Nav URL; change it to your search.
3. **Knowledge Base docs** — the 4 Google Docs tool nodes point at specific doc IDs that won't exist in your Drive. Replace them with your own docs.
4. **Airtable base/table IDs** — the Airtable nodes reference a specific base; point them at yours.
5. **`Enrich Lead` HTTP node** — URL is blank in the template; you decide what enrichment API to call (or remove it and rely on the Apify chain).
6. **Wait durations** — default timing on the drip is probably aggressive (hours instead of days in some copies of this template). Verify the `Wait` node values match the 4-days-across-4-steps cadence advertised in the sticky note.
7. **Webhook URL** — grab the production URL from the Webhook node and plug it into GoHighLevel as an outbound webhook on new-contact.
