# Saffron Street Kitchens  Predixen UX/QA Report

**Tester Role**: Founder/CEO of an 18-store fast-casual chain (Series A), paying Predixen customer
**Test Date**: 2026-02-14
**App Version**: Dev (44dba869...replit.dev)
**Company Created**: "Saffron Street Kitchens"  Food/CPG, Series A, INR, Millions

---

## 1. UX TASK OUTCOMES

### C1: First-Time Onboarding
| Step | Result | Notes |
|------|--------|-------|
| Find company name field | PASS | Clear, top of form |
| Select industry | PARTIAL FAIL | No "Restaurant/F&B/QSR" option. Closest is "Food / CPG" which is CPG-oriented. A restaurant founder would hesitate here. |
| Select stage | PASS | "Series A" available |
| Select currency INR | PASS | INR available, helpful "All financial values will be displayed in INR" hint |
| Select Values-In = Millions | PASS | Excellent "Live Preview: You enter 25 -> Predixen reads it as 25,000,000" feature |
| Enter 7 baseline fields | PASS with bug | All fields accept input. BUT field labels show "($)" instead of "()"  critical trust-breaker |
| Verify dashboard shows  | PARTIAL | MRR card shows "38.0M" correctly. But multiple places show "$" (Health Check burn, Goal Tracker, alerts) |
| Time to complete | ~3 minutes | Acceptable for onboarding |

### C2: Navigation + Mental Model
| Task | Result | Time | Notes |
|------|--------|------|-------|
| Find Dashboard | PASS | <2s | Sidebar clearly labeled |
| Find Simulate | PASS | <2s | Sidebar clearly labeled |
| Find Health Check | PASS | <5s | Under FINANCE section  logical |
| Find Data Input | FAIL | >30s | No obvious "Data Input" or "Edit Baseline" link. Settings > Data Input exists but buried. No "Edit" button on dashboard KPI cards. |
| Understand GM/COGS terminology | PARTIAL |  | "Gross Margin %" is standard but a restaurant person thinks "food cost %" first. No tooltip mapping GM to food cost. |

### C3: Edit + Apply/Reset Safety
| Test | Result | Notes |
|------|--------|-------|
| Change GM 68->65 | NOT TESTED | Could not find an in-app "edit baseline" flow without re-running onboarding. No inline edit on Dashboard or Health Check. |
| Apply/Reset buttons | NOT FOUND | No visible "Apply" or "Reset to baseline" mechanism for editing core financial data |
| Change logging | NOT FOUND | No audit trail or "what changed" log visible to the user |

**Verdict**: Editing baseline data requires navigating to Settings > Data Input (buried) or re-onboarding. There is no inline-edit, no undo, no reset-to-baseline. This is a P0 UX gap.

### C4: Output Comprehension
| Test | Result | Notes |
|------|--------|-------|
| Locate runway | PARTIAL | Dashboard says 60.0 mo, Health Check says "Sustainable", Simulate says 999.0 mo. Three different values = P0 trust-breaker. |
| Locate burn | PARTIAL | Dashboard says 0/month (correct direction). Health Check says "$-5" ($ wrong, -5 approximately correct). |
| Consistent across pages | FAIL | Runway: 60 vs Sustainable vs 999. Burn: 0 vs $-5. |
| "Why" explanations | PARTIAL | Health Check shows "How Metrics Are Computed" formulas (good), but no actual computed values inline. Simulation narrative doesn't explain why 13% survival for a profitable company. |
| 30-second comprehension | FAIL | A founder would need >2 minutes to reconcile contradictory runway numbers across pages. |

### C5: Error Prevention
| Test | Result | Notes |
|------|--------|-------|
| Wrong denomination (cash=60000 when M) | NOT TESTED AT ENTRY | No warning appeared during onboarding. No sanity check like "60,000M = 60 Billion  did you mean to enter in Units?" |
| Negative revenue | NOT TESTED | Would need re-onboarding to test input validation |
| GM > 100 | NOT TESTED | Same limitation |
| Empty required fields | PASS | "Please fill in all required fields: Industry, Stage" validation works well |

### C6: Scenario Builder Usability
| Test | Result | Notes |
|------|--------|-------|
| Natural language input | PASS | Accepts restaurant-relevant queries. Ran S1 successfully. |
| Time-phased controls | FAIL | No way to specify "months 1-3 only" visually. Must rely on NL parsing which shows "No changes from baseline" even when changes were described. |
| Scenario comparison | PARTIAL | Before/After cards exist but numbers are unreliable (Revenue @24MO overflows, 0 baseline). |
| Scenario naming | FAIL | All scenarios auto-named "Quick simulation". No way to name or tag them. |

---

## 2. HEURISTIC AUDIT (Nielsen Norman Group 10 Heuristics)

### H1: Visibility of System Status
**Issues:**
- No loading indicator during simulation (15s wait with no progress feedback)  P1
- "Data Confidence: 62%" shown but never explained what would make it 100%  P2
- Simulation "Reproducible" badge is great but needs tooltip  P2

**Severity**: P1 | **Fix**: Add a progress bar or streaming status during simulation. Add tooltip to Data Confidence explaining what data is missing.

### H2: Match Between System and Real World
**Issues:**
- Language is SaaS-centric: "startup", "ARR", "churn", "engineers", "Series A fundraise"  P1
- Quick scenario buttons: "Hire 5 engineers", "Churn hits 5%", "Raise $2M Series A"  irrelevant for restaurants  P1
- Segment Analysis shows "Enterprise", "Starter", "Paid Search", "North America"  completely wrong for a restaurant  P1
- No restaurant-specific KPIs: food cost, labor cost, prime cost, average check, same-store sales  P0

**Severity**: P0 | **Fix**: Industry-aware templates. When industry=Food/CPG, show restaurant KPIs, restaurant scenario buttons ("Food costs rise 5%", "Open 3 new stores"), restaurant segments (Dine-in, Delivery, Takeaway).

### H3: User Control and Freedom
**Issues:**
- No "Edit Baseline" button on Dashboard or anywhere obvious  P0
- No undo after running a simulation  P2
- No "Reset to baseline" for financial data (only for simulation seed)  P1
- Cannot delete or rename saved scenarios  P2

**Severity**: P0 | **Fix**: Add "Edit" icon on each KPI card. Add "Reset All to Baseline" button. Add scenario rename/delete.

### H4: Consistency and Standards
**Issues:**
- Currency symbol inconsistent:  on Dashboard KPI cards, $ on Health Check burn, $ on Goal Tracker, $ on Scenario Comparison, $ on quick buttons  P0
- Runway inconsistent: 60.0 mo (Dashboard) vs "Sustainable" (Health Check) vs 999.0 mo (Simulate KPI bar)  P0
- Burn Rate: 0 (Dashboard) vs "$-5" (Health Check) vs 0 (Simulate KPI bar)  P0
- "mo mo" double suffix in P90 card  P2
- Scale suffix missing on some KPI cards: "38" could be 38 or 38M  P1

**Severity**: P0 | **Fix**: Single formatCurrency() utility. Single calculateRunway() function. Single source of truth for all derived metrics.

### H5: Error Prevention
**Issues:**
- No sanity check on input values (entering cash=60000 when scale=Millions would mean 60 Billion with no warning)  P1
- No guard rails on simulation outputs (Revenue @24MO showing 20-digit number with no cap or warning)  P0
- Gross Margin slider in What-If Explorer goes to 6800%  clearly broken max range  P0
- No validation that computed values make sense (13% survival for profitable company)  P0

**Severity**: P0 | **Fix**: Input validation with sanity warnings. Output anomaly detection. Cap slider ranges to reasonable bounds (0-100% for GM).

### H6: Recognition Rather Than Recall
**Issues:**
- Onboarding Step 2 shows formulas but not computed values  user must calculate mentally  P2
- No reminder of what Values-In scale means after onboarding  P2
- Dashboard doesn't show which metrics are user-entered vs AI-estimated vs derived  partially addressed with badges  P2

**Severity**: P2 | **Fix**: Show computed values live during onboarding. Show persistent "Values in M" reminder. Expand metric source badges.

### H7: Flexibility and Efficiency of Use
**Issues:**
- No keyboard shortcuts for common actions  P2
- No quick-edit inline on Dashboard  P1
- No batch scenario comparison ("run S1-S6 and compare")  P2
- "Adjust Variables Manually" exists in Simulate but is separate from scenario builder  P2

**Severity**: P2 | **Fix**: Inline editing, keyboard shortcuts, batch scenario runs.

### H8: Aesthetic and Minimalist Design
**Issues:**
- Dashboard is dense but well-organized  generally good
- Simulation results page has too many sections (Your Answer, Decision Score, Inputs vs Baseline, Before/After, Sensitivity, What-If, Scenario Comparison)  slightly overwhelming  P2
- Sidebar navigation is clean  good

**Severity**: P2 | Generally acceptable. Consider collapsible sections in simulation results.

### H9: Help Users Recognize, Diagnose, and Recover from Errors
**Issues:**
- "5/10 NO-GO" for a profitable company with no explanation of WHY  P0
- "13% survival probability" with no breakdown of what drives it down  P0
- No "this looks wrong" feedback mechanism for users to flag suspicious outputs  P1
- Alert "Cash Balance Critical < $100K" is stale from a previous company and uses wrong currency  P0

**Severity**: P0 | **Fix**: Every metric and score must have an expandable "Why?" section. Users must be able to flag outputs as wrong.

### H10: Help and Documentation
**Issues:**
- Tutorial mode in Classic Wizard is helpful  good
- "How Your Metrics Are Computed" section in onboarding  good
- No help tooltip on "Founder Mode" toggle  P2
- No documentation on how Monte Carlo simulation works  P2
- No glossary mapping restaurant terms to Predixen terms (food cost = 1-GM, labor cost = payroll/revenue)  P1

**Severity**: P1 | **Fix**: Add tooltips everywhere. Add a glossary. Document the simulation model.

---

## 3. BUGS FOUND (Prioritized)

### P0  Trust-Breaking

| ID | Bug | Where | Expected | Actual |
|----|-----|-------|----------|--------|
| B1 | Currency shows $ instead of  | Onboarding Step 2 labels, Health Check burn, Goal Tracker, Scenario Comparison Cash @24m, Quick buttons |  everywhere | $ in 6+ places |
| B2 | Runway inconsistent across pages | Dashboard vs Health Check vs Simulate | Single consistent value | 60.0 mo vs "Sustainable" vs 999.0 mo |
| B3 | Baseline shows 13% survival / NO-GO for a profitable company | Simulate > Baseline | High survival (company is cash-flow positive) | 5/10 NO-GO, 13% survival |
| B4 | Gross Margin slider max = 6800% | Simulate > What-If Explorer | Max 100% | 6800% |
| B5 | Revenue @24MO = 0 for baseline | Simulate > Before/After | ~912M+ | 0 |
| B6 | Onboarding overwrites existing company | Onboarding flow | Creates new company | Overwrites company ID |
| B7 | Fabricated metrics (NRR 105%, ARPU 253K, Customers 150, Churn 3.2%) | Dashboard and Health Check | N/A for un-entered metrics | Hallucinated values |

### P1  Significant

| ID | Bug | Where | Expected | Actual |
|----|-----|-------|----------|--------|
| B8 | No "Restaurant/F&B" industry option | Onboarding | Restaurant category | Only "Food / CPG" |
| B9 | SaaS-centric quick buttons and segments | Simulate, Dashboard | Industry-relevant suggestions | "Hire engineers", "Churn hits 5%" |
| B10 | "Scenario Inputs vs Baseline" always shows "No changes" | Simulate results | Parsed parameters highlighted | "No changes from baseline" |
| B11 | Growth Rate 0.0% (should be N/A) | Dashboard KPI Health | N/A (1 data point) | 0.0% |
| B12 | Payback 580.5 months | Dashboard KPI Health | N/A or reasonable | 580.5 mo |
| B13 | "mo mo" double suffix | P90 card | "19.0 mo" | "19.0 mo mo" |
| B14 | No inline edit for baseline data | Dashboard | Edit button | Must re-onboard |

### P2  Polish

| ID | Bug | Where | Notes |
|----|-----|-------|-------|
| B15 | Cash on Hand = "$0K" in Scenario Tools | Simulate KPI bar | $ + wrong value |
| B16 | Rev/Emp = 0.05 missing scale suffix | Health Check | Should say 0.05M |
| B17 | Stale alerts from previous company | Dashboard alerts | "$100K threshold" |
| B18 | "Tell us about your startup" copy | Onboarding | Not all businesses are startups |

---

## 4. FEATURE IDEAS  "RESTAURANT METRIC PACK"

### F1: Prime Cost Dashboard Card [P0, Size: M]
**What**: Show Prime Cost (COGS + Labor) and Prime Cost % as a first-class KPI card on Dashboard.
**UI**: New card between Burn Rate and CAC: "Prime Cost 23.6M (62%)" with green/yellow/red indicator vs 60% benchmark.
**Where**: Dashboard, above Segment Analysis.
**Tooltip**: "Prime Cost = Food Cost + Labor Cost. QSR target: 55-60%. Yours: 62%."

### F2: Food Cost % and Labor Cost % KPIs [P0, Size: S]
**What**: Derive food_cost_pct = (1 - GM/100) and labor_cost_pct = payroll/revenue automatically.
**UI**: Two small cards in KPI Health Status: "Food Cost 32% (target: 28-35%)" and "Labor Cost 30% (target: 28-32%)".
**Tooltip**: "Food Cost % = 100% - Gross Margin %. Industry benchmark for QSR: 28-35%."

### F3: Industry-Aware Quick Scenario Buttons [P1, Size: M]
**What**: When industry=Food/CPG or Restaurant, show: "Food costs rise 5%", "Open 3 new stores", "Delivery share grows 10pp", "Minimum wage hike +8%", "Bad monsoon month".
**Where**: Simulate page, replacing "Hire 5 engineers" and "Churn hits 5%".

### F4: Average Check and Transaction Count [P1, Size: M]
**What**: Allow input of monthly transactions. Compute avg_check = revenue / transactions.
**UI**: New input field in onboarding or Data Input: "Monthly Transactions". Dashboard card: "Avg Check 100 | 380K txns/mo".
**Where**: Dashboard, Advanced KPIs section.

### F5: Store-Level Rollup / Filter [P2, Size: L]
**What**: Allow entering per-store revenue. Show same-store sales growth. Filter dashboard by store.
**UI**: New tab "By Store" in Segment Analysis. Table: Store Name | Revenue | Food Cost % | Prime Cost % | Same-Store Growth.
**Where**: Dashboard > Segment Analysis.

### F6: Channel Mix (Dine-in / Delivery / Takeaway) [P1, Size: M]
**What**: Replace SaaS segments (Referral, Paid Search, Enterprise) with restaurant channels.
**UI**: Segment Analysis tabs: "Dine-in (58%)", "Delivery (22%)", "Takeaway (20%)" with revenue and margin per channel.
**Where**: Dashboard > Segment Analysis, replacing current SaaS-centric segments.

### F7: Waste/Shrink Proxy [P2, Size: S]
**What**: Allow input of waste %. Show as KPI. Use in scenario modeling ("What if waste increases 1pp?").
**UI**: Small card: "Waste 2.1% (target: <2.5%)".
**Where**: Dashboard, KPI Health Status.

### F8: POS/Delivery Connectors [P2, Size: L]
**What**: Integrate with Toast, Square, Petpooja (India), Swiggy, Zomato APIs to auto-import daily sales, item mix, delivery orders.
**UI**: Data Sources page, new connector cards.
**Where**: Settings > Integrations.

### F9: Daily Sales View [P2, Size: M]
**What**: Restaurants track daily, not just monthly. Show daily revenue chart with 7-day rolling average.
**UI**: Dashboard card: "Today: 1.3M | 7-day avg: 1.27M | vs last week: +2.4%".
**Where**: Dashboard, top area.

### F10: Menu Mix Levers in Scenario Builder [P2, Size: L]
**What**: Model "What if we remove 3 low-margin items and add 2 high-margin items?" by allowing item-level margin inputs.
**UI**: Advanced panel in Simulate > Adjust Variables Manually.
**Where**: Simulate page.

---

## 5. UI/UX IMPROVEMENTS (Prioritized)

### U1: Fix All Hardcoded $ [P0, Size: S]
Grep codebase for "$" and replace with dynamic currency from company.currency. Affects: onboarding labels, Health Check burn, Goal Tracker, Scenario Comparison, Quick buttons, Alerts.

### U2: Single Source of Truth for Runway [P0, Size: M]
Create one calculateRunway() function. Rules: if netBurn <= 0, return "Sustainable (cash-flow positive)". If netBurn > 0, return cashBalance / netBurn. Use this EVERYWHERE.

### U3: Add Scale Suffix to All KPI Cards [P1, Size: S]
"38" -> "38M". Show the scale on every monetary card. Consider adding "(in Millions)" subtitle.

### U4: Show N/A for Un-entered Metrics [P1, Size: S]
NRR, Churn, Active Customers, ARPU, CAC, LTV  if not user-entered, show "N/A" with "Add this metric ->" CTA. Never fabricate.

### U5: Industry-Aware Copy and Suggestions [P1, Size: M]
Replace "startup" with "business". Replace "engineers" with role-neutral "team members". Replace SaaS segments with industry-relevant ones based on company.industry.

### U6: Add "Edit Baseline" Button on Dashboard [P0, Size: S]
Add pencil icon on each KPI card that opens an inline editor or navigates to Data Input with that field focused.

### U7: Anomaly Guard on Computed Values [P0, Size: M]
If growth rate > 200%, revenue projection > 100x baseline, GM slider > 100%, or survival < 20% for a profitable company  flag with warning: "This looks unusual. Check your inputs."

### U8: Show Computed Values Live in Onboarding [P1, Size: S]
Below the 7 input fields, show: "COGS: 12.2M | Total Expenses: 33.2M | Net Burn: -4.8M (Profitable!) | Runway: Sustainable". Update as user types.

### U9: Explain "Why" for Every Score [P0, Size: M]
The 5/10 NO-GO score and 13% survival need expandable explanations: "Survival is 13% because the Monte Carlo model assumes X growth rate and Y churn, which are not based on your data but on defaults. Your actual cash flow is positive."

### U10: Add Onboarding Step 4 (Review) [P2, Size: S]
Before completing onboarding, show a summary: "Company: Saffron Street Kitchens | Currency:  (Millions) | Revenue: 38M | GM: 68% | ... Confirm?"

---

## 6. FOUNDER VERDICT

### Would I use Predixen weekly?

**Today: No.** Here is why:

1. **Trust is broken on page 1.** The baseline simulation tells me my profitable, cash-generating restaurant chain has "13% survival" and rates it "NO-GO." If the first thing Predixen tells me is wrong and scary, I close the tab. I would never show this to my board.

2. **The numbers contradict each other.** Runway is 60 months on one page, "Sustainable" on another, and 999 months on a third. I cannot trust a tool that cannot agree with itself.

3. **It does not speak my language.** I think in food cost, labor cost, prime cost, daily sales, and same-store growth. Predixen speaks ARR, churn rate, CAC, and NRR. These are SaaS metrics. They mean nothing to me.

4. **I cannot edit my own data easily.** After onboarding, there is no obvious way to update my baseline without diving into Settings. If my numbers change month-to-month (they do  this is a restaurant), I need a fast "update this month's actuals" flow.

### What must change for me to pay 25,000/month?

1. **Fix the math.** A profitable company must not show 13% survival. Period. This is the #1 blocker.

2. **Fix the currency.** Every single "$" on my screen is a trust violation. I set INR. Show INR.

3. **Add a "Restaurant Pack."** Show me food cost %, labor cost %, prime cost, average check, and same-store sales. Let me simulate "food inflation +5%" and "open 3 new stores" with one click.

4. **Let me edit my data inline.** Click a number, change it, see all outputs update. No re-onboarding.

5. **Explain why.** Every score, every survival number, every recommendation must have an expandable "here is how we calculated this" section. If I cannot trace the logic, I cannot trust it.

### What would make me tell other founders about Predixen?

If Predixen became the "restaurant CFO copilot" that:
- Auto-imports my POS data (Petpooja, Toast, Square)
- Shows me daily prime cost and flags when food cost creeps above 33%
- Lets me simulate "What if ingredient prices rise 8% for 3 months?" with a time-phased slider
- Generates a board-ready PDF comparing 3 scenarios with clear recommendations
- And gets the basic math right, with  everywhere

Then I would pay 50,000/month and recommend it to every restaurant founder I know.

---

*Report generated by QA stress test: Saffron Street Kitchens (Synthetic) on Predixen v2026-02-14*
*UX framework: Nielsen Norman Group 10 Usability Heuristics*
*Source: https://www.nngroup.com/articles/ten-usability-heuristics/*
