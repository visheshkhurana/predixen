# FounderConsole marketing audit — 19 Oct 2026

Read-only. No posts, no outreach, no ad spend, no DNS changes, no pushes to `main`.
Live checks ran 19 Oct 2026 ~17:56–18:05 UTC against `https://founderconsole.ai` with a Googlebot user agent for HTML, plus public DNS and web search. Repo tip at audit time: `06e5d77c` on `origin/main`.

Paid acquisition stays off. The last spend note in the product code is AED 1,900 on 15–19 Aug with zero `signup_view`, `signup_start`, and `cta_click` on the runway calculator (`client/src/pages/runway-calculator.tsx`). That is evidence to leave ads off, and this audit does not recommend turning them back on.

## Top 10 actions

Impact is organic discovery or a cleaner conversion record. Effort is the size of the change, assuming an existing PR counts as already started.

| # | Action | Impact | Effort | Owner |
| --- | --- | --- | --- | --- |
| 1 | Correct the SaaS burn-multiple formula on `/runway/saas`. The live sentence says `net new ARR / net burn`. The bands on the same page, `/tools/burn-multiple`, and `llms.txt` all use `net burn / net new ARR` (lower is better). Source: `client/src/data/runway-industries.ts`. This is the industry page search already associates with FounderConsole. | High | Small | Eng |
| 2 | Return a real 404 for unknown URLs. `/this-page-should-404`, `/runway`, `/feed`, and `/rss` answer **200** with the SPA shell (4,558 bytes), homepage canonical, and `index, follow`. `/blog/does-not-exist-audit` and `/tools/runway` already 404. `/favicon.ico` is the same shell. Open PR [#86](https://github.com/visheshkhurana/predixen/pull/86). | High | Small (PR open) | Eng |
| 3 | Put an in-body link to the runway calculator in the 13 posts that only have the sitewide cite block. Draft PR [#114](https://github.com/visheshkhurana/predixen/pull/114). The cite block on every prerendered page already links `llms.txt` and the calculator. | Medium | Small (PR drafted) | Eng |
| 4 | Fire `calculator_used` on burn, dilution, LTV:CAC, and the survival simulator. Today only the runway calculator and default-alive do. Open PR [#166](https://github.com/visheshkhurana/predixen/pull/166). | Medium | Small (PR open) | Eng |
| 5 | Add the one-field result email to default-alive (the query the site does not rank for) only after the runway form’s `lead_captured` shows up in PostHog 522965. The server emitter exists; the Sep 16 baseline was still 0 events. | Medium | Medium | Eng + Vishesh (PostHog) |
| 6 | Refresh `agents/STATE.md`. It still says 16 Sep 2026 and stops at E9. E10 shipped 15 Sep (`#27` `#28` `#29`) and is live. E11 does not exist in git history, `agents/`, or GitHub search. | Medium for the org, low for traffic | Small | Eng |
| 7 | Point `founderconsole.com` at `founderconsole.ai`, or remove the paused Vercel deployment from the index. Live answer is **503** `DEPLOYMENT_PAUSED`. Search still has a cached page with “500+ Founders in Beta”, “10K+ Scenarios Modeled”, “4.9/5”, and “$2B+ Funding Modeled”. | High for trust | Needs the domain | Vishesh |
| 8 | Align mail auth with Resend. SPF authorizes Google only (`include:_spf.google.com`, `~all`). `resend._domainkey` exists; `google._domainkey` does not. DMARC is `p=quarantine`. Lifecycle mail already sends RFC 8058 one-click unsubscribe. | Medium | DNS | Vishesh |
| 9 | Search Console coverage check. Verification TXT records and a meta tag are published. This audit could not open the property. `site:founderconsole.ai` returned zero rows from the search tool; brand and exact-title queries did return FounderConsole URLs, so the property is the place to see what is actually indexed. | High | Account | Vishesh |
| 10 | Leave paid ads off. Meta pixel `872167299140812` still loads on every marketing page (`MarketingLayout`). X Ads stays inert until `VITE_X_PIXEL_ID` is set. Decide whether the Meta pixel should keep measuring with spend at zero. | Saves money; stops a live collector if you turn it off | Account | Vishesh |

## What is working

- **Prerender is real.** All 51 sitemap URLs returned 200 HTML with one `<h1>`, a unique `<title>`, a meta description, a self-canonical, Open Graph (`og:title`, `og:description`, `og:image`, `og:url`), and `twitter:card=summary_large_image`. JSON-LD on those pages parsed. No duplicate titles among the sitemap URLs.
- **AI crawlers are allowed.** `robots.txt` allows GPTBot, ClaudeBot, PerplexityBot, Google-Extended, and `*`, and disallows `/api/`, `/admin/`, `/auth`, `/onboarding`. Sitemap URL is declared.
- **`llms.txt` is live** (200, last updated 2026-10-14) and shows up in search next to the runway calculator. It states the correct burn-multiple formula and the published bands.
- **`www` redirects.** `https://www.founderconsole.ai/` is a 301 to `https://founderconsole.ai/`.
- **Free-tool cluster is in the sitemap and renders:** `/tools`, `/tools/runway-calculator`, `/tools/burn-multiple`, `/tools/dilution`, `/tools/ltv-cac`, `/default-alive`, `/survival-simulator`, and eight `/runway/{saas,ecommerce,fintech,marketplace,ai,hardware,biotech,devtools}` pages. E10 sibling links and hub links are in the served HTML.
- **Citation block** is appended in `injectSEO` for every route with `bodyContent`, including blog posts. It points at `llms.txt` and the runway calculator.
- **Measurement is wired in code.** GA4 `G-NJKW0TGC4C` is in `client/index.html`. PostHog initializes once from `client/src/lib/posthog.ts` (`capture_pageview: false`, so `App.tsx` owns pageviews). `trackFunnel` sends to gtag, PostHog, and X (X no-ops without a pixel id).
- **Lead path on the two calculators that ask for email.** Runway and survival call `useViewedOnce("lead_form_viewed")`, POST `/api/leads`, then `trackFunnel("lead_captured")`. `server/api/leads.py` also emits `lead_captured` server-side after the row commits.
- **Signup events exist.** `client/src/pages/auth.tsx` fires `signup_view`, `signup_start`, `signup_completed`, and `sign_up`.
- **Lifecycle mail** (`deliver_lifecycle_email`) stamps `List-Unsubscribe` to an HTTPS one-click URL and `List-Unsubscribe-Post`.
- **DMARC is published** at quarantine, and Resend’s DKIM key is in DNS.
- **Customers page is honest.** The live description says early access has not published logos or case studies.
- **Homepage weight is text-first.** Served HTML is 5–14 KB. No `<img>` in the SSR body. Fonts are self-hosted (`client/index.html` comment). The entry bundle is `index-BnDiNL89.js` at 572 KB raw / 179 KB gzip; CSS `index-CC4P4aRS.css` is 209 KB raw / 32 KB gzip. OG image is 1200×630, 141 KB, and is a meta image, not an in-page LCP candidate.

## What is broken or thin

### 1. SEO

**Sitemap vs live.** `sitemap.xml` is 200 `application/xml`, 8,972 bytes, 51 `<loc>`s. Every loc returned 200. `WebFetch` reported a 500 on the sitemap; `curl` did not. Treat the curl result as the live one. `lastmod` is stale on the homepage and several marketing URLs (`2026-03-17`) while `/tools/*` is `2026-10-15` and the two newest posts are `2026-10-14`.

**Pages outside the sitemap that still 200:** `/privacy`, `/terms` (short descriptions, no JSON-LD). `/demo` is in the sitemap and has no JSON-LD.

**Soft 404s.** Unknown paths that are not a missing blog slug or a missing `/tools/` slug fall through to `index.html`:

| URL | Status | What Googlebot receives |
| --- | --- | --- |
| `/this-page-should-404`, `/runway`, `/feed`, `/rss` | 200 | Shell title `FounderConsole - AI Decision Simulator for Founders`, homepage description, canonical `https://founderconsole.ai/`, no `<h1>` |
| `/auth`, `/onboarding` | 200, robots.txt Disallow | Same shell |
| `/blog/does-not-exist-audit`, `/tools/runway` | 404 | Real not-found |
| `/favicon.ico` | 200 `text/html` 4,558 bytes | Same shell. `/favicon.png` is a real 64×64 PNG |

**Titles.** Unique across the 51 sitemap URLs. Short ones that will truncate poorly as the whole title: `/faq` (20 characters), `/about` (22), `/pricing` (24), `/contact` (24), `/demo` (21). No missing titles on prerendered marketing, tool, runway, blog, or `/ai-cfo` pages.

**Canonicals** on prerendered pages match the sitemap URL. The shell’s canonical is always the homepage, which is why a soft 404 consolidates into `/`.

**JSON-LD.** Parsed cleanly everywhere it was present (Organization, SoftwareApplication, FAQPage, WebApplication, Article, BreadcrumbList, CollectionPage, WebPage). Gaps: `/demo`, `/privacy`, `/terms`. Organization `sameAs` includes `https://github.com/founderconsole`, which **404s**.

**Index presence.** Brand query “FounderConsole AI CFO” returned the homepage, `/how-it-works`, `/pricing`, `/ai-cfo`, and `/product`. An exact tool query returned `/tools/runway-calculator`, `/llms.txt`, `/vs/runway-calculator-vs-spreadsheet`, and `/runway/saas`. `site:founderconsole.ai` returned **no rows** from this search tool. That operator is unreliable here; Search Console is the check that matters (action 9).

**Core Web Vitals.** No lab run (no CrUX access, no Lighthouse in this pass). Proxies: HTML is small, the gzip JS entry is ~179 KB plus a deferred PostHog chunk, CSS is render-blocking at ~32 KB gzip, SSR text is inside `#root` so the first paint does not wait on the bundle (`seo-prerender.ts` comment records an older 890 KB bundle and a 21/21 mobile bounce). OG image is fine for cards. `/favicon.ico` returning HTML is a crawl defect, not a CWV one.

### 2. AI search

`llms.txt` is present, linked from the cite block, and itself indexed.

None of these four queries returned a `founderconsole.ai` URL in the result set:

| Query | Who occupied the results |
| --- | --- |
| runway calculator for startups | Pilot, Tooljo, Trezy, Datapile, Fuel3 |
| startup burn multiple | David Sacks, Wall Street Prep, FPARef, HSBC Innovation Banking, Closing Report |
| AI CFO for startups | cfo.ai, Marge, CentSight, Finlens |
| default alive calculator | Simplify, Mercury, Tooljo, Founder Ventures, Eightx |

The site is citable when the query names it. It is absent when the query names the job.

### 3. Content

**Inventory (18 posts, all 200, all in the sitemap).** In-body links below are in `client/src/data/blog-posts.ts`. Every prerendered post also gets the cite block (llms.txt + runway calculator).

| Date | Slug | In-body runway or default-alive link |
| --- | --- | --- |
| 14 Oct 2026 | `what-is-a-good-burn-multiple` | Yes |
| 14 Oct 2026 | `13-week-cash-flow-template` | Yes |
| 10 Aug 2026 | `founderconsole-vs-sturppy-vs-finmark-vs-causal` | Yes |
| 8 Aug 2026 | `startup-fpa-tools-acquired-timeline` | Yes |
| 8 Aug 2026 | `finmark-shut-down-alternative` | Yes |
| 15 Mar 2026 | `how-to-calculate-startup-runway` | No |
| 12 Mar 2026 | `seed-stage-saas-benchmarks-2026` | No |
| 8 Mar 2026 | `best-ai-tools-startup-financial-planning` | No |
| 5 Mar 2026 | `what-if-analysis-for-startups` | No |
| 3 Mar 2026 | `board-deck-30-minutes` | No |
| 28 Feb 2026 | `digital-twin-for-startups` | No |
| 25 Feb 2026 | `ltv-cac-ratio-explained` | No |
| 24 Feb 2026 | `calculate-true-runway` | No |
| 18 Feb 2026 | `monte-carlo-founders-guide` | No |
| 10 Feb 2026 | `cap-table-mistakes` | No |
| 29 Jan 2026 | `timing-series-a` | No |
| 15 Jan 2026 | `data-driven-culture` | No |
| 6 Jan 2026 | `unit-economics-guide` | No |

Freshness: two posts on 14 Oct, three in August, thirteen from January–March. No RSS (`/feed` and `/rss` are soft 200s; `/blog/rss.xml` is 404).

**Claims to fix or source before they get quoted:**

- `/runway/saas` inverts the burn-multiple formula while the bullets above it say “under 2x” and “above 3x”, which only make sense if lower is better. The burn-multiple tool page cites Scale VP and Benchmarkit and says neither publishes a sample size. The SaaS industry page does not.
- `llms.txt` still lists planned prices Starter $29, Growth $49, Scale $99. The live `/pricing` page says every feature is free during public beta and that paid tiers come later. Open PR [#163](https://github.com/visheshkhurana/predixen/pull/163) (“Make FounderConsole fully free”) would move this again.
- Marketing copy says **37 data connectors**. `server/connectors` registers **34** `PROVIDER_ID`s, including generic ones (`rest_api`, `mysql`, `google_sheets`).
- `seed-stage-saas-benchmarks-2026` says FounderConsole compares you with “anonymized, stage-matched companies in our platform.” The product has an opt-in to contribute anonymized metrics (`CompanySwitcher`). The post reads as if the comparison already exists.
- LinkedIn post from the `founderconsole` company page (3 Mar 2026) says “90% of seed-stage GTM strategies fail” and “I’ve watched 200+ early-stage founders,” with no source. The paused `.com` snapshot adds the four social-proof figures above. The `.ai` customers page does not repeat them.
- Security copy says GDPR compliant and SOC 2 Type II in progress, and says it does not claim SOC 2. That distinction is in the page. The FAQ also says data sits on “SOC2-compliant cloud providers,” which is a host claim, not a FounderConsole certification.

### 4. Conversion path

Landing (`cta_click` at hero, hero-calculator, pricing tiers, footer) → free tool → optional email → `/signup`.

| Step | Runway | Default alive | Survival | Burn / dilution / LTV:CAC |
| --- | --- | --- | --- | --- |
| SSR + signup CTA | Yes | Yes | Yes | Yes |
| `calculator_used` | Yes | Yes | No | No |
| Lead form + `lead_form_viewed` | Yes | No | Yes | No |
| Client `lead_captured` | Yes | No | Yes | No |
| Server `lead_captured` | Yes, on any `/api/leads` create | — | Yes | — |

`lead_form_viewed` goes through `trackEvent` (PostHog only). Capture goes through `trackFunnel` (PostHog + GA4 + X). Server capture uses a hashed `lead:{sha256}` distinct id and does not identify the browser person. Open identity PRs: [#104](https://github.com/visheshkhurana/predixen/pull/104), [#88](https://github.com/visheshkhurana/predixen/pull/88).

**UTM.** Legacy `/runway-calculator` redirects keep the query string (`server/tests/legacy-redirects.test.ts`). Survival’s signup buttons add `utm_source=survival_simulator`. Embed links add `utm_source=embed`. PostHog’s SDK will see UTMs present on the current URL. The lead POST does not send `utm_source` / `gclid`. There is no first-touch store of inbound UTMs onto the lead row. Sep 16 state recorded two runway rage sessions that arrived with `gclid`, from the period ads were on.

**Pixels.** GA4 and PostHog load. Meta pixel is hardcoded in `useMetaPixel` and runs on marketing layout, separate from the env-gated `client/src/lib/metaPixel.ts`. X pixel code is present and inert. CSP still allows `connect.facebook.net` and `static.ads-twitter.com`.

### 5. Off-site

| Surface | What this pass could verify |
| --- | --- |
| `founderconsole.com` | **503** from Vercel, `x-vercel-error: DEPLOYMENT_PAUSED`, body is plain text. A is `216.150.1.1`, NS are GoDaddy (`ns65`/`ns66.domaincontrol.com`). Search still summarizes an old marketing page with the unsourced stats in section 3. |
| `founderconsole.app` | 200. A different product (“The operating system” — cap table, obligations, people). Name collision on brand queries. |
| X / Twitter `@founderconsole` | Declared in `twitter:site`, Organization `sameAs`, and `llms.txt`. Profile fetch returned 403 to this client. Not treated as proof the account is active. |
| LinkedIn `/company/founderconsole` | A company post URL `linkedin.com/posts/founderconsole_…` (3 Mar 2026) is in the index. Company page fetch was not readable from here. |
| GitHub `github.com/founderconsole` | **404.** Still in Organization JSON-LD. The repo that ships the product is `visheshkhurana/predixen`. |
| Product Hunt, G2, Capterra, There’s An AI For That, Crunchbase | No FounderConsole listing in web search. Direct fetches returned 403 (bot wall), which is not a listing. Closest names were FounderPal and Founderl. |
| Backlinks found in the open web | The Offline Network transcript (Vishesh, Shiprocket episode) names Founder Console and `founderconsole.ai` and says early access had about 40–50 people. One LinkedIn post from the company page. One unrelated LinkedIn post uses the hashtag. No directory or editorial links in this pass. |

### 6. Email DNS and unsubscribe

`founderconsole.ai` NS: Cloudflare. MX: Google Workspace (`aspmx.l.google.com` and the four alt records).

| Record | Value observed |
| --- | --- |
| SPF | `v=spf1 include:dc-aa8e722993._spfm.founderconsole.ai ~all` |
| That include | `v=spf1 include:_spf.google.com ~all` |
| DKIM | `resend._domainkey` publishes an RSA key. `google._domainkey` and the usual Google selectors are empty. |
| DMARC | `v=DMARC1; p=quarantine; adkim=r; aspf=r; rua=mailto:dmarc_rua@onsecureserver.net;` |
| BIMI | none |

Resend is the sender in `server/email/service.py`. SPF does not include Resend, so SPF fails soft (`~all`) for those messages. DMARC can still pass on the Resend DKIM signature (relaxed alignment). Mail that leaves through Google has SPF and no DKIM record found here. `~all` is a soft fail, not `-all`.

**List-Unsubscribe in code.** Covered lifecycle, digest, and briefing mail get an HTTPS one-click URL plus `List-Unsubscribe-Post`. Transactional mail (password reset, verification, receipt) skips the header on purpose. The runway result email uses `send_email` with no unsubscribe headers; the visitor asked for that message. `server/email/send_update_v22.py` sets `List-Unsubscribe` to a `mailto:` and also sets `List-Unsubscribe-Post`, which one-click clients will not accept. That file is a historical campaign script, not `deliver_lifecycle_email`.

### 7. Repo marketing state

`agents/STATE.md` header: “updated 16 Sep 2026”. It records E1/E3 folded, E2 closed, E9 as the `/faq` SSR links (`#22`), ads off, and `lead_captured` at 0 in project 522965. It does not mention E10 or E11.

**E10 is shipped and live**, under commit messages `seo(e10):` :

- `#27` `c601ee3d` — typed runway defaults and free-tool links on `/runway/*`
- `#28` `a0081fbc` — sibling links and WebApplication JSON-LD
- `#29` `26e91d7f` — hub links every industry slug

Tests in `server/tests/runway-industry-ssr.test.ts` and `prerender-coverage.test.ts` still name E10.1 / E10.2 / E10.3. Live `/runway/saas` contains the sibling pattern and the inverted formula from the same data file.

**E11:** `git log --grep`, `git log -G 'E11(\.|:| )'`, `git grep` on `HEAD`, and `gh search` for E11 in this repo returned no experiment. Nothing to resume.

**Open PRs that touch SEO or growth** (19 Oct 2026):

| PR | Draft? | What it is |
| --- | --- | --- |
| [#166](https://github.com/visheshkhurana/predixen/pull/166) | No | Noindex share pages, single-source tool titles, `calculator_used` on all free tools |
| [#114](https://github.com/visheshkhurana/predixen/pull/114) | Yes | In-body runway calculator link in the 13 posts that lack one |
| [#111](https://github.com/visheshkhurana/predixen/pull/111) | Yes | Sitemap guard fails on the bad auto-merge file |
| [#105](https://github.com/visheshkhurana/predixen/pull/105) | Yes | IndexNow ping from the sitemap |
| [#86](https://github.com/visheshkhurana/predixen/pull/86) | No | 404 for unknown routes instead of a homepage duplicate |
| [#104](https://github.com/visheshkhurana/predixen/pull/104) | No | One PostHog identity, no duplicate funnel events |
| [#88](https://github.com/visheshkhurana/predixen/pull/88) | Yes | Join server PostHog events to the browser person |
| [#163](https://github.com/visheshkhurana/predixen/pull/163) | No | “Make FounderConsole fully free” — changes the pricing story `llms.txt` still publishes |

Stale `#1`, `#2`, `#3` are still open. STATE already says to ignore them unless Vishesh says otherwise.

## What needs Vishesh

Accounts and decisions this pass could not take:

- **Google Search Console** for `founderconsole.ai`. Verification is already in DNS (two TXT records) and in the homepage meta tag. Coverage, the soft-404 report, and whether `site:` emptiness is real all live there.
- **GA4** property `G-NJKW0TGC4C` and **PostHog** project 522965, to confirm `lead_captured` is no longer zero before anyone adds another lead form.
- **DNS at Cloudflare:** add Resend to SPF (or switch the soft fail once that include is in), publish Google DKIM if Workspace still sends, and confirm the DMARC aggregate mailbox at `onsecureserver.net` is read.
- **`founderconsole.com`:** the Vercel project is paused. Redirect to `.ai`, or accept that the indexed page still carries the unsourced beta stats.
- **`github.com/founderconsole`:** create it, or remove it from Organization `sameAs` and `llms.txt`.
- **X `@founderconsole` and the LinkedIn company page:** confirm they are the accounts you still want cited. This audit did not log in or post.
- **Meta pixel `872167299140812`:** it collects on marketing pages while spend is zero. Turning it off is a measurement choice. Turning ads back on is a separate decision, and the Aug evidence does not support it.
- **Directory listings** (G2, Capterra, Product Hunt, There’s An AI For That) do not exist in public search. Creating them means accounts and a listing in your name. Not done here.
- **Merge call** on `#86`, `#166`, `#114`, `#105`, `#104`. They are the backlog this audit would ship first.

## Method

- `curl` of `robots.txt`, `sitemap.xml`, `llms.txt`, all 51 sitemap URLs, plus probes for privacy, terms, unknown paths, auth, onboarding, www, favicon, and the JS/CSS entry.
- HTML parse for title, h1, description, canonical, robots, Open Graph, Twitter, JSON-LD parse, and asset URLs.
- Public DNS (`dig`) for A/MX/TXT/DKIM/DMARC.
- Web search for the brand, `site:founderconsole.ai`, the four AI-search queries, and directory names.
- Repo read of `agents/STATE.md`, prerender, blog posts, funnel, leads, email lifecycle, and `gh pr list`.
