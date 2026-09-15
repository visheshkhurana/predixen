# Autonomy

Agents decide anything that can be undone. Vishesh keeps: money, credentials, legal, final send, pricing, direction.

| Type | Meaning | Who |
|---|---|---|
| 0 | Reversible, in policy | The owning agent; gates still apply to code |
| 1 | Irreversible / spend / creds / legal / public send as Vishesh | Batched daily to Vishesh by Chief of Staff |
| 2 | Phase gate (spawn phase 2/3) | Vishesh; CoS enforces the metric tripwires **unless Vishesh overrides in writing** |

Phase 2 tripwire (policy): identity + signup events verified **and** `lead_captured` fired 2 straight weeks.
**16 Sep OVERRIDE:** Vishesh started Phase 2 with that gate unmet (`lead_captured` still 0; identity unverified). Logged in DECISIONS.md. This is not evidence the metrics were hit.

Phase 3 tripwire (still in force): 4 weeks of week-on-week growth in activated founders **and** a human pricing decision. Do not spawn Phase 3.

Executives (Product / Engineering / Growth Leads) start **within policy**. Finance Watcher stays **read-only**. Data Trust starts **within policy**. Build makers start **autonomous** (PRs still gated). Lifecycle and SEO stay **within policy**. User Research starts **autonomous** (user contact is drafts only).

Auth lock trio (`templates` / `integrations` / `notifications`) remains **human-hold** — no agent edits those files.
