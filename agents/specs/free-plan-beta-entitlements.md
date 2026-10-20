# Spec: Free plan beta entitlements (P0)

Owner: App Engineer · Author: Product Lead · Gates: Reviewer -> Data Trust (touches plan/feature gating, roles) -> Release Manager
Source: Bot live QA audit, `/workspace/qa-audit/REPORT.md` (P0-1), 21 Oct 2026.

## Problem (evidence)
- Free signups cannot reach activation. Repro from the audit: sign up, onboard with manual numbers, then
  - `/truth-scan` Refresh Scan -> `POST /api/companies/{id}/truth/run` -> 403 `feature_locked` (`app/core_truth_after_refresh.png`)
  - `/simulate` "Hire 5 engineers" -> `POST /api/scenarios/{id}/simulate` -> 403 (`app/core_sim_result.png`)
  - Copilot locked, UI says "session expired" (`app/core_copilot.png`)
- Cause: `server/core/plans.py` `PLAN_DETAILS[PlanTier.FREE]["features"]` lists only DASHBOARD, BASIC_METRICS, CSV_UPLOAD, MANUAL_DATA_ENTRY. It omits SIMULATIONS, TRUTH_SCAN, COPILOT.
- The same FREE entry already sets `max_simulations_per_month: 3` and `max_copilot_messages_per_month: 10`, and its highlights (billing page) promise "3 simulations / month" and "10 copilot messages / month". The limits exist; the features are not enabled.
- Onboarding steers users to both locked features. The 30-day trial is opt-in, not automatic.

## Decision
During public beta, Free gets `Feature.SIMULATIONS`, `Feature.TRUTH_SCAN` and `Feature.COPILOT` **within the existing limits**: 3 simulations / month and 10 Copilot messages / month, as already in `plans.py`. Not unlimited. Do not add SIMULATION_UNLIMITED / COPILOT_UNLIMITED. No Truth Scan limit is defined in plans.py; do not invent one (see Inconsistencies).

## Explicitly NOT in scope
- Not a pricing change. Prices, the paid Starter/Growth/Scale ($29/$49/$99) plans and the Scale trial stay switched off / unchanged.
- Changing any other plan contents, changing limits, or auto-starting the trial is a Vishesh decision and is out of scope.

## Implementation steps
1. **First**, paste the exact current `plans.py` FREE block (lines as on `main`) into the PR description, so reviewers see limits set but features not enabled.
2. Add the three features to the FREE `features` list. No other plan entry changes.
3. Confirm the existing monthly counters enforce `max_simulations_per_month` and `max_copilot_messages_per_month` for Free; if they do not, enforce them in the same PR.

## Acceptance tests (in the PR, run in CI pytest)
1. Fresh free signup, own manually-entered data: Truth Scan run returns 200 (no 403).
2. Same account: simulation run returns 200 (no 403).
3. Same account: 4th simulation in a calendar month is refused (limit error, not 403 `feature_locked` and not an outage message).
4. Copilot: messages 1-10 accepted, 11th refused.
5. `founder_activated` fires with `is_sample=false` for that account.
6. Existing paid-plan gating unchanged: snapshot test of Starter/Growth/Scale `features` and limits equals current `main`; Free still lacks features it did not get here (e.g. DATA_CONNECTORS, FUNDRAISING_OS).

## Rollout
Single PR, merged by Release Manager after Reviewer and Data Trust pass. Release Manager proves deploy landed with a functional probe: fresh test signup -> Truth Scan 200 and simulation 200 on production. Product Lead re-walks signup -> first simulation after deploy.

## Rollback
Revert the one PR (removes the three features from FREE). No schema change, no data migration; fully reversible.

## Metric
Activation = weekly count of `founder_activated` with `is_sample=false`. No target set here; baseline taken from PostHog the week before deploy.

## Inconsistencies found
- plans.py FREE limits/highlights (3 sims, 10 Copilot) are set, but the features are not in the FREE list -> the billing promise is unreachable.
- `/pricing` says every feature is free during public beta (no card, no trial), while billing copy shows Free as limited (3 sims / 10 Copilot) and many features remain paid-only in plans.py. This spec does not resolve that; reconciling `/pricing` copy vs plan contents is a Vishesh decision.
- No Truth Scan quota exists in plans.py or billing copy.
- FREE says "1 company" but the audit created 4 companies on one free account (P2-10).

## Follow-ups (separate PRs, after this P0)
- P1, App Engineer: onboarding resumes instead of failing on duplicate company name.
- P1, App Engineer: lock errors shown as outages ("engine temporarily unavailable", "session expired") -> show "not on your plan" / limit reached.
- P1, Reliability: 60/min rate limit trips during normal browsing.
- P1, Product decision: hide `/fundraising` until it shows real founder data or a clear "sample data" label (currently unlabelled $850K / 15 investors).
- P1, Modeling & AI: Digital Twin shows wrong numbers; fix with a known-input test.
- P2, App Engineer: Free company limit (1) not enforced; separate PR after the P0.
