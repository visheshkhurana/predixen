# CHANGELOG - P0 Bug Fixes

## Date: 2026-02-15

### P0 #1: Health Check Forecast "$24 Quintillion" Fix
**Root Cause:** `revenue_growth_mom` (e.g., 1268.4%) was used as a monthly compound 
multiplier without clamping, causing `(1 + 12.684)^12` exponential explosion.

**Files Changed:**
- `server/truth/truth_scan.py` - Clamped growth_rate to max 100% monthly, added 
  value clamps on projected_revenue and projected_expenses (max 1e12)
- `server/simulation.ts` - Clamped effectiveGrowthRate to [-50%, 100%] before 
  computing monthlyGrowthMultiplier

**Verification:** Run Health Check for PulsePal  forecast should show reasonable 
values (not exceeding billions)

---

### P0 #2: Runway Inconsistency (11.8 / 16.0 / 236.8 months)
**Root Cause:** Dashboard used Monte Carlo P50, store used simple cash/burn, 
Decisions used AI-computed value.

**Files Changed:**
- `client/src/lib/finance.ts` - NEW canonical calculateRunway() function
- `client/src/lib/utils.ts` - Existing calculateRunway() already correct

**Note:** The canonical formula is `cash / (expenses - revenue)`. The Dashboard's 
P50 simulation value is inherently different from the simple formula because it 
includes growth projections. Cross-page parity is improved but P50 will always 
differ from static calculations.

---

### P0 #3: Scale Not Applied ("$520" instead of "$520K")
**Root Cause:** `useCurrency.format()` used `formatCurrencyAbbrev()` which had NO 
scale awareness. Alert thresholds compared raw values against base-unit thresholds.

**Files Changed:**
- `client/src/hooks/useCurrency.ts` - format() now appends scale suffix (K/M/Cr)
- `client/src/pages/overview.tsx` - Cash alert threshold now converts to base units 
  before comparing
- `client/src/lib/money.ts` - NEW canonical money formatting module

**Verification:** All currency values should show "$520K" not "$520". Cash Balance 
Critical alert should NOT fire when cash is $4.5M.

---

### P0 #4: Cross-Company Data Contamination
**Root Cause:** founderStore did not reset company-specific state on company switch. 
Stale financial data from previous company persisted in Zustand store.

**Files Changed:**
- `client/src/store/founderStore.ts` - setCurrentCompany() now resets financial 
  baseline, cash, revenue, expenses, and step state

**Verification:** Switch between companies  scenario table and metrics should 
only show data for the selected company.

---

### P0 #5: Gross Margin 90% Shown as 0.9%
**Root Cause:** Backend sometimes returns GM as decimal (0.90) while frontend 
expects percentage (90). Double-multiplication in trend data generation 
(getValue(m.gross_margin) || 0.65) * 100 when GM was already 90 = 9000%.

**Files Changed:**
- `client/src/pages/truth-scan.tsx` - Added GM normalization (decimal -> percentage)
  in enhancedMetrics useMemo. Fixed trend data generation to detect and handle 
  both decimal and percentage formats.

**Verification:** Health Check should show "Gross Margin: 90.0%" not "0.9%".

---

### P0 #6: AI Briefing States "$19/month Burn" (Should be "$382K/month")
**Root Cause:** `company_context` in decisions.py formatted raw values as 
`${net_burn:,.0f}` without scale context. LLM received "$382" and interpreted 
it literally.

**Files Changed:**
- `server/api/decisions.py` - Added amount_scale detection and scale context to 
  company_context. Burn rate now shows "382K (actual: $382,000)" when scale=THOUSANDS.

**Verification:** Generate new briefing for PulsePal  burn rate should reference 
~$382K/month or ~$330K/month, not $19/month.

---

## New Modules Created

### client/src/lib/money.ts
Canonical money formatting and parsing module. Functions:
- parseInputToBase() / baseToDisplayScale()
- formatScaleValue() / formatBaseToDisplay()
- alertThresholdInBase()
- detectUnitMismatch()
- buildAIMoneyContext()

### client/src/lib/finance.ts
Canonical financial computation module. Functions:
- calculateRunway() / calculateMonthlyBurn() / calculateNetBurnRate()
- clampGrowthRate()
- calculateCashFlowForecast()
- formatRunway()
- normalizeGrossMarginPct()
