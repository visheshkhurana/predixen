# Rage-click write-up — FounderConsole (PostHog 522965)

**Author:** User Research  
**Date:** 16 Sep 2026 ~03:45 GST  
**Scope:** `$rageclick` last 60 days (Conversion Eng proof + User Research re-query)  
**Correction:** ORG “9 recorded” = **9 rage-click events across 4 sessions / 4 distinct devices**, not 9 separate recordings.

## Executive summary

Founders are rage-clicking in three places: the **runway calculator** (paid Google traffic, 2 sessions / 5 events), **post-Google-auth onboarding** (1 session / 3 events), and the **survival-simulator embed CTA** (1 session / 1 event, ChatGPT referral). Element text is missing on 8/9 events; only the embed CTA is labeled. Session 4’s replay TTL was ~3d at proof time — watch expiry. Do **not** claim `lead_captured` works (0/0 over 90d).

## Sessions (pasteable)

| # | Session ID | When (UTC) | Path | Rage events | Source | Duration | Replay |
|---|------------|------------|------|-------------|--------|----------|--------|
| 1 | `01a08122-0d38-7eab-9dc6-7625e18e89ee` | 8 Sep 13:08–13:49 | `/onboarding` (via `/auth/callback`) | 3 | Google accounts referrer | 2479s (active ~296s); 93 clicks; 2 console errors | [replay](https://us.posthog.com/project/522965/replay/01a08122-0d38-7eab-9dc6-7625e18e89ee) |
| 2 | `01a06c9b-febd-7426-9c7d-0451f46ee435` | 4 Sep 13:29–13:30 | `/tools/runway-calculator` | 3 | Google Ads (`gclid`) | 79s (active ~66s); 25 clicks | [replay](https://us.posthog.com/project/522965/replay/01a06c9b-febd-7426-9c7d-0451f46ee435) |
| 3 | `01a0316e-ea67-71b1-9b64-b9929db94189` | 24 Aug 01:42–01:45 | `/survival-simulator` | 1 | `utm_source=chatgpt.com` | 178s (active ~142s); 42 clicks; 728 keypresses | [replay](https://us.posthog.com/project/522965/replay/01a0316e-ea67-71b1-9b64-b9929db94189) |
| 4 | `01a01a87-a5b1-7fa5-bdd3-d03b91bf441b` | 19 Aug 14:58–15:00 | `/tools/runway-calculator` | 2 | Google Ads (`gclid`) | 138s (active ~73s); 21 clicks; **TTL was ~3d** | [replay](https://us.posthog.com/project/522965/replay/01a01a87-a5b1-7fa5-bdd3-d03b91bf441b) |

All four: Desktop · Chrome. Distinct IDs: 4 (one per session). Devices ≈ sessions for this tiny set.

## Themes (counts)

1. **Runway calculator friction under paid traffic — 2 sessions / 5 events**  
   Both gclid sessions rage on `/tools/runway-calculator` within ~1–2 minutes. No `$el_text`. Hypothesis for Conversion Eng to validate in replay: input controls, CTA, or broken interactive region — not proven until watched.

2. **Onboarding after Google sign-in — 1 session / 3 events**  
   Three rageclicks in ~13s on `/onboarding` immediately after Google OAuth callback. Long recording (~41 min wall / ~5 min active), 2 console errors. Highest severity single session for product pain.

3. **Embed CTA on survival simulator — 1 session / 1 event**  
   Only labeled hit: `$el_text` = **“Embed the runway widget on your site”**. ChatGPT-sourced visitor; heavy typing (728 keypresses) then rage on embed. Suggests interest in embedding vs. completing the sim — watch replay before changing copy/CTA.

## Recommended tickets (observe → decide; no code claimed)

| Priority | Ticket draft | Evidence | Owner |
|----------|--------------|----------|-------|
| P0 | Watch sessions 1–2 end-to-end; file specific UI bug if click target is dead | replays 1–2 | Conversion Eng + User Research |
| P0 | Onboarding first-screen audit post-OAuth (session 1 + console errors) | replay 1 | App Eng / Conversion Eng |
| P1 | Survival-sim embed CTA: clarify affordance vs dead control | replay 3 + el_text | Conversion Eng |
| P1 | Improve rageclick element capture (`$el_text` null on 8/9) | taxonomy | Analytics |
| Standing | Do not claim lead capture; Analytics server-side `lead_captured` | 0/0 90d (Conversion Eng) | Analytics |

## Funnel context (Conversion Eng, 30d — not rates)

`calculator_used` 11 · `signup_view` 22 · `cta_click` 16 · `signup_start` 3. Ads restart remains Vishesh-only.

## Open questions

- What exact control was rage-clicked on calculator and onboarding (element chain missing)?
- Did session 1 complete onboarding or abandon after the rage cluster?
- Session 4 may expire soon under 30d retention — archive findings if still viewable.

## Pasteable evidence (User Research re-query, 16 Sep)

```
Project 522965 · event=$rageclick · last 60d → 9 events / 4 sessions
Paths: /onboarding×3, /tools/runway-calculator×5, /survival-simulator×1
Only labeled element: "Embed the runway widget on your site" (session 3)
Recording metadata fetched via query-session-recordings-list for all 4 IDs
lead_captured: do not claim (Conversion Eng 0/0 90d)
```

