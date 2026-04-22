# Design Audit — founderconsole.ai

**Date:** 2026-04-22
**Scope:** Landing page (quick audit, viewport captures only — full-page blew the 2000px image cap last run)
**Auditor:** Claude + gstack /design-review

---

## Headline Scores

- **Design Score: C+** — solid dark-theme fundamentals, but the hero has a string-concatenation bug and the body is a textbook AI-slop section rhythm.
- **AI Slop Score: D** — hits 5 of the 10 blacklist patterns directly. This reads as "nice Cursor template," not "product with a point of view."

---

## First Impression

The site communicates **"competent fintech dashboard — the screenshot template, not the product."**

I notice **the H1 says "The Flight Simulatorfor Founders"** — no space between "Simulator" and "for". Broken concatenation, rendered 72px, dead center of the hero. First-impression killer.

The first 3 things my eye goes to are: **(1) the giant H1 (good, intended)**, **(2) the gradient purple "for Founders" (pulls attention for the wrong reason — it's where the bug lives)**, **(3) the blue "Start Simulation" CTA (good)**. Hierarchy is working except the gradient is compensating for weak typography by adding color where craft should be.

**One word: template.**

### Trunk test (landing)
- Site ID: PASS (logo + name top-left)
- Page purpose: PARTIAL — "Flight Simulator for Founders" is evocative but the supporting line "Run your startup like a simulation" is filler
- Nav: PASS
- Options at this level: PASS (two CTAs, but see F-007)
- Search: N/A for landing

---

## Inferred Design System

| Dimension | Observed | Flag |
|---|---|---|
| Fonts | Inter + IBM Plex Mono | Inter is on the "generic signal" list. Not a crime, but you have no typographic identity. |
| Colors (accents) | blue `#3C83F6`, purple `#8B5CF6`, green `#10B981`, cyan `#0EA5E9` | 4 accents on a marketing page = color circus |
| Surface | `#121317` background, `rgba(22,24,29,*)` cards | Consistent, good |
| Heading scale | h1 72 / h2 30 / h3 16-18 | **72→30 is a 2.4× jump (not on scale). h3 is inconsistent (16px in "How it works", 18px in "Core capabilities")** |
| Page height | 6019px | Long. 7+ sections. Every section same rhythm. |

---

## Findings

### HIGH IMPACT

**F-001 · Broken H1 string concatenation** (Typography)
The H1 renders as "The Flight Simulator**for** Founders" — no space. Looking at the JSX, this is almost certainly two spans with a missing whitespace or `<br>` that collapses. This is the single most visible element on the site and it's visibly broken.
*Fix:* Add a space or `&nbsp;` between the two spans. Verify in DOM: `textContent` should be `"The Flight Simulator for Founders"`, not `"The Flight Simulatorfor Founders"`.

**F-002 · Stat value "18.2" renders as "18 . 2"** (Typography)
In the hero metric card, "18.2" displays with wide gaps around the decimal — looks like `font-variant-numeric: tabular-nums` + `letter-spacing` applied to a period. Reads as "18 . 2 Months Runway", which is visually broken.
*Fix:* Remove letter-spacing from numeric displays, or render the stat without the decimal bug (check for a `.split('.')` with whitespace in between).

**F-003 · AI-slop section rhythm** (AI Slop Pattern #10)
Hero → stat strip → connector chips → 4-step icon-in-blue-circle grid → 4-card feature grid → stats → testimonials → pricing → FAQ → CTA. This is the exact sequence of a generic SaaS starter template. Every section is centered, every section has the same vertical rhythm, every section has a `h2 + subtitle + grid` structure. A human designer would break the rhythm — one section full-bleed, one section asymmetric, one section with a real product screenshot, one section with dense type.
*Fix:* Pick 2 sections to make asymmetric. Put a real product screenshot (actual dashboard, not a decorative stat card) in the hero or right after it. Kill at least one section (the hero stat card duplicates the stats section later).

**F-004 · 4-column icon-in-colored-circle grid** (AI Slop Pattern #2 — direct hit)
The "How it works" section is literally the AI-slop-blacklist-pattern-#2: icon-in-colored-circle + bold title + description, repeated symmetrically. It's the single most recognizable "this was vibe-coded" signal.
*Fix:* Replace with a horizontal flow diagram, a real screenshot sequence, or a single animated demonstration. If you keep a grid, break symmetry: different sizes, one card larger, some with screenshots and some with text.

### MEDIUM IMPACT

**F-005 · Four accent colors fighting on the hero** (Color)
Blue CTA, purple gradient H1, green progress bar (Months Runway), blue progress bar (MoM Growth), purple progress bar (Survival P50). There's no single accent — every stat gets its own color. This is decorative, not semantic.
*Fix:* Pick one accent (the blue you're already using for the CTA). Use neutral gray for the non-primary bars, or use intensity (muted → saturated) instead of hue to differentiate.

**F-006 · Testimonials read as AI-generated** (Content)
"Priya Sharma, Co-founder & CEO, NovaPay" and "Marcus Chen, Founder, DataSync Labs" — stereotype names + invented company names that sound like ChatGPT output. If these are real, add LinkedIn links or logos. If they're placeholders, replace them or remove the section until you have real ones. Fake-sounding social proof is worse than none.
*Fix:* Real quotes with real names + companies that exist + ideally a headshot or company logo. Or delete the section.

**F-007 · Two "Demo" CTAs in hero** (Interaction / Content)
"Watch Demo" (top-right, outlined) and "View Demo" (next to Start Simulation). Same word, two different actions. This is a mindless-click failure — user has to think about which one they want.
*Fix:* Pick one. If both exist, rename — "Watch 2-min video" vs. "Open interactive demo", with visibly different affordances.

**F-008 · Forced line break in hero subcopy** (Typography)
The subcopy "Connect your company data, simulate the future, and get AI-powered decisions." has a forced break before "Run your startup like a simulation." The second sentence reads as an afterthought, and the break isn't doing hierarchy work — just adding vertical space.
*Fix:* Either merge into one sentence, or make the second sentence visually distinct (smaller, italic, or as a tagline under the H1 before the primary subcopy).

**F-009 · H3 size inconsistency** (Typography)
H3 is 16px in "How it works" and 18px in "Core capabilities" — same semantic level, different scale. Pick one.
*Fix:* Standardize H3 at 18px. 16px is body-text territory.

### POLISH

**F-010 · "+29 more" text chip** — replace with fading/overlapping logo row. Text labels for visual content = lazy.
**F-011 · Decorative floating dots across every section** — generic "particles" background. Remove or make them do something (data viz, actual motion tied to scroll).
**F-012 · No `text-wrap: balance` on H1 or H2** — long headings wrap awkwardly on narrow viewports.
**F-013 · Inter as primary display font** — functional but generic. Consider a display typeface for the H1 (Geist, Satoshi, GT America, or something custom) and keep Inter for body.

---

## Quick Wins (under 30 min each)

1. **Fix F-001** (the H1 space) — probably a one-char diff. This alone removes the most visible defect.
2. **Fix F-002** (the "18 . 2" number) — remove letter-spacing on numeric displays.
3. **Kill the decorative dots** (F-011) — delete the background particle layer. Instant cleanup.
4. **Rename one of the Demo CTAs** (F-007) — 30 seconds.

---

## What's Working

- Dark theme is coherent and comfortable, not the "pure black + neon" mistake.
- CTAs have good affordance (solid blue vs. outlined).
- Typography scale within body copy is readable.
- The connector chip row is a nice idea conceptually — just executed lazily.
- No obvious a11y disasters (contrast looks OK in captures, though formal WCAG check not run).

---

## Not Audited (deferred)

- Auth flow, dashboard, and authenticated pages (needs login + cookie import)
- Mobile responsive (skipped to avoid 2000px image cap — `$B responsive` generates tall mosaics)
- Interaction flows (form submits, modal feel)
- Performance (LCP/CLS)
- Codex outside-voice review of source code

If you want any of these next, say which one and I'll target it specifically with viewport-only capture.

---

## PR Summary Line

> Design review found 13 issues on landing. High-impact: broken H1 space (F-001), broken stat "18 . 2" (F-002), AI-slop section rhythm (F-003), 4-column icon-grid pattern (F-004). Design score C+, AI slop score D.
