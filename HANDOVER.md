# FounderConsole — Engineering Handover

**Written 15 September 2026.** Every fact below was verified against the live
site, the git remote, the working copy and PostHog on that date. Where something
is inference rather than measurement it says so.

---

## 1. Where everything lives

| Thing | Location |
|---|---|
| GitHub repository | https://github.com/visheshkhurana/predixen |
| Default branch | `main` |
| Working copy (Vishesh's Mac) | `~/Fund-Flow` |
| Production site | https://founderconsole.ai |
| Hosting | Railway, auto-deploys on push to `main` |
| Analytics | PostHog project **522965** — https://us.posthog.com/project/522965 |
| Google Ads | account **550-259-2868** (FOUNDER CONSOLE), `ocid=8450324777` |
| Payments | Stripe, live mode |

Useful commit links:

- Current `origin/main`: https://github.com/visheshkhurana/predixen/commit/1e55b1e5
- Last commit I authored (deployed): https://github.com/visheshkhurana/predixen/commit/d4daf289
- Merged PR #4: https://github.com/visheshkhurana/predixen/pull/4

**There is no cloud copy of this work any more.** It was built in an ephemeral
container that has since been reclaimed. `~/Fund-Flow` on the Mac is the only
copy of the uncommitted changes described in section 3.

---

## 2. Git state, exactly

```
origin/main   1e55b1e5  Merge pull request #4 from visheshkhurana/cursor/survival-sim-auth-utm-788b
              941228a4  fix: send survival simulator auth CTAs to /auth with UTMs
local main    d4daf289  Show visitors a page instead of a blank screen   <- ~/Fund-Flow HEAD
              6ff8ea29  Probe crawler access from a blocked country, not just our own
              eb28f338  Never geo-block ad crawlers — this disapproved every ad
              f2b22f49  Geo-restrict to US and India; add X Ads conversion tracking
```

`~/Fund-Flow` is **2 commits behind** `origin/main` and has **10 uncommitted
files**. The only file changed upstream in those two commits is
`client/src/pages/survival-simulator.tsx`, which does not overlap with any
pending file, so `git pull` merges cleanly. I verified this with
`git diff --name-only HEAD origin/main`.

---

## 3. Uncommitted work sitting in `~/Fund-Flow` — READ THIS FIRST

Ten files, written 20 August, never committed and never deployed. I checksummed
all ten on 15 September against what was originally built; **all ten match
byte-for-byte**, so nothing has been edited or half-reverted in the interim.

**Modified (8):**

```
client/src/App.tsx
client/src/lib/posthog.ts
client/src/pages/runway-calculator.tsx
server/api/leads.py
server/api/events.py
server/api/simulation_jobs.py
server/api/slack_bot.py
server/seo-prerender.ts
```

**New, untracked (2):**

```
server/tests/analytics-single-identity.test.ts
server/tests/prerender-coverage.test.ts
```

### What that work does, and why it matters

**(a) Four API routers have never served a single request in production.**
`server/index.ts` proxies `/api/*` to the FastAPI backend with
`pathRewrite: {"^/api": ""}`. A router whose own prefix *contains* `/api` is
therefore registered at `/api/leads` while the request arrives as `/leads` — a
guaranteed 404 for every caller. Four routers were written that way: `leads`,
`events`, `simulation_jobs`, `slack_bot`. Still broken in production today:
`curl https://founderconsole.ai/api/leads` returns
`404 {"detail":"Not Found"}`, while `/api/companies` returns `401` because
`companies.py` uses the bare prefix `/companies`.

The pending diff changes each prefix to the bare form. `connector_catalog.py`
has the same flaw and was **deliberately left alone** — `connectors.py` already
serves the identical three paths and registers first, so it is shadowed either
way; "fixing" it only adds risk.

**(b) That fix carries a trap.** `GET /api/leads` had no authentication and
returns email addresses. It leaks nothing today only because it is unreachable.
Restoring the route without the lock converts a dead endpoint into a live
disclosure. The pending `leads.py` puts `GET` behind `require_platform_admin`
(from `server/api/admin.py`) and leaves `POST` public, which is correct — `POST`
is the conversion step on a free tool. **If you ship the prefix change, ship the
auth change with it.** Do not split them.

**(c) PostHog counts every visitor twice.** Two independent bugs compound:
`client/src/lib/posthog.ts` sets `capture_pageview: true` while `App.tsx`
separately fires `trackPageView()` on every route change including first render;
and `App.tsx` called `resetUser()` → `posthog.reset()` whenever `user` was
falsy, which on a marketing page is the first render. `reset()` mints a fresh
`distinct_id` *and* `session_id`.

Proof, from one real visitor on 15 August: two `$pageview` events on the same
path 258 ms apart, same `$device_id`, two different `distinct_id`s, two
different `session_id`s. Still true on 15 September — the most recent week shows
**31 devices producing 48 sessions**.

The practical consequence is not cosmetic inflation. An ad click lands on
identity A and a later signup lands on identity B, so no funnel can join them.
Every conversion rate in this project is measured through that.

**(d) The calculator's number inputs cannot be cleared.** `type="number"` with
`onChange={e => setCash(Number(e.target.value))}` — and `Number("")` is `0`, so
deleting the last digit of the pre-filled `500000` snaps the field back to "0"
and it never empties. The pending version holds text and parses on read. On
19 August the single most engaged paid visitor spent 138 seconds here, typed 47
keystrokes, rage-clicked twice and left; this is my best explanation, though I
never confirmed which element they clicked.

**(e) A conversion lighter than signup.** The calculator's only call to action
was "Connect Your Real Data" → full signup. The pending version adds an
email-capture card: one field, their own result mailed back, no account. It
`POST`s to `/api/leads` with the entered numbers in `notes`, and the endpoint
queues a Resend email via `BackgroundTasks`. There is a test that fails if the
client stops sending the three fields the email is keyed off, because the UI
says "check your inbox" the moment the POST succeeds.

**(f) Eleven blank pages get server-rendered text.** `/pricing`, `/demo`,
`/ai-cfo` and all eight `/runway/<vertical>` pages. The eight verticals had no
entry in `seo-prerender.ts` at all — no title, no description, no canonical.
They are driven from `client/src/data/runway-industries.ts`, the same file the
React page renders from, imported relatively (not via the `@/` alias) because
esbuild bundles the server from `server/index.ts` and a path alias is one more
thing that can resolve differently at build time.

### Verification status of the pending work, as of 20 August

Everything below was run and passed:

- `npx tsx server/tests/prerender-coverage.test.ts` — 16/16 paths, asserted
  against the **real built `dist/public/index.html`**. My first version of this
  test used a hand-written shell and failed all 15 paths, because `injectSEO`
  *replaces* the canonical and robots tags rather than inserting them. Run
  `npm run build` before this test or it will fail on a missing file.
- `npx tsx --test server/tests/analytics-single-identity.test.ts` — 7/7
- `npx tsx --test server/tests/geoRestrict.test.ts` — 13/13 (pre-existing)
- `npx tsc --noEmit` — 82 errors, identical to the baseline before the change.
  **82 is the expected number.** They are pre-existing and unrelated; do not
  treat a clean run as the goal.
- `npm run build` — clean

These have **not** been re-run since 20 August and `origin/main` has moved two
commits. Re-run them after pulling.

### Shipping it

```bash
cd ~/Fund-Flow
git stash                       # the 10 pending files
git pull --ff-only origin main  # d4daf289 -> 1e55b1e5
git stash pop                   # no conflicts expected; only survival-simulator.tsx moved upstream
npm run build && npx tsx server/tests/prerender-coverage.test.ts
npx tsx --test server/tests/analytics-single-identity.test.ts
git add -A
git commit -m "Make the free tools convert, and count the people who use them"
git push origin main
```

Railway deploys automatically. Verify with:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://founderconsole.ai/api/leads   # expect 405 or 422, NOT 404
curl -s https://founderconsole.ai/pricing | grep -c 'id="ssr-content"'         # expect 1
```

A deploy takes a few minutes. On 20 August one push sat for over 40 minutes
before Railway picked it up, so do not conclude it failed too early.

---

## 4. What is live right now

Production is serving entry bundle `index-gml8iciL.js`; backend uptime is
~16 days, so the last deploy was around 30 August.

- The **August prerender fix is live**: `/tools/runway-calculator`, `/`,
  `/blog`, `/default-alive` and the blog posts render real text inside
  `<div id="root">` before JavaScript loads. 20 of the 37 sitemap URLs do.
- **17 sitemap URLs are still blank until ~890 KB of JS lands**: `/features`,
  `/pricing`, `/about`, `/faq`, `/contact`, `/demo`, `/survival-simulator`,
  `/privacy`, `/terms`, and all eight `/runway/*`. Section 3(f) fixes eleven of
  these; `/features`, `/about`, `/faq`, `/contact`, `/survival-simulator`,
  `/privacy` and `/terms` remain.
- **The geo gate is OFF.** A browser user-agent from a German IP gets `200`.
  Env vars `GEO_RESTRICTION_ENABLED` / `GEO_ALLOWED_COUNTRIES` control it;
  `server/middleware/geoRestrict.ts` fails open by design.
- **Ad crawlers are unblocked.** AdsBot-Google gets `200`.
- Entry bundle is ~888 KB (down from 1,327 KB in August). The 204 KB stylesheet
  is still render-blocking. Neither has been improved since.

---

## 5. Traffic and conversion, measured

Weekly, from PostHog. `devices` is the honest count; `sessions` is roughly
double it because of the bug in section 3(c).

| Week of | Devices | Sessions | Pageviews | Paid pageviews |
|---|---|---|---|---|
| 09 Aug | 21 | 37 | 40 | 6 |
| 16 Aug | 101 | 188 | 211 | 62 |
| 23 Aug | 116 | 240 | 327 | 79 |
| 30 Aug | 65 | 124 | 142 | 60 |
| 06 Sep | 61 | 127 | 173 | 40 |
| 13 Sep | 31 | 48 | 146 | **0** |

**Paid traffic has stopped.** Zero gclid pageviews in the week of 13 September,
down from 40 the week before. Vishesh asked to stop all ads on 20 August and I
could not action it (see section 7). Google's advertiser identity verification
deadline was 2026-09-09 and ads may simply have lapsed. **I have not confirmed
which.** Check the Google Ads account before assuming anything.

Conversion events in the last five weeks — note these **are** now firing, which
was not true in August:

```
signup_view      23 events / 19 devices   last 2026-09-09
cta_click        17 events / 17 devices   last 2026-09-09
calculator_used  11 events / 10 devices   last 2026-09-04
$rageclick        9 events /  4 devices   last 2026-09-08
signup_start      3 events /  3 devices   last 2026-09-08
```

`lead_captured` does not exist in the taxonomy, confirming the email capture in
section 3(e) has never shipped.

Nine rage clicks across four devices is worth someone's attention. Session
replay is enabled; recordings are at
https://us.posthog.com/project/522965/replay

Traffic sources, last 14 days, by device: direct 77, google.com 38,
founderconsole.ai 4, **chatgpt.com 4**, brave 1, duckduckgo 1, venice.ai 1.
The AI-assistant referrals are small but real, and relevant because Vishesh's
stated priority is non-paid growth.

---

## 6. Known open items

Ranked by my judgement of value, not effort.

1. **Ship section 3.** It is written, tested and sitting on the disk.
2. **Prerender the remaining 7 blank pages** — same mechanism, more content.
3. `/ai-cfo` is a Google Ads landing page and renders blank. The "AI CFO for
   Startups" ad's Final URL is `https://founderconsole.ai` (the homepage), not
   `/ai-cfo` — I read that off the ad itself, because the display path says
   `/ai-cfo/free-trial` and is purely cosmetic. I never checked the third ad's
   Final URL.
4. **Two of three Google ads were disapproved** with "Destination not working",
   left over from a geo-block outage I caused in August. Google does not
   re-review on its own; an edit-and-save resubmits. Moot while ads are off.
5. **A negative keyword list was never applied.** In August, "shiba inu burn
   rate" was the account's highest-click search term at AED 106.73, and crypto
   terms took 22% of search spend. The list exists but I do not have a surviving
   path to the file — regenerate from the search terms report.
6. Entry bundle still 888 KB; the 204 KB stylesheet still render-blocking.
7. The calculator pre-fills a fictional company's numbers (`DEFAULTS` in
   `runway-calculator.tsx`).
8. Older audit items, never addressed: silent logout, light-theme billing page
   unreadable, 95 routes with ~15 reachable, 76 unlabelled icon buttons,
   43 non-responsive grids.
9. Cleanup: a test row `VERIFY-RECOMPUTE-1` still exists in Brightloop.

---

## 7. Operating constraints you will hit

These cost me real time. They are properties of the environment, not bugs.

- **The cloud sandbox cannot push to this repo.** The git proxy returns 403 for
  `visheshkhurana/predixen`. The working loop was: edit in the sandbox →
  transfer to `~/Fund-Flow` → Vishesh pushes from his own terminal. If you are
  also running in a sandbox, plan for that; do not promise a push you cannot
  make.
- **Vite inlines `import.meta.env` at build time.** An env var that is not
  present *during the build* is dead-code-eliminated. Setting it at runtime does
  nothing. This is why `VITE_X_PIXEL_ID` must exist before a rebuild.
- **`createRoot()` discards `#root`'s children** on first render — which is what
  makes the prerender approach work without hydration or matching markup. Do not
  "fix" this into `hydrateRoot` without understanding that.
- **`express.static` defaults to `index: "index.html"`.** The `index: false` in
  `server/index.ts` is load-bearing for the SEO prerenderer.
- **`fast-geoip` does not guard reserved ranges** — it answers "JP" for
  `127.0.0.1` and "IT" for `192.168.1.1`. `isPrivateAddress()` in
  `geoRestrict.ts` exists because of that; without it the gate blocks Railway's
  own health checks.
- **AdsBot-Google is a distinct user agent from Googlebot.** A regex matching
  `googlebot` does not match `adsbot-google`. I got this wrong in August and it
  disapproved every ad in the account for roughly three days. There is a named
  regression test for it in `server/tests/geoRestrict.test.ts`.
- **Node's `fetch` sends the user-agent `node`**, which the geo gate treats as a
  bot and lets through. Tests that expect a block must send a real browser UA or
  they pass for the wrong reason.
- **`server/seo-data.ts` holds an abridged copy of the blog content** for the
  prerenderer. It must be updated in parallel with
  `client/src/data/blog-posts.ts`.
- The blog renderer's `renderInline` handles only `[label](href)` and `**bold**`
  — **not** `*italic*`. Asterisks will render literally.
- Google Ads and X Ads web UIs hang on loading spinners frequently. Budget for
  it; do not loop.

---

## 8. Things I got wrong, so you don't repeat them

Stated plainly, because each one cost something.

- I reported three commits as live and verified. They were not — Railway had
  stopped deploying over an unpaid subscription and five commits were stranded.
  I now prove deploys by diffing the served asset hash, never by assuming.
- I shipped a crawler-exemption regex matching `googlebot` but not
  `adsbot-google`. Every ad in the account was disapproved for about three days.
- **Twice** I mistook a Google Ads *display path* for the *Final URL* and drew a
  confident wrong conclusion about a broken destination. The display path is
  cosmetic and need not resolve. Open the ad and read the Final URL field.
- I claimed the geo gate was trivially bypassable via `X-Forwarded-For` more
  confidently than I had actually checked.
- My first prerender test failed all 15 paths because the stub HTML shell had no
  canonical tag to replace. The code was fine; the test was wrong. Check which
  one is broken before changing either.

---

## 9. Strategic context

As of 20 August Vishesh chose, explicitly, to **fix conversion before chasing
more traffic**, and to prefer **work that runs without him** (code, SEO, product
loops) over work requiring a daily posting habit. Section 3 is the first
instalment of that and has not shipped.

The August paid numbers, for calibration: AED 1,900.27 spent over 2–19 August,
78 clicks, 3.31% CTR, AED 24.36 average CPC, **zero conversions**. Since then
`signup_view` and `cta_click` have started firing, so something improved — but
with identities splitting in two, treat every rate as approximate until
section 3(c) ships.
