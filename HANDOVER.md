# FounderConsole — Engineering Handover

**Rewritten 15 September 2026; events lock re-verified ~23:43 GST by Chief of Staff (ex Historian).** Facts below were
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
| Team memory | `HANDOVER.md` + `agents/STATE.md` + `agents/CHARTER.md` |

Useful commit links (tip of `main` as of rewrite):

- `29b282e1 (#10 feedback+forecast) ← 65c7ca01` — Fix ai-governance callback caught by platform-admin mount (#7)
- `26791cd7` — Lock `/api/events` and `/admin/ai-governance` behind auth (#6)
- `f29f978b` — Add team CHARTER and STATE
- `cc2642c4` / `#5` — marketing SSR
- `4ef45867` — conversion / identity / leads

---

## 2. Git / deploy state (verified)

```
origin/main   344ab340  docs: sync HANDOVER and agents STATE (#8)
              ea19a61a  Mark auth lock shipped with live 401 evidence in STATE
              65c7ca01  Fix ai-governance callback caught by platform-admin mount (#7)
              26791cd7  Lock /api/events and /admin/ai-governance behind auth (#6)
              f29f978b  Add team CHARTER and STATE for autonomous coordination
              cc2642c4  Prerender remaining blank marketing pages for crawlers
```

**Production (curl 15 Sep 23:40 GST):**

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
- Broad marketing SSR is live (see table above). Growth owns SEO follow-through; audit done SEO impact.
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

1. **Reviewer sweep** of blast radius from `#6` and other Sep-reachable routes.
2. ~~Lock `/api/events` (+ ai-governance)~~ — **done live** (`#6`/`#7`, 401 at 23:43 GST).
3. **Analytics:** prove one visitor ≈ one identity (PostHog connector blocked).
4. **Product:** rage-click replays; confirm `lead_captured` exists and fires.
5. **Growth:** SEO hygiene + SSR cross-link packs with Release Manager.
6. **Reliability:** deploy-landed monitor (served hash).
7. Remaining product debt from older audits (silent logout, billing theme, dead routes, a11y, bundle size).
8. Ads / money decisions stay with Vishesh.

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
