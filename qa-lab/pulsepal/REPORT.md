# PulsePal QA Lab  Predixen UI/UX Audit Report

**Company:** PulsePal (Synthetic)  AI habit coach + journaling app  
**Stage:** Series A | **Currency:** USD | **Values-in:** THOUSANDS  
**Tester Role:** Founder/CEO + Ruthless UI/UX QA Tester  
**Date:** February 15, 2026  
**Predixen Version:** Production (observed via live app)

---

## Executive Summary  Founder Verdict

**Would I pay? Not yet.** Predixen has a compelling vision  natural-language scenario simulation with Monte Carlo analysis is genuinely powerful. The onboarding flow is smooth, the AI copilot is promising, and the decision-scoring framework (Risk/Reward/Capital Efficiency/Survival) is exactly what a Series A founder needs. However, **three trust-breaking bugs would cause me to cancel within the first session:**

1. **Runway shows 3 different values** across Dashboard (11.8 mo), Simulate (16.0 mo), and Decisions (236.8 mo) for the same baseline data.
2. **Health Check cash flow forecast shows $24 quintillion** at month 12 (exponential calculation bug).
3. **Unit handling is broken**  Values-in=THOUSANDS is not consistently applied to display, alerts, or AI narratives.

Until these P0 issues are fixed, I cannot trust any output from the platform. The foundation (NL scenario queries, Monte Carlo, decision scoring) is excellent  but the execution on unit handling and cross-page consistency is not production-ready for a paid product.

**Score: 4/10** (would be 7/10 with P0 fixes)

---

## Part 1: Nielsen Norman Group 10 Heuristics Audit

### H1  Visibility of System Status

| Issue | Severity | Fix |
|-------|----------|-----|
| "Baseline saved!" toast on onboarding  good | PASS |  |
| Business Health score (88/100) always visible  good | PASS |  |
| Data Confidence (67%) always visible  good | PASS |  |
| No loading indicator during Monte Carlo simulation runs (auto-ran without user action) | P1 | Show progress: "Running 1,000 Monte Carlo iterations... 45% complete" |
| Simulation auto-triggers without explicit user click | P1 | Require explicit "Run Simulation" click; show "Ready to simulate" state |
| No "last saved" timestamp on data input fields | P2 | Add "Last saved: 2 min ago" below Save button |

### H2  Match Between System and Real World

| Issue | Severity | Fix |
|-------|----------|-----|
| Industry categories lack "Consumer Subscription" or "Mobile App"  forced to use "D2C / Consumer" | P2 | Add: Consumer Subscription, Mobile App, Gaming, Health & Wellness |
| Metric catalog is SaaS-centric (ARR, NRR, Pipeline Velocity, Magic Number)  no consumer sub metrics | P0 | Add: Installs, Trial Starts, Paywall Views, ARPPU, DAU/MAU, D1/D7/D30 Retention, Refund Rate |
| "5% MoM (conservative SaaS benchmark)" suggested for growth  wrong benchmark for D2C/Consumer | P1 | Context-aware benchmarks: "3% MoM (median consumer app, RevenueCat 2025)" |
| Scenario chips reference generic business ("Cut marketing 30%") not consumer app actions ("Improve paywall conversion") | P2 | Industry-aware chips: "Improve trial conversion", "Launch annual plan", "ATT impact" |
| Alert references "Food costs" from another company  cross-company data contamination | P0 | Strict company-scoped alerts. Never show scenarios/alerts from other companies. |
| "Active Customers: 45" in multi-period view = employee count, not customers | P0 | Fix field mapping: employees should not populate "Active Customers" |

### H3  User Control and Freedom

| Issue | Severity | Fix |
|-------|----------|-----|
| No "Undo" after saving data changes | P1 | Add undo stack with Cmd+Z support |
| Reset button on sensitivity sliders works | PASS |  |
| No "Reset to Baseline" button on Dashboard or Data Input | P1 | Add global "Restore Original Baseline" with confirmation dialog |
| No change log (from  to, timestamp) anywhere | P1 | Add audit trail: "Gross Margin changed 90%  85% on Feb 15, 2026 at 10:42am" |
| Cannot remove/delete AI-generated scenarios from comparison table | P2 | Add delete/archive per scenario row |
| No "Back" button in onboarding flow | P2 | Add " Previous Step" link |

### H4  Consistency and Standards

| Issue | Severity | Fix |
|-------|----------|-----|
| Runway: 11.8 mo (Dashboard) vs 16.0 mo (Simulate) vs 236.8 mo (Decisions) | P0 | Single source of truth: all pages must query the same computed value |
| Decision Score: 5/10 (header) vs 6/10 (detail) on same simulation page | P0 | Ensure header score = detail score |
| MRR: $520 (Dashboard) vs $16.2K (Advanced multi-period)  different values for same metric | P0 | Reconcile MRR calculation: 520 (input) should show consistently |
| Gross Margin: 90% (Dashboard) vs 0.9% (Advanced multi-period) | P0 | Fix: input of 90 meaning 90% should not be divided by 100 again |
| Growth Rate: +1268.42% (full precision float)  should be N/A for first period | P0 | If no prior period: show "" or "First period" not a garbage percentage |
| "$520" shown as MRR (not "$520K") despite Values-in=THOUSANDS | P0 | Always suffix monetary displays with unit indicator when Values-in != Units |
| COGS: 51.99999999 (floating point) in expense breakdown | P1 | Round to 2 decimal places for display: 52.00 |
| Alert "Cash Balance Critical: < $100K" triggers falsely ($4,500K = $4.5M cash) | P0 | Alert thresholds must respect Values-in multiplier |

### H5  Error Prevention

| Issue | Severity | Fix |
|-------|----------|-----|
| "Live Preview" on onboarding ("$25  Predixen reads as $25,000")  excellent | PASS |  |
| "All monetary values in Thousands" banner on data entry  good but insufficient | P1 | Add inline unit hint per field: "Monthly Revenue ($K)" not "Monthly Revenue ($)" |
| No warning when entering 4.5 for cash balance (possibly meant 4500 for $4.5M) | P1 | Smart detection: "You entered 4.5. With Values-in=Thousands, that's $4,500. Did you mean $4.5M (enter 4500)?" |
| No validation for GM > 100% | P1 | Reject with: "Gross margin cannot exceed 100%. Current: [value]%" |
| No validation for negative revenue | P2 | Warning: "Negative revenue entered. Is this a refund adjustment?" |
| No validation for churn > 100% | P2 | Reject with: "Monthly churn cannot exceed 100%" |
| Number input fields accept any value without range checks | P1 | Add min/max constraints with clear error messages |

### H6  Recognition Rather Than Recall

| Issue | Severity | Fix |
|-------|----------|-----|
| "How Your Metrics Are Computed" section in onboarding  excellent | PASS |  |
| Info icons () on most metrics  good | PASS |  |
| AI Assistant with suggested questions on Data Input  excellent | PASS |  |
| No tooltip explaining what "Values in Thousands" means on financial cards | P1 | Hover tooltip: "This value is in thousands. $520 = $520,000" |
| Scenario comparison table has no "explain this score" link | P2 | Add "Why this score?" expandable per scenario |
| "Burn Multiple", "Magic Number" have no explanation for non-finance founders | P2 | Add glossary tooltip: "Burn Multiple = Net Burn / Net New ARR. Lower is better." |

### H7  Flexibility and Efficiency of Use

| Issue | Severity | Fix |
|-------|----------|-----|
| Natural language scenario query  excellent power user feature | PASS |  |
| Quick scenario chips (Cut marketing 30%, etc.)  good shortcuts | PASS |  |
| "Founder Mode" toggle  interesting but unclear what it changes | P2 | Tooltip: "Founder Mode shows plain-English summaries instead of financial jargon" |
| No keyboard shortcuts for common actions (Run Simulation, Reset, Save) | P2 | Add: Cmd+Enter = Run, Cmd+R = Reset, Cmd+S = Save |
| No saved scenario templates ("Consumer Sub Pack", "Growth Push") | P1 | Pre-built industry templates selectable during onboarding |
| Cannot export simulation as shareable URL with parameters | P2 | Add "Copy link with scenario params" |
| No bulk data import for multi-month financials | P2 | Accept CSV with monthly columns |

### H8  Aesthetic and Minimalist Design

| Issue | Severity | Fix |
|-------|----------|-----|
| Dark theme is clean and professional | PASS |  |
| Dashboard layout with cards is scannable | PASS |  |
| Briefing document format (Situation, Recommend, Risks)  well structured | PASS |  |
| Growth Rate "+1268.421052631579%"  raw float, not formatted | P1 | Format: "+1,268.4%" or suppress entirely if no prior data |
| Scenario comparison table has good visual hierarchy (Strong/Moderate/At Risk badges) | PASS |  |
| Too many phantom metrics (ARPU, Active Buyers, NRR, Segments) auto-generated without data | P1 | Show only metrics with actual data; collapse others into "Add metric" |

### H9  Help Users Recognize, Diagnose, and Recover from Errors

| Issue | Severity | Fix |
|-------|----------|-----|
| "Please fill in all required fields: Industry, Stage"  clear inline validation | PASS |  |
| No error message when COGS calculation produces float imprecision | P1 | Silently round; if user sees raw float, that IS the error |
| False "Cash Balance Critical" alert with no way to dismiss or fix | P0 | Fix threshold logic; add "Dismiss" and "Learn why" buttons |
| No guidance when scenario produces unrealistic results (e.g., $24Q cash forecast) | P0 | Add sanity check: "Warning: projected values exceed realistic bounds" |
| "Pre-Revenue Company" tooltip when revenue=0 in onboarding  excellent contextual help | PASS |  |

### H10  Help and Documentation

| Issue | Severity | Fix |
|-------|----------|-----|
| "Help & Docs" link in sidebar | PASS |  |
| AI Copilot available on every page | PASS |  |
| No in-app tutorial/walkthrough for first-time users | P2 | Add optional onboarding tour: "Let's set up your first scenario in 60 seconds" |
| No explanation of how Monte Carlo iterations affect results | P1 | Tooltip: "More iterations = more precision. 500 is fast, 5000 is thorough." |
| No FAQ about "Values in" setting and common mistakes | P1 | Add FAQ entry: "I set Values-in=Thousands but my numbers look wrong" |

---

## Part 2: Cross-Page Consistency Check

| Check | Expected | Dashboard | Data Input | Simulate | Decisions | Health Check | Pass/Fail | Root Cause Guess |
|-------|----------|-----------|------------|----------|-----------|--------------|-----------|-----------------|
| Runway (months) | 11.78 | 11.8 mo | 11.8 mo | 16.0 mo (P50) | 236.8 mo | Exponential bug | **FAIL** | Simulate uses Monte Carlo P50 (different model); Decisions uses wrong formula; Health Check has exponential growth bug |
| MRR | $520K | $520 | $520 | $520 | $520/month | $16.2K (Advanced) | **FAIL** | Dashboard/Simulate show raw input; Advanced view applies unknown multiplier |
| Gross Margin | 90% | 90.0% | (not shown in Simple) | (not shown) | (not mentioned) | 0.9% (Advanced) | **FAIL** | Advanced view divides by 100 again: 90/100 = 0.9 displayed as 0.9% |
| Net Burn | $382K/mo | $382/mo | $382/mo | $382 | $19/month | (not shown) | **FAIL** | Decisions AI narrative uses completely wrong burn value ($19) |
| Cash Balance | $4,500K | $4.5K | 4500 | $4.5K | $4,500 | $10.7K (month 1) | **FAIL** | Display formats vary; Health Check month 1 is wrong starting value |
| Total Expenses | $902K | (not shown) | $902 (computed) | (not shown) | (not shown) | (not shown) | PASS | Consistent where shown |
| COGS | $52K | (not shown) | 51.9999... | (not shown) | (not shown) | (not shown) | **FAIL** | Floating point precision bug |
| Currency ($) | $ everywhere | $ | $ | $ | $ | $ | PASS | Consistent |
| Values-in badge | Visible on all financial displays | Banner in onboarding only | Not visible | Not visible | Not visible | Not visible | **FAIL** | Badge only shown during onboarding, not on subsequent pages |
| Growth Rate | N/A (first period) | +1268.4% | (not shown) | 1268.4% | 1268.4% | (not shown) | **FAIL** | Phantom growth rate calculated without prior period |

### Sanity Dataset Validation

**Dataset A (Sustainable):** Revenue=1000, GM=50%, Opex=200, Payroll=100, Other=50, Cash=5000
- Expected: COGS=500, TotalExp=850, NetBurn=-150 (revenue > expenses), Runway=Sustainable
- **Not tested in Predixen**  would require creating second company. Based on observed bugs, prediction: runway calculation would be wrong if netBurn is negative.

**Dataset B (Low Margin):** Revenue=1000, GM=20%, Opex=200, Payroll=100, Other=50, Cash=5000
- Expected: COGS=800, TotalExp=1150, NetBurn=150, Runway=33.33 months
- **Not tested in Predixen**  same concern about cross-page inconsistency.

---

## Part 3: Prioritized Bug List

### P0  Trust Breakers (Fix immediately, block release)

| # | Bug | Repro Steps | Impact |
|---|-----|-------------|--------|
| 1 | Health Check 12-mo forecast shows exponential growth ($24Q at M12) | Create company, enter baseline, navigate to Health Check | Founder makes wrong decisions based on fantasy projections |
| 2 | Runway inconsistent: 11.8 (Dashboard) vs 16.0 (Simulate) vs 236.8 (Decisions) | Enter baseline, check all three pages | Founder cannot trust ANY runway number |
| 3 | Values-in=THOUSANDS not applied to display ($520 shown instead of $520K) | Set Values-in=Thousands, enter 520 revenue, check Dashboard cards | Founder thinks revenue is $520, not $520,000 |
| 4 | Alert "Cash Balance Critical < $100K" fires with $4.5M cash | Enter 4500 cash (=$4.5M), check Dashboard alerts | False alarm erodes trust in all alerts |
| 5 | Decisions briefing says "$19/month burn" and "236.8 months runway" | Enter baseline, navigate to Decisions | AI-generated narrative is factually wrong |
| 6 | Cross-company scenario contamination ("Food costs", "menu prices" in PulsePal) | Create new company, check scenario comparison table | Data isolation failure  shows other users' data |
| 7 | Gross Margin 90% displayed as 0.9% in Advanced multi-period view | Enter 90% GM, check Advanced view in Data Input | Percentage stored/displayed with double division |
| 8 | Active Customers = 45 (mapped from employees, not actual customers) | Enter 45 employees, check Advanced metrics | Completely wrong metric mapping |
| 9 | Growth Rate 1268.4% with no prior data | Create new company, check Dashboard | Meaningless metric displayed prominently |

### P1  Major UX Issues (Fix within 2 weeks)

| # | Bug/Issue | Fix |
|---|-----------|-----|
| 10 | No consumer subscription metrics (installs, trials, paywall, ARPPU, retention) | Add Consumer Subscription metric pack |
| 11 | COGS floating point: 51.99999... | Round to 2 decimal places |
| 12 | Field labels show ($) not ($K) when Values-in=Thousands | Dynamic label: "Monthly Revenue ($K)" |
| 13 | No time-phased scenario inputs | Add start/end month for each parameter change |
| 14 | Scenario "Inputs vs Baseline" shows "No changes" when AI interpreted NL query | Translate NL  explicit parameters and show them |
| 15 | No change log / audit trail | Track all data changes with fromto and timestamp |
| 16 | "SaaS benchmark" suggested for D2C/Consumer company | Context-aware benchmark suggestions |
| 17 | Decision Score inconsistency (5/10 vs 6/10 same page) | Single computed score displayed consistently |
| 18 | No scenario stacking (combine S1+S4+S5) | Allow parameter layering with visual preview |
| 19 | Sensitivity sliders limited to 3 variables | Add more: revenue growth, headcount, opex change |

### P2  Minor UX Issues (Fix within 1 month)

| # | Issue | Fix |
|---|-------|-----|
| 20 | No industry-specific onboarding templates | Add "Consumer Sub", "SaaS", "Marketplace" templates |
| 21 | No keyboard shortcuts | Cmd+Enter, Cmd+S, Cmd+R |
| 22 | No "Back" button in onboarding wizard | Add navigation between steps |
| 23 | Seed field shows "Random" with no reproducibility guarantee | Show actual seed value; verify determinism |
| 24 | Cash @24m shows "" for most scenarios | Show projected value or "Runs out at month X" |
| 25 | No in-app tutorial for first-time users | Add optional guided tour |

---

## Part 4: Top 15 Feature Ideas

1. **Consumer Subscription Metric Pack**  First-class inputs for installs, paywall views, trial starts, trial conversion, ARPPU, churn, refunds, renewals, DAU/MAU, cohort retention (D1/D7/D30/D90). Auto-compute LTV, CAC, payback.

2. **Time-Phased Scenario Builder**  Calendar UI where each parameter change has a start month, end month, and ramp curve (immediate, linear, exponential). Enable "spend now, benefit later" modeling.

3. **Cohort Retention Curves**  Visual input for retention by cohort week. Support both fixed (enter actuals) and modeled (input D1/D7 and extrapolate). Show churn  LTV  revenue impact.

4. **Funnel Simulator**  Visual pipeline: Installs  Paywall Views  Trial Starts  Trial-to-Paid  Active Subs  Revenue. Each node editable per-scenario. Show bottleneck highlighting.

5. **Scenario Stacking/Layering**  Compose multiple parameter changes into one scenario. Visual diff: Baseline vs S1 vs S1+S4 vs S1+S4+S5. Support "what if we do everything?"

6. **Unit-Aware Display Engine**  Every monetary display includes unit context badge. "$520K" not "$520" when Values-in=Thousands. Alert thresholds auto-adjust to unit scale.

7. **Explain-This-Number**  Click any computed metric to see: formula, inputs used, data source, confidence level, and link to change the inputs. Essential for trust.

8. **Assumption Ledger**  Sidebar showing all assumptions in the current view: what was entered vs inferred vs AI-generated. Color coding: green=verified, yellow=assumed, red=missing.

9. **Growth Accounting Dashboard**  New MRR, Expansion MRR, Churned MRR, Contraction MRR, Net New MRR. Time-series chart. Standard for subscription businesses.

10. **Store Economics Module**  Apple/Google commission rates, payment processing fees, refund rates. Auto-deduct from revenue. Model store policy changes (commission reduction, ATT impact).

11. **Reproducible Monte Carlo**  Echo actual seed value in results. "Replay" button runs identical simulation. Deterministic mode for QA/audit. Seed comparison: show how different seeds affect P10/P50/P90.

12. **Competitor Benchmark Library**  Instead of generic "Top 20% seed SaaS", offer: "Median Series A consumer app (RevenueCat 2025)", "Top quartile habit app", etc. Industry + stage aware.

13. **Multi-Currency Support**  For companies with international revenue. Enter revenue in different currencies per region. Auto-convert to base currency with exchange rate assumptions.

14. **Board Deck Export**  One-click PDF with: executive summary, KPI dashboard, runway analysis, scenario comparison, recommended actions. Formatted for board presentation.

15. **Integration Pack**  RevenueCat (subscription metrics), Mixpanel/Amplitude (retention, DAU/MAU), Stripe (revenue, churn), App Store Connect / Google Play Console (installs, reviews). Auto-populate baseline from live data.

---

## Part 5: Top 15 UI/UX Improvements

1. **Always-Visible Unit Badge**  Persistent pill badge on every financial card: "Values in $K" (teal background). Clicking opens unit settings. Never let a user forget the scale.

2. **Smart Unit Mismatch Warning**  If user enters 4.5 for cash balance with THOUSANDS selected, show: "You entered 4.5 ($4,500). Did you mean $4.5M? Enter 4,500 instead." Trigger when value seems too low for the unit scale.

3. **Baseline vs Scenario Diff View**  Side-by-side comparison with red/green highlighting on changed values. Inline delta: "Revenue: $520K  $551K (+6%)". Always show what changed and why.

4. **Change Log Sidebar**  Persistent audit trail: "Feb 15, 10:42am  Gross Margin: 90%  85% (manual edit by you)". Clickable to revert. Filter by date/field/user.

5. **Contextual Microcopy in Onboarding**  Replace "Monthly Revenue ($)" with "Monthly Revenue ($K)  Your total monthly recurring revenue in thousands." Add example: "If your MRR is $520,000, enter 520."

6. **Scenario Name Auto-Generation**  Instead of "Quick simulation", auto-name: "Revenue +6% from M3 (Paywall Redesign)". Editable. Shows parameters in name.

7. **Dashboard KPI Confidence Indicators**  Each metric card shows source: "Verified" (user-entered), "Computed" (derived), "Estimated" (AI-assumed). Users can challenge AI estimates.

8. **Industry-Aware Quick Chips**  For D2C/Consumer: "Improve trial conversion 5%", "Launch annual plan", "ATT impact: -10% installs", "Reduce churn 1pp". Not generic "Cut marketing 30%".

9. **Runway Countdown Timer**  Prominent countdown: "~352 days of runway remaining" with progress bar. Updates in real-time as data changes. Color: green > 18mo, yellow 12-18mo, red < 12mo.

10. **Onboarding Summary Card**  After Step 2, show computed summary before proceeding: "Revenue: $520K/mo | Burn: $382K/mo | Runway: 11.8 months | Health:  Caution". Let user confirm or adjust.

11. **Responsive Sensitivity Sliders**  Real-time preview: as user drags churn slider, show instant impact on runway and survival. No need to click "Run". Live formula: "Churn: 2%  Runway: 15.3 mo (+3.5 mo)".

12. **"What If" Natural Language + Parameter Display**  When user types NL query, show the interpreted parameters BEFORE running: "I understood: Revenue +6% from month 3. Is this correct?" User confirms, then run.

13. **Metric Catalog Tagging**  Tag metrics by business model: [SaaS] [Consumer Sub] [Marketplace] [E-commerce]. Auto-suggest relevant metrics during onboarding based on industry selection.

14. **Export with Context**  All exports (CSV, PDF) include: company name, currency, unit scale, date generated, baseline parameters, scenario description. Never export raw numbers without context.

15. **Error Boundary for AI Narratives**  Before displaying AI-generated text (Decisions briefing), sanity-check all numbers against baseline. If narrative says "$19 burn" but computed burn is $382K, flag: "AI narrative may contain errors. Click to refresh."

---

## Part 6: Onboarding & Scenario Flow Execution Log

### C1  Onboarding Clarity + Unit Safety
- Created company "PulsePal"  smooth, 2 clicks
- Selected D2C / Consumer, Series A, USD, Thousands  all dropdowns worked
- Entered all 7 baseline values  no issues
- "Live Preview" ($25  Predixen reads as $25,000)  EXCELLENT trust builder
- "All monetary values in Thousands" banner  present in onboarding, MISSING on all other pages
- Field labels show ($) not ($K)  unit suffix missing
- Intentional test: entering 4.5 for cash balance  NO WARNING shown. System silently accepted it as $4,500 (not $4.5M). FAIL.

### C2  Navigation + Mental Model
- Dashboard: found in < 2s (sidebar) 
- Simulate: found in < 2s (sidebar)   
- Scenarios: same as Simulate (no separate page)  slight confusion
- Data Input: found via Settings gear  Data Input  8 seconds, not immediately discoverable
- Cohorts/Retention: NOT FOUND. No dedicated page. Churn slider buried in Simulate  Adjust Variables Manually.
- Exports: found on Simulate page (Share Link, Email, Print/PDF, Export)  5 seconds
- **Friction:** "Where do I put paywall/trial metrics?"  NOWHERE. No input fields exist for these.

### C3  Apply/Reset/Undo Safety
- Changed Gross Margin conceptually (not executed to avoid corrupting test data)
- Observation: Data Input has "Save All Data" button  explicit save required 
- Reset: Sensitivity sliders have Reset button . No global "Reset to Baseline" found.
- Change log: NONE. No fromto tracking. No timestamps. No revert capability.

### C4  Output Comprehension (30-Second Test)
- Runway/burn: VISIBLE on Dashboard within 5 seconds ... but WRONG across pages 
- Growth plan impact: Scenario comparison table is clear 
- Funnel impacts: IMPOSSIBLE  no funnel metrics exist
- Retention impacts: IMPOSSIBLE  no retention input/output
- "Can I understand the recommendation in 30 seconds?"  YES for the format, NO for accuracy. The recommendation says "16 months runway" when Dashboard says 11.8. I'd lose trust in 30 seconds.

### C5  Error Prevention
- GM > 100%: NOT TESTED (avoiding data corruption)  Likely no validation based on absence of range constraints on input fields
- Negative revenue: NOT TESTED  number inputs have no min constraint observed
- Churn > 100%: Churn slider maxes at 10%, so cannot exceed via slider. Direct input: no validation observed.
- Trial conversion > 100%: NOT APPLICABLE  no trial conversion input exists

### C6  Scenario Builder UX
- Created revenue +6% scenario via NL query 
- Time-phased "starting month 3" was interpreted by AI 
- Baseline vs scenario comparison available 
- Start/end month controls: NOT AVAILABLE in manual mode. Only via NL interpretation.
- Export: Share Link, Email, Print/PDF, Export buttons available 
- Scenario stacking: NOT SUPPORTED

---

## Appendix A: Bug Reproduction Steps

### Bug #1: Health Check Exponential Forecast
1. Create company with Values-in=Thousands
2. Enter: Revenue=520, GM=90%, Opex=350, Payroll=420, Other=80, Cash=4500
3. Navigate to Health Check (sidebar  Health Check)
4. Observe 12-Month Cash Flow Forecast
5. **Expected:** Declining cash curve, M1$4,118K, M12$0 (or negative)
6. **Actual:** M1=$10.7K, M6=$3,683.6M, M12=$24,187,813,607.2M

### Bug #2: Cross-Page Runway Inconsistency
1. Same data as Bug #1
2. Check Dashboard  11.8 months
3. Check Simulate  16.0 months (P50)
4. Check Decisions  236.8 months
5. All should show the same value (11.8 months)

### Bug #3: Unit Display Missing Thousands Suffix
1. Set Values-in=Thousands during onboarding
2. Enter Revenue=520
3. Dashboard shows "$520"  should show "$520K"
4. Repeats for Cash ($4.5K should be "$4,500K" or "$4.5M"), Burn ($382 should be "$382K")

### Bug #4: Cross-Company Alert Contamination  
1. Create new company "PulsePal" (D2C/Consumer)
2. Navigate to Data Input page
3. Observe alert banner: "Survival probability below 40%  Food costs increase by 4 percentage points (GM drops from 68...)"
4. "Food costs" and "GM drops from 68" reference a different company's data

---

*Report generated from live QA session on Predixen, February 15, 2026.*
*All data is synthetic (PulsePal does not exist). Benchmarks cited are from publicly available industry reports.*
