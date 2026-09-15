# FounderConsole — Engineering Handover

**Rewritten 15 September 2026; Phase 2 override + #16 live re-verified 16 Sep ~00:49 GST by Chief of Staff.** Facts below were
re-checked against the live site and `origin/main` on that timestamp. Inference
is labeled as such.

---

## 1. Where everything lives

| Thing | Location |
|---|---|
| GitHub repository | https://github.com/visheshkhurana/predixen |
| Default branch | `main` |
| Working copy (Vishesh's Mac) | `~/Fund-Flow` (may lag; prefer `origin/main`) |
| Production site | https://founderconsole.ai |
| Hosting | Railway, auto-deploys on push to `main` |
| Analytics | PostHog project **522965** — https://us.posthog.com/project/522965 |
| Google Ads | account **550-259-2868** (FOUNDER CONSOLE), `ocid=8450324777` |
| Payments | Stripe, live mode |
| Team memory | `HANDOVER.md` + `agents/STATE.md` + `agents/CHARTER.md` + `DECISIONS.md` + `AUTONOMY.md` + `ORG-22.md` |

Useful commit links (tip of `main` as of 16 Sep 00:49 GST):

- `34ce49e7` / `#16` — `/ai-cfo` free-tool SSR links + WebApplication JSON-LD (**live** 00:47 GST)
- `f48f71e3` — docs: tip after #14/#15
- `cb04e17d` / `#14` — deploy-landed monitor (**code on main; control asset still 200 HTML — not shipped live**)
- `295aedb5` / `#15` — CoS STATE/HANDOVER fold (**still Phase 1 parked staffing — superseded by this follow-up**)
- `3c2f1094` / `#13` — dispatch-only RM check suite
- `9d559d17` / `#12` — SEO SSR cross-links + `/ai-cfo` sitemap

---

## 2. Git / deploy state (verified)

```
origin/main   34ce49e7  seo: /ai-cfo free-tool cross-links + WebApplication JSON-LD (#16)
              f48f71e3  docs: tip cb04e17d — mark #14/#15 shipped
              cb04e17d  Add queued deploy-landed monitor (#14) — control NOT proven live
              295aedb5  docs: CoS STATE/HANDOVER after #12 (#15) — staffing still Phase 1
              3c2f1094  ci: workflow_dispatch-only RM check suite (#13)
```

**Production (curl 16 Sep 00:40 GST, Googlebot UA):**

- Served entry bundle: `index-eWXmctMP.js`
- `/health` → healthy, `routers_loaded: true`, DB + Redis connected
- Deploy proof rule: diff the **served asset hash** (or response body), never assume push = live

---

## 3. What shipped on 15 Sep (was "pending §3")

The August uncommitted Mac work is **no longer pending**. It landed as
`4ef45867` and is live.

### Verified live

| Check | Expect | Observed 23:40 GST |
|---|---|---|
| `GET /api/leads` | auth on list | **401** `Not authenticated` |
| `POST /api/leads` | public capture | **200** `{"status":"ok","created":true}` (23:45 GST probe) |
| `GET /api/simulations/jobs` | router live | **401** |
| `GET /api/slack/events` | POST-only route exists | **405** Method Not Allowed |
| `GET /api/events` | locked | **401** (also POST → 401) at 23:43 GST after `#6`/`#7` |
| `GET /admin/ai-governance` | locked | **401** at 23:43 GST |
| Marketing SSR | `id="ssr-content"` | **1** on features, about, faq, contact, privacy, terms, survival-simulator, pricing, demo, ai-cfo, home, runway-calculator |

### What that commit did (substance)

1. **API prefix fix** — routers use bare prefixes (`/leads`, `/events`, …) so Express `pathRewrite {"^/api": ""}` can reach them.
2. **Leads auth** — `GET /api/leads` behind platform admin; `POST` stays public for calculator email capture.
3. **PostHog single-identity** — stop double pageview + `reset()` on anonymous first paint (Analytics must prove devices≈sessions).
4. **Calculator clearable inputs + email-capture CTA** — Product owns `lead_captured` proof in PostHog.
5. **SSR / prerender** — expanded in `#5` / `cc2642c4` after the conversion ship.

### Trap that shipped with the prefix fix (closed)

Unlocking `/api/events` without auth made **public read+write** until `#6`.
A 23:40 GST probe still saw **200** (Railway pre-roll). At **23:43 GST** GET and
POST both return **401**; `/admin/ai-governance` returns **401**. Bundle may stay
`index-eWXmctMP.js` — cite response bodies, not the JS hash, for this class of ship.

`connector_catalog.py` was deliberately left alone (shadowed by `connectors.py`).

---

## 4. What is live right now

- Conversion + identity client changes from `4ef45867` are in the served bundle.
- Broad marketing SSR is live. **#12 SEO pack is live** (CoS Googlebot 00:40 GST: sitemap 36 locs, `/ai-cfo`=1, privacy/terms=0; SSR cross-links on `/` `/pricing` `/contact`; contact meta 143). SEO next = re-audit.
- **Geo gate is OFF** (fails open). Ad crawlers remain unblocked by design after the August AdsBot mistake.
- Entry bundle ~888 KB class; stylesheet still large/render-blocking (not re-measured this pass).

---

## 5. Traffic and conversion (last measured)

Weekly PostHog snapshot from the prior handover (week of 13 Sep). **Do not treat
sessions as people** until Analytics confirms the identity fix:

| Week of | Devices | Sessions | Pageviews | Paid pageviews |
|---|---|---|---|---|
| 09 Aug | 21 | 37 | 40 | 6 |
| 16 Aug | 101 | 188 | 211 | 62 |
| 23 Aug | 116 | 240 | 327 | 79 |
| 30 Aug | 65 | 124 | 142 | 60 |
| 06 Sep | 61 | 127 | 173 | 40 |
| 13 Sep | 31 | 48 | 146 | **0** |

Paid traffic was zero that week. Ads restart is **human-only**. Conversion events
had started firing (`signup_view`, `cta_click`, `calculator_used`, rageclicks) —
refresh after identity ship.

---

## 6. Known open items (Chief of Staff ranking)

1. **P0 auth lock trio** (templates / integrations / notifications) — **Vishesh held**; no agent works it.
1a. **Phase 2 is live by OVERRIDE** (18 agents). Metric gate unmet. Do **not** spawn Phase 3.
1b. ~~`/ai-cfo` SSR links + JSON-LD~~ — **#16 live** (CoS Googlebot 00:47 GST). Remaining SEO gap: `/faq` free-tool links.
1c. **#14 deploy-landed** code on main but control asset still **200 HTML** — do not mark shipped.
2. ~~Lock `/api/events` (+ ai-governance)~~ — **done live** (`#6`/`#7`).
3. ~~SEO SSR cross-links + `/ai-cfo` sitemap~~ — **#12 live** (`9d559d17`; CoS Googlebot recheck 00:40 GST).
4. **Analytics:** prove one visitor ≈ one identity (PostHog connector blocked).
5. **User Research:** rage-click write-up **done** — `agents/research/rage-click-writeup-2026-09-16.md` (4 sessions / 9 events, PostHog 522965). **Conversion Eng:** P0 watch sessions 1–2; do **not** claim `lead_captured` (0/0 90d).
6. **Reliability:** deploy-landed monitor (#14 in review).
7. **QA:** dispatch-only CI (#13 Gate 1 PASS; Actions minutes still Vishesh).
8. Remaining product debt from older audits. Ads / money stay with Vishesh.

---

## 7. Operating constraints

- **Only Release Manager pushes/merges to `main`.** Other agents open PRs; Reviewer (Gate 1) reviews.
- **Evidence rule:** no "shipped/fixed" in STATE without pasteable proof (hash, curl body, test output, query).
- Vite inlines `import.meta.env` at **build** time.
- `createRoot()` discards `#root` children — load-bearing for prerender; do not casually switch to `hydrateRoot`.
- `express.static` `index: false` is load-bearing for SEO prerender.
- AdsBot-Google ≠ Googlebot — regression covered in `geoRestrict` tests.
- Google Ads display path ≠ Final URL.
- Railway can lag; wait on hash/body change before declaring deploy failure.

---

## 8. Wrong beliefs (do not repeat)

| Believed | Actually | Cost |
|---|---|---|
| §3 pending forever on Mac | Shipped `4ef45867` 15 Sep | month of dead tools |
| Prefix fix alone is safe | `/api/events` public until `#6` | live data leak window |
| `/api/leads→401` means all methods | GET 401; POST 200 by design | almost doc-locked capture |
| Events still open after 23:40 probe | Pre-roll; 401 by 23:43 | almost left docs wrong |
| Bundle hash must move for auth ship | Bodies can change alone | wrong deploy signal |
| Push = deployed | Must diff served hash | stranded commits under unpaid Railway |
| `googlebot` regex covers AdsBot | It does not | ad disapprovals ~3 days |
| Ads display path = Final URL | Cosmetic | wrong diagnoses ×2 |
| This morning's HANDOVER still true | It claimed §3 uncommitted | agents acting on stale ship status |

Full Corrections table: `agents/STATE.md`.

---

## 9. Strategic context

Vishesh prioritized **fix conversion before more traffic**, and work that runs
without a daily posting habit. §3 was the first instalment and is now live;
measurement trust and the events auth hole are the immediate follow-through.

Coordinate via `agents/STATE.md`. Chief of Staff owns honesty of that file and this
handover; Release Manager merges doc PRs.
