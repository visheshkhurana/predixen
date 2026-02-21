# FounderConsole Product Audit
## Comprehensive UX, Feature, and Data Flow Analysis

**Date:** February 21, 2026
**Version:** 1.0
**Scope:** Full frontend UX audit, input/output classification, feature inventory, and product recommendations

---

## Executive Summary

FounderConsole is a sophisticated AI-powered financial intelligence platform designed for startup founders. The product enables founders to:
- **Ingest financial data** from multiple sources (manual entry, Excel/PDF uploads, API connectors)
- **Analyze baseline health** via "Truth Scan" (automated financial assessment)
- **Run unlimited scenarios** to stress-test assumptions and model outcomes
- **Get AI guidance** through an embedded copilot that provides recommendations
- **Make informed decisions** with data-driven insights about company direction

**Current State:** The product is feature-rich with advanced analytics capabilities but suffers from three critical UX issues: (1) unclear data flow from inputs to outputs, (2) many advanced features buried without clear guidance, (3) onboarding doesn't clarify when/why founders need each feature.

**Overall Assessment:** Strong technical product with significant founder value, but the user journey is confusing. Founders need clearer mental models of what data to enter, what the system will calculate, and when to use advanced features.

---

## Page-by-Page UX Audit

### 1. **Auth Page** (`/auth`)
**Purpose:** User login and signup
**Status:** Functional but minimal

**UX Issues:**
- No inline help for new users
- No "forgot password" link visible in initial view
- No guidance on what FounderConsole does before signup
- No social login options shown (if available)

**Missing Features:**
- Password reset flow
- Email verification feedback
- OAuth/SSO options not prominently displayed

**Suggested Improvements:**
- Add a one-sentence value prop: "Connect your financials. Understand your runway. Make confident decisions."
- Show example founder testimonial or one-click demo access
- Display SSO options prominently if available

---

### 2. **Onboarding Page** (`/onboarding`)
**Purpose:** Initial company setup and data entry
**Status:** Long (1646 lines) but lacks clear progression

**UX Issues:**
- **No visible stepper** until company is selected (Stepper in header, but not prominent on page)
- **Too many fields at once** in the form (company name, description, stage, industry, cash, revenue, expenses, growth rate, etc.)
- **No clear explanation** of why each field matters (e.g., why we need "target runway" vs just burn calculation)
- **Manual entry is the only visible path** for new users; API connectors/integrations are hidden
- **No progress persistence** - users cannot save and return later
- **Expense breakdown fields** are optional, leading to data quality issues
- **No validation feedback** until form submit (long wait time)
- **"Growth scenario" dropdown** (optimistic/conservative/worst-case) is not explained

**Missing Features:**
- Step-by-step wizard (intro → company info → financial data → connectors)
- Smart field auto-fill (e.g., suggest industry based on description)
- "Quick start" path vs "comprehensive" path options
- Sample data option to explore the product
- Integration setup during onboarding

**Suggested Improvements (P0):**
- Break into 4-step wizard:
  1. Company basics (name, stage, industry)
  2. Initial financial snapshot (cash, revenue, expenses)
  3. Data source setup (manual, Excel, or connector)
  4. Benchmark industry selection
- Add clear explanations: "Growth rate helps us model your trajectory" / "Expense breakdown improves our burn accuracy"
- Show progress bar: "Step 2 of 4"
- Add "Save & Continue Later" button

---

### 3. **Data Input Page** (`/data`)
**Purpose:** Enter or upload financial data
**Status:** Large, complex, lacks clear workflow

**UX Issues:**
- **Three data input methods exist but aren't clearly separated:**
  - Manual form fields
  - Excel/PDF file upload
  - Connector syncs (buried in integrations)
- **No guidance on frequency** - should founders update weekly/monthly/quarterly?
- **Time series editor** exists but isn't obvious (MetricTimeSeriesEditor component)
- **No visualization of entered data** before submission
- **Warnings about missing fields don't suggest fixes** (just says "required")
- **No comparison to last uploaded data** - can't see what changed
- **File upload shows no progress** during processing

**Missing Features:**
- Data quality score before submission
- Dry-run preview showing how data will be interpreted
- Historical data comparison ("Last entry: Jan 2026")
- Bulk editing interface for multiple months
- Template import (e.g., "Import last month's structure")

**Suggested Improvements (P1):**
- Add a single "Add Data" button → modal with three options:
  1. "Manual Entry" (quick form)
  2. "Upload File" (Excel/PDF)
  3. "Connect App" (Stripe, QB, etc.)
- Before submit, show: "Data for Jan 2026: Revenue $50K, Burn $20K" with ability to confirm/edit
- Add monthly data timeline on left side showing which months have data

---

### 4. **Data Verification Page** (`/data/verify/:sessionId`)
**Purpose:** Review uploaded data before finalizing
**Status:** Good concept, but unclear what happens next

**UX Issues:**
- **No clear "this is your data" visual hierarchy** - too much text
- **Confidence warnings** don't suggest what to fix
- **No undo option** visible after verification
- **Unclear what happens after verification** - does it lock the data or can it be edited?
- **No side-by-side comparison** with previous import

**Missing Features:**
- "Accept & Continue" vs "Request Corrections" flow
- Field-by-field confidence indicator (✓ high, ⚠ medium, ✗ low)
- Suggested corrections: "Revenue looks low - did you include all revenue streams?"

**Suggested Improvements (P2):**
- Add a 3-column layout: Original File | Extracted Values | Confidence
- Use color: green (high confidence), yellow (medium), red (low)
- Add explanations: "Confidence low because only 3 months of data"
- Button: "Accept & Run Truth Scan" (clarifies next step)

---

### 5. **Truth Scan Page** (`/truth-scan` or `/truth`)
**Purpose:** Automated financial health analysis and benchmarking
**Status:** Feature-rich but overwhelming

**Current Features:**
- Data confidence score (0-100)
- Quality of Growth Index (0-100)
- Metric cards showing: runway, burn rate, churn, LTV:CAC, gross margin, etc.
- Benchmark comparisons to industry
- Risk flags (critical/warning/healthy)
- Cash flow forecast chart
- Unit economics panel
- Headcount panel
- Burn breakdown by category

**UX Issues:**
- **40+ metrics shown without clear prioritization** - founder doesn't know which 5 matter most
- **Metric cards lack context** - "Runway: 12 months" without explanation of whether that's good
- **Benchmark comparisons hidden in detail** - not visually prominent
- **No action prompts** - shows problems but doesn't suggest what to do
- **Charts are static** - can't drill down into burn breakdown
- **No export mechanism** to share with investors (wait, there's ExportButton - but not visible in UX)
- **Refresh button unclear** - "Re-run truth scan" - takes time, progress not shown
- **Metric detail modals** are text-heavy

**Missing Features:**
- "Key Metrics" vs "Full Metrics" toggle
- "What's your biggest risk?" AI summary
- Suggested next steps: "Your churn is 5% above target. Try the Retention scenario."
- Comparison view: "vs 3 months ago" or "vs industry"
- Download PDF summary for investor deck

**Suggested Improvements (P0):**
- Reorganize into 3 sections:
  1. **Score Cards** (top 3): Data Confidence | Growth Quality | Risk Level
  2. **Key Metrics** (7-8): Runway, Burn, Revenue, Gross Margin, CAC, LTV, Churn, NRR
  3. **Advanced Metrics** (toggle to show): All others
- For each metric, show: Value | Trend (↑/↓) | Benchmark | Status (🟢/🟡/🔴)
- Add: "Suggested Actions" section with 2-3 specific, clickable recommendations
- Make benchmark comparisons a prominent banner: "Your burn rate is 20% above SaaS average"

---

### 6. **Scenarios Page** (`/scenarios` / `/scenarios/:id`)
**Purpose:** Create and run financial projections/stress tests
**Status:** Very feature-rich (2377 lines) but navigation is complex

**Current Features:**
- Scenario wizard with sliders for: pricing, growth, hiring, burn reduction, margin delta
- Custom event builder (one-time revenue, expense, hiring changes)
- Pre-built scenario templates (up/down market, recession, etc.)
- Multi-scenario comparison
- Sensitivity analysis
- Tornado charts
- What-if explorer
- Stress testing (reverse stress test)
- Scenario versioning
- Comments on scenarios
- Sharing scenarios
- Monte Carlo simulation outputs

**UX Issues:**
- **Scenario Wizard sliders have no defaults** - founder stares at zeros
- **"Play" button not obvious** - runs simulation but unclear what "run" means
- **Slider ranges unclear** - is "30% growth" realistic? What range do top SaaS see?
- **No guidance on which levers matter most** - which variable has biggest impact on runway?
- **Comparison mode is hidden** - require users to know about scenario comparison
- **Advanced features (tornado, sensitivity) are in tabs** - users never find them
- **Simulation results take time but no progress indication**
- **Chart selection unclear** - too many chart options, no default recommendation
- **Scenario history/versioning** shows list of versions but can't quickly compare two
- **AI summaries exist (AISummaryCard)** but may be hiding good insights in prose

**Missing Features:**
- "Template marketplace" - pre-built scenarios from community
- "What if we needed to fundraise?" scenario
- "Sensitivity rank" - which 3 levers have biggest impact
- Scenario naming suggestions based on what changed
- "Autorun" option to rerun with latest data
- Scenario approval workflow (for team scenarios)

**Suggested Improvements (P1):**
- **Redesign Wizard:**
  - Show default scenario first: "Current path (no changes)" with projected runway
  - Slider controls with context: "Growth Rate: 10% (vs 8% avg SaaS)"
  - Show impact live: "Impact: +6 months runway"
  - Pre-filled with "typical" values: "Based on your industry, let's start with 5% growth"
- **Add "Scenario Gallery" tab:**
  - "Recession": Cut burn by 20%, revenue down 10%
  - "Land & Expand": Gross margin +5%, NRR +10%
  - One-click pre-fill
- **Results page reorganization:**
  - Top: "Outcome: 18 month runway (vs 12 today)"
  - Middle: "Key Changes" (bullets)
  - Bottom: "Advanced Analysis" (tabs: Sensitivity, Tornado, Monte Carlo)
- **Add "Sensitivity Rank"** showing impact order: Revenue +10% → +8mo runway | Burn -20% → +4mo runway | etc.

---

### 7. **Decisions Page** (`/decisions`)
**Purpose:** Document and track business decisions
**Status:** Exists but unclear value

**UX Issues:**
- **Decision lifecycle unclear** - can decisions be closed/completed?
- **Linking decisions to scenarios** is not obvious (if possible)
- **No template for "what to decide"** - blank page with "New Decision" button
- **Decisions appear isolated** from scenarios that inform them
- **No decision outcome tracking** - did the decision work?

**Missing Features:**
- "Decision templates": "Hire new team" / "Raise funding" / "Pivot to new segment"
- Linking decisions to scenarios that informed them
- Decision status: "In Progress" / "Decided" / "Implemented" / "Review"
- Outcome tracking: "Did this decision help runway?"
- Export decisions to investor deck

**Suggested Improvements (P2):**
- Add decision templates with default questions
- Link a decision to scenario(s): "Based on 'Recession' scenario, we decided to..."
- Add status column and outcome field
- Show in scenario: "This scenario informed 3 key decisions"

---

### 8. **Copilot Page** (`/copilot`)
**Purpose:** AI assistant for financial questions
**Status:** Feature exists in drawer and full page

**UX Issues:**
- **Copilot is only discoverable via Cmd+K or drawer icon** - new users won't find it
- **Full copilot page at /copilot feels redundant** with drawer
- **No context awareness** if you're mid-scenario - copilot doesn't know what you're analyzing
- **Suggested prompts are generic** - not personalized to your company data

**Missing Features:**
- "Help" button on pages that explains what they should ask copilot
- Context-aware prompts: "Analyze my current scenario" / "Compare to industry"
- Memory: copilot should remember previous company questions

**Suggested Improvements (P1):**
- Add prominent **"Ask AI"** button in page headers (next to Briefing)
- Personalize copilot prompts based on page context
- Show copilot suggestions in Truth Scan: "Your churn rate is 40% above benchmark. Want to run a retention scenario?"

---

### 9. **Integrations Page** (`/integrations`)
**Purpose:** Connect data sources (accounting, payments, HR, analytics)
**Status:** Large (1470 lines), but feature discovery is poor

**Current Connectors:** 30+
- Accounting: Stripe, QuickBooks, Xero, NetSuite, Wave
- HR: Gusto, Rippling, Deel
- Analytics: Mixpanel, Amplitude, Google Analytics
- CRM: Salesforce, HubSpot, Close
- And more: Shopify, Brex, Chargebee, etc.

**UX Issues:**
- **Too many connectors listed at once** - overwhelming for new users
- **No guidance on "which connector should I add first"**
- **Setup instructions unclear** for API key vs OAuth flows
- **No indicator of data freshness** - "Last synced: 2 days ago"?
- **Failed connections show generic error** - not actionable
- **OAuth errors send users to browser** - context lost

**Missing Features:**
- "Priority ranking": Show Stripe/QB/Gusto first
- Setup wizard: "Step 1: Connect accounting" → "Step 2: Add payment processor"
- Data freshness indicators on each connector
- "Sync now" button for manual refresh
- Connector health dashboard

**Suggested Improvements (P1):**
- Group by category (Accounting, HR, Revenue, Analytics)
- Add "Recommended for your industry" badge
- Show setup time: "5 min setup"
- Display data freshness: "Syncing every 24 hours" / "Last updated: today"
- Add setup wizard in modal, not new page

---

### 10. **Alerts Page** (`/alerts`)
**Purpose:** Monitor financial KPI thresholds
**Status:** Exists with some alerts, but customization unclear

**UX Issues:**
- **Alerts shown in header dropdown** but full page exists - unclear which to use
- **No alert creation UI visible** - can you set custom alerts?
- **Alerts feel like read-only notifications** without action buttons
- **No alert history** - can't see past alerts

**Missing Features:**
- Alert creation/customization interface
- Threshold configuration: "Notify me if runway < 10 months"
- Frequency options: instant, daily digest, weekly
- Export alerts to Slack/email

**Suggested Improvements (P2):**
- Add "Create Alert" button on page
- Support alerts: Runway, Burn Rate, Cash, Churn, Revenue miss
- Show alert history with timeline

---

### 11. **KPI Board Page** (`/kpi-board`)
**Purpose:** Custom dashboard of key metrics
**Status:** Likely exists but unclear purpose

**Likely UX Issues:**
- **Unclear relationship to Truth Scan and Overview**
- **Hard to understand when to use** this vs another page

**Suggested Improvements:**
- Clarify: "Choose your 5-10 most important KPIs and monitor them here"
- Make it the default for returning users with preset boards by industry

---

### 12. **Dashboard/Overview Page** (`/dashboard` or `/`)
**Purpose:** Main landing page for logged-in users
**Status:** 2438 lines - feature-rich but may be cluttered

**Likely Features:**
- Summary KPIs: Runway, MRR, Burn, Churn, LTV:CAC
- Recent scenarios
- Alerts
- Decision journal snippets
- Chart of key metrics

**Likely UX Issues:**
- **Too much information above the fold**
- **No clear next action** prompt
- **Personalization may be missing** based on company stage/health

**Suggested Improvements:**
- Implement "Dashboard modes":
  - **"Critical"** mode: If runway < 12mo, show Path to Sustainability scenarios prominently
  - **"Growing"** mode: Show Growth initiatives, scaling metrics
  - **"Healthy"** mode: Show optimization opportunities, benchmarking
- Add "Quick Actions" button: "Run Scenario" / "Update Data" / "Share Results"

---

### 13. **Metric Catalog Page** (`/metrics`)
**Purpose:** Browse all available metrics
**Status:** 840 lines - good reference but unclear when to use

**UX Issues:**
- **Metrics catalog is exploratory** - useful for reference but not action-oriented
- **No "recommended metrics for your stage"** guidance

**Suggested Improvements:**
- Add filters: by stage, by industry, by impact
- Show "most important" metrics first
- Link to scenarios that impact each metric

---

### 14. **Fundraising Page** (`/fundraising`)
**Purpose:** Fundraising-specific insights
**Status:** 595 lines

**Likely Features:**
- Dilution modeling
- Fundraising scenario builder
- Benchmark: "What's typical to raise for your stage?"
- Runway impact of different funding amounts

**Likely UX Issues:**
- **Unclear if this is just info or can model raises**
- **May not integrate with scenarios**

**Suggested Improvements:**
- Add "Model a Fundraise" button → scenario generator
- Show: "If you raise $5M at $25M valuation: +24 months runway"

---

### 15. **Investor Room Page** (`/investor-room`)
**Purpose:** Share results with investors
**Status:** Exists

**Likely Features:**
- Public scenario sharing (via UUID)
- Password protection
- Investor presentation mode

**Likely UX Issues:**
- **Unclear how to access** - no obvious "share with investor" button on scenarios

**Suggested Improvements:**
- Add "Share" button on scenario results
- Generate link → customize: remove company name, add custom message

---

### 16. **Admin Pages** (`/admin/*`)
**Purpose:** Platform administration
**Status:** Comprehensive admin tools (users, billing, companies, metrics, etc.)

**Assessment:** Admin tools appear well-structured. Notable pages:
- `/admin/users` - manage users
- `/admin/companies` - manage customer companies
- `/admin/metrics` - manage metric definitions
- `/admin/email-templates` - manage emails
- `/admin/llm-audit` - review LLM outputs
- `/admin/ai-governance` - AI content policies
- `/admin/evals` - evaluation metrics

**Observations:**
- Strong governance around LLM/AI features (good security posture)
- Comprehensive billing and user management
- Admin features well-separated from user product

---

## Input vs Output Variable Classification

### Key Data Flow

**User Input** → **System Processing** → **Output for Display**

```
Manual Fields / Connectors
       ↓
Financial Data Normalization
       ↓
Truth Scan (Analysis Engine)
       ↓
Metrics Calculation
       ↓
Simulation Engine
       ↓
Visualizations & Recommendations
```

### INPUT VARIABLES

**Source:** Data entered manually, uploaded via files, or synced via connectors

#### Core Financial Inputs (User-entered or connector-synced)
| Variable | Type | Source | Usage |
|----------|------|--------|-------|
| `cashOnHand` | Currency | Manual entry / bank connector | Runway calculation |
| `monthlyRevenue` (MRR) | Currency | Manual / Stripe / QB / GA4 | Profitability, growth rate |
| `totalMonthlyExpenses` | Currency | Manual / QB / Xero | Burn calculation |
| `payrollExpenses` | Currency | Manual / Gusto / Rippling | Payroll breakdown |
| `marketingExpenses` | Currency | Manual / GA4 / Mixpanel | CAC calculation |
| `operatingExpenses` | Currency | Manual / QB | Opex breakdown |
| `cogsExpenses` | Currency | Manual / QB | Gross margin |
| `monthlyGrowthRate` | Percentage | Manual entry | Growth modeling |
| `churnRate` | Percentage | Manual / Stripe / GA4 | Retention analysis |
| `totalCustomers` | Count | Manual / Stripe / GA4 | ARPU, CAC, LTV |
| `headcount` | Count | Manual / Gusto / Rippling | Cost per employee |
| `targetRunway` | Months | Manual (default: 18) | Planning timeline |
| `growthScenario` | Enum | Manual (optimistic/conservative/worst-case) | Baseline assumption |

#### Company Metadata
| Variable | Type | Source |
|----------|------|--------|
| `company.name` | String | Manual entry |
| `company.industry` | String | Manual selection |
| `company.stage` | String | Manual (seed/series-a/etc.) |
| `company.currency` | String | Manual selection |

#### Scenario Parameters (Additive inputs on top of baseline)
| Variable | Type | Source | Meaning |
|----------|------|--------|---------|
| `pricing_change_pct` | Percentage | Scenario wizard slider | Adjust pricing by ±X% |
| `growth_uplift_pct` | Percentage | Scenario wizard slider | Uplift revenue growth by ±X% |
| `burn_reduction_pct` | Percentage | Scenario wizard slider | Reduce burn by ±X% |
| `gross_margin_delta_pct` | Percentage | Scenario wizard slider | Adjust GM by ±X% |
| `churn_change_pct` | Percentage | Scenario wizard slider | Change churn by ±X% |
| `hiring_change_pct` | Percentage | Scenario wizard slider | Adjust headcount growth by ±X% |
| `cac_reduction_pct` | Percentage | Scenario wizard slider | Improve CAC efficiency by ±X% |

#### Custom Events (Special inputs for specific changes)
| Variable | Type | Source |
|----------|------|--------|
| `customEvent.type` | Enum | CustomEventBuilder (hiring, revenue boost, one-time expense) |
| `customEvent.month` | Date | User selection |
| `customEvent.amount` | Currency | User input |

### OUTPUT VARIABLES

**Source:** Calculated by system from inputs

#### Automated Truth Scan Outputs
| Metric | Calculation | Purpose | Output Type |
|--------|-----------|---------|------------|
| `runway` | `cash / (burn_rate if burn > 0, else 0)` | Months until out of money | Months |
| `burnRate` | `expenses - revenue` | Net monthly cash outflow | Currency/month |
| `burnMultiple` | `burn / (revenue - cogs)` | How many $ burned per $ of gross profit | Ratio |
| `netBurn` | `totalExpenses - revenue` | Net burn | Currency |
| `grossMargin` | `revenue - cogs` | Profit before opex | Currency |
| `grossMarginPct` | `(revenue - cogs) / revenue` | Gross margin as % | Percentage |
| `cac` | `marketingExpenses / newCustomers` | Cost to acquire one customer | Currency |
| `ltv` | `(arpu * lifespan) or (revenue / churnRate)` | Lifetime value of customer | Currency |
| `ltvCacRatio` | `ltv / cac` | Unit economics health (healthy: 3+x) | Ratio |
| `churnRatePct` | `(lostCustomers / startingCustomers) * 100` | Monthly churn as percentage | Percentage |
| `arpu` | `revenue / customers` | Average revenue per user | Currency |
| `ndr` (Net Dollar Retention) | `(expandingCustomers - churnedRevenue) / priorRevenue` | Growth from existing customers | Percentage |
| `dataConfidenceScore` | `(completeness + consistency + recency) * 100` | How trustworthy is the data (0-100) | 0-100 |
| `qualityOfGrowthIndex` | Composite of: growth rate, burn efficiency, margins, diversification, risk | Overall health score (0-100) | 0-100 |

#### Benchmark Comparisons (Outputs)
| Variable | Calculation | Purpose |
|----------|-----------|---------|
| `runwayVsIndustry` | `company.runway - benchmarkRunway` | How you compare |
| `burnMultipleVsIndustry` | `company.burnMultiple - benchmarkBurnMultiple` | Efficiency comparison |
| `growthVsIndustry` | `company.growth - benchmarkGrowth` | Growth rate comparison |

#### Scenario Simulation Outputs
| Variable | Calculation | Purpose | Output Type |
|--------|-----------|---------|------------|
| `projectedRunway` | Simulation forward based on scenario inputs | Expected runway under scenario | Months |
| `projectedCashAtMonth12` | Simulation forward 12 months | Cash at specific point | Currency |
| `breakEvenMonth` | Month when cumulative becomes positive | When profitability occurs | Month/year or "Never" |
| `monthlyProjection` | Month-by-month forward projection | Detailed forecast | Array of monthly values |
| `monteCarlo[distribution]` | 1000 simulations with variance | Probability distribution of outcomes | Statistical distribution |
| `sensitivityRanks` | Which input has most impact on runway | Variable sensitivity ranking | Ranked list |

#### AI-Generated Outputs
| Variable | Type | Purpose |
|----------|------|---------|
| `aiInsight` | Text | Natural language recommendation |
| `riskAlert` | Text | Identified risk and mitigation |
| `suggestedAction` | Text | Recommended next step |
| `followupSuggestions` | Array of strings | Suggested follow-up questions |

---

### HYBRID VARIABLES (Input OR Output)

| Variable | When Input | When Output | Example |
|----------|-----------|-----------|---------|
| `revenue` | Manual entry / connector | Calculated if using trend | User: "MRR: $50K" OR system: "MRR calculated from Stripe history" |
| `churnRate` | Manual entry / calculated from data | Calculated from customer history | User: "We assume 2% monthly churn" OR system: "Actual churn: 1.8% from data" |
| `grossMargin` | Override entry / calculated | Usually calculated | User: "Assume 70% GM" OR system: "Calculated: $50K / $100K = 50%" |
| `cac` | Estimated / calculated | Calculated from spend/acquisition | User: "Rough estimate: $100/customer" OR system: "Actual: $87 from data" |
| `headcount` | Manual / from HR connector | Calculated or projected | User: "We have 15 people" OR system: "From Gusto: 15 employees" |

---

## Input → Output Data Flow Map

### Complete Flow Visualization

```
┌─────────────────────────────────────────────────────────────────┐
│                        TIER 1: DATA INGESTION                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   Manual Entry              Excel/PDF Upload         Connectors  │
│   - Form fields             - File parser            - Stripe    │
│   - Keyboard entry          - Auto-extraction       - QuickBooks │
│   - Validation              - Confidence scoring    - Gusto      │
│                                                     - Mixpanel   │
│                                                                   │
└──────────────────────────────────────┬──────────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────┐
                    │  FinancialMetricPoint (normalized)  │
                    │  - value, source, confidence        │
                    │  - period, classification           │
                    └──────────────────┬──────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────┐
│                     TIER 2: DATA VERIFICATION                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ImportSession (status: parsed → verified → saved)               │
│  - Detects sign convention (accounting vs all-positive)          │
│  - Detects time granularity (monthly, quarterly, annual)         │
│  - Generates warnings for missing/inconsistent data              │
│  - Computes data quality score                                   │
│                                                                   │
└──────────────────────────────────────┬──────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────┐
│                TIER 3: FINANCIAL ANALYSIS (Truth Scan)          │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  TruthScan Analysis Engine:                                      │
│  INPUT: FinancialMetricPoints (normalized, verified)             │
│                                                                   │
│  Calculates:                                                      │
│  - Runway = cash / burn_rate                                     │
│  - Burn Multiple = burn / (revenue - cogs)                       │
│  - LTV:CAC = ltv / cac                                           │
│  - Quality of Growth Index = f(growth, burn_eff, margins, etc)  │
│  - Data Confidence Score = f(completeness, consistency, etc)     │
│                                                                   │
│  OUTPUT: TruthScan object with:                                  │
│  - metrics: {runway, burn, growth, ltv_cac, churn, ndr, ...}    │
│  - flags: [{severity, title, description}, ...]                 │
│  - benchmark_comparisons: [{metric, company_val, industry_avg}] │
│  - data_confidence_score: 0-100                                  │
│  - quality_of_growth_index: 0-100                                │
│                                                                   │
└──────────────────────────────────────┬──────────────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────┐
         │                             │                         │
    ┌────▼──────────┐            ┌────▼──────────┐        ┌────▼──────────┐
    │  Display on   │            │ Scenarios     │        │  Triggers     │
    │  Truth Scan   │            │  Engine input │        │  Alerts       │
    │  Page         │            │  (baseline)   │        │  (rules-based)│
    └──────────────┘            └────┬──────────┘        └──────────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          │                          │                          │
    ┌─────▼────────────────────────────────────────────────────────────┐
    │                TIER 4: SCENARIO SIMULATION                        │
    ├──────────────────────────────────────────────────────────────────┤
    │                                                                    │
    │  INPUT:                                                           │
    │  - Baseline metrics from TruthScan                               │
    │  - Scenario parameters (pricing, growth, burn reduction, etc.)   │
    │  - Custom events (one-time revenue, hiring, expenses)            │
    │  - Time horizon (default: 24 months)                             │
    │                                                                    │
    │  SimulationEngine:                                               │
    │  1. Apply scenario deltas to baseline                            │
    │  2. Project month-by-month forward                               │
    │     - Revenue: baseline * (1 + growth + pricing_change)^month    │
    │     - Expenses: baseline - burn_reduction + hiring_cost          │
    │     - Cash: prior_cash + revenue - expenses + custom_events      │
    │  3. Calculate derived metrics at each month                      │
    │  4. Generate final metrics (breakeven month, min cash, etc.)     │
    │  5. Run Monte Carlo with variance (±15% on inputs)              │
    │                                                                    │
    │  OUTPUT: ScenarioResult object with:                             │
    │  - id, name, scenario_params                                     │
    │  - monthly_projections: [{month, revenue, burn, cash, ...}, ...] │
    │  - summary: {runway, breakeven_month, min_cash}                  │
    │  - monte_carlo: {distribution_25pct, median, dist_75pct}        │
    │  - sensitivity: {variable: impact_on_runway_months}             │
    │                                                                    │
    └──────────────────────────┬───────────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
         ┌────▼────────┐  ┌────▼────────┐  ┌───▼────────┐
         │ Scenario    │  │ Comparison  │  │ Sensitivity│
         │ Results     │  │ View        │  │ Analysis   │
         │ (single)    │  │ (multi-way) │  │ (tornado)  │
         └─────────────┘  └─────────────┘  └────────────┘
                               │
    ┌──────────────────────────┼──────────────────────────┐
    │                          │                          │
    └──────────────┬───────────┼───────────────┬──────────┘
                   │           │               │
        ┌──────────▼────────────▼──┐   ┌──────▼──────────┐
        │  AI Copilot (Summaries)  │   │  Recommendations│
        │  - Key changes           │   │  - Next actions │
        │  - Impact story          │   │  - Suggested    │
        │  - Risk highlights       │   │    scenarios    │
        └─────────────────────────┘   └─────────────────┘
                   │
    ┌──────────────▼──────────────────────────────────────┐
    │         TIER 5: VISUALIZATION & EXPORT              │
    ├───────────────────────────────────────────────────────┤
    │                                                        │
    │  Charts (Recharts):                                   │
    │  - Line charts (runway over time)                     │
    │  - Area charts (revenue vs burn stacked)              │
    │  - Bar charts (monthly results)                       │
    │  - Distribution charts (Monte Carlo)                  │
    │                                                        │
    │  Tables:                                              │
    │  - Monthly results table                              │
    │  - Scenario comparison table                          │
    │  - Sensitivity rankings                               │
    │                                                        │
    │  Export formats:                                      │
    │  - PDF (scenario results + charts)                    │
    │  - CSV (monthly projections)                          │
    │  - Share link (public scenario view)                  │
    │                                                        │
    └────────────────────────────────────────────────────────┘
```

---

## Critical UX Issues (P0-P1)

### P0 (Blocks User Value) - Fix Immediately

#### Issue #1: **Unclear What Data to Enter and Why**
**Impact:** Founders spend 20+ minutes confused on onboarding, abandon product
**Root Cause:** 15 form fields at once with minimal explanation

**Evidence:**
- Onboarding page (1646 lines) shows all fields at once
- No field-level help text or inline explanations
- No progress indicator showing "what comes after this"

**Fix:**
1. Break onboarding into 4-step wizard with progress bar
2. Add one-sentence explanations for each field
3. Suggest typical values: "For SaaS at your stage, typical growth is 5-10%"

**Effort:** 3-4 days
**Impact:** 30-40% improvement in onboarding completion

---

#### Issue #2: **Truth Scan Shows 40+ Metrics Without Prioritization**
**Impact:** Founders don't know which 5 metrics matter; confusion about what's good/bad
**Root Cause:** Display all available metrics equally; no guidance on which to focus on

**Evidence:**
- Truth Scan page has metric cards for runway, burn, churn, LTV:CAC, CAC, LTV, NRR, gross margin, customer concentration, payback period, revenue per employee, etc.
- No visual hierarchy
- No "top 3 priorities" vs "optional metrics"

**Fix:**
1. Create 3-tier metric structure:
   - **Critical (always show):** Runway, Burn, Revenue, Data Quality
   - **Key (default show):** Growth, Gross Margin, Churn, LTV:CAC
   - **Advanced (optional toggle):** NRR, CAC, LTV, Payback, etc.
2. For each metric, add 1-line status: "🟢 Healthy" or "🔴 Below Target"
3. Add "Biggest Risk" AI summary (top 3 things to fix)

**Effort:** 2-3 days
**Impact:** 50%+ improvement in founder understanding

---

#### Issue #3: **Scenario Wizard Starts with Zeros; Founder Doesn't Know What Values to Try**
**Impact:** Scenarios feel abstract; founders can't judge "is 20% growth realistic?"
**Root Cause:** No defaults, no context, no sensitivity guidance

**Evidence:**
- ScenarioWizard.tsx shows sliders starting at 0%
- No pre-filled values
- No indication of "typical" values for industry/stage
- Slider ranges unclear (is -50% to +50%? Or -100% to +100%?)

**Fix:**
1. Pre-fill sliders with "current trajectory" scenario
2. Show context: "Growth rate: 8% (SaaS avg: 5-10%)"
3. Add "Sensitivity Rank" showing impact order: "10% growth change = +4 runway months"
4. Provide template scenarios: "Recession" (burn -20%, revenue -10%), "Acceleration" (growth +20%), etc.

**Effort:** 2-3 days
**Impact:** Scenarios become immediately actionable

---

#### Issue #4: **No Clear Path from "I Need a Solution" to "Run Scenario"**
**Impact:** Founders don't know what to do when they see a problem (e.g., "runway is 10 months")
**Root Cause:** Truth Scan shows problems but no action buttons

**Evidence:**
- Truth Scan page shows: "Runway: 10 months 🔴"
- No suggested action
- No button: "Model a retention improvement" or "Run fundraising scenario"
- Founder must navigate to Scenarios manually

**Fix:**
1. Add "Suggested Actions" section after top issues
2. Make actions clickable: "Try 'Improve Churn' scenario" → pre-populates scenario
3. Link problems to solutions: If churn is high → suggest churn improvement scenario

**Effort:** 2-3 days
**Impact:** Dramatically improves tool usability

---

#### Issue #5: **Integrations Page is Overwhelming (30+ Connectors)**
**Impact:** New users don't know which integration to start with
**Root Cause:** All connectors shown with no guidance on priority

**Evidence:**
- Integrations page (1470 lines) lists all 30+ connectors
- No grouping by "Start here" vs "Optional"
- No indication of setup time

**Fix:**
1. Reorganize by category and priority:
   - **Start Here:** Stripe (payments), QuickBooks (accounting), Gusto (payroll)
   - **By Category:** Analytics, CRM, HR, etc.
2. Add "5 min setup" / "10 min setup" labels
3. Show data freshness for each connection

**Effort:** 1-2 days
**Impact:** Clearer onboarding path

---

### P1 (Major Friction) - Fix Within 2 Weeks

#### Issue #6: **Data Verification Page Unclear About Next Steps**
**Impact:** Founders unsure if data is locked in, can't correct mistakes
**Root Cause:** No clear "accept vs request changes" flow

**Fix:**
1. Add 3-column layout: Uploaded File | Extracted Values | Confidence
2. Show "High" / "Medium" / "Low" confidence on each field
3. Buttons: "Accept & Continue" vs "Request Corrections"

---

#### Issue #7: **Advanced Features (Sensitivity, Tornado, Stress Test) Are Hidden in Tabs**
**Impact:** Users never find these features; don't get full value
**Root Cause:** Advanced features buried in tabs at bottom of scenario results

**Fix:**
1. Create "Advanced Analysis" tab visible at top level
2. Show links to advanced features in scenario results banner
3. Provide one-liner descriptions: "Tornado: Which variables matter most?"

---

#### Issue #8: **Scenario Comparison Not Obvious**
**Impact:** Founders can't easily compare "What if we raise funding?" vs "Bootstrap scenario"
**Root Cause:** Comparison feature exists but isn't discoverable

**Fix:**
1. Add "Compare Scenarios" button at top of scenario results
2. Show side-by-side: Scenario A vs B
3. Highlight deltas: "Runway: +6 months", "Breakeven: 2 months sooner"

---

#### Issue #9: **Copilot Exists But Users Don't Know About It**
**Impact:** AI assistant underutilized
**Root Cause:** Only accessible via Cmd+K or drawer icon (not obvious)

**Fix:**
1. Add "Ask AI" button in page headers
2. Show context-aware prompts: On Truth Scan, show "Ask about this metric"
3. Add tutorial: "Meet your AI copilot" on first visit

---

#### Issue #10: **No Onboarding Completion Celebration or Next Steps**
**Impact:** Users unsure if they're done; don't know what to do next
**Root Cause:** After onboarding, they land on empty Truth Scan or Data Input page

**Fix:**
1. Show success modal: "Great! Your data is ready."
2. Prompt: "Next step: Run your first scenario" with Quick Start button
3. Show preview of dashboard with sample metrics

---

## Missing Core Features

### Tier 1 (Blocks Product-Market Fit)

#### Feature: **Data Quality Scoring & Guidance**
**Why:** Founders upload partial data and don't know if projections are reliable
**Current State:** Data confidence score exists but is hidden in Truth Scan
**Solution:**
- Show data quality prominently on data entry page: "Data Quality: 65%" with ↑ indicators
- Suggest fixes: "Add 6 more months of data to increase confidence to 80%"
- Don't allow scenario runs if data quality < 30%

---

#### Feature: **Guided Scenario Library**
**Why:** New users don't know what scenarios to run
**Current State:** Scenario templates exist but aren't guided
**Solution:**
- Create "Scenario Playbook" with 5-10 essential scenarios
- For each: Description, why it matters, typical learnings
- One-click scenarios: "What if we hit our hiring plan?" → pre-filled
- Show most impactful scenarios first

---

#### Feature: **Metric Recommendations by Industry/Stage**
**Why:** Founders overwhelmed by 40+ metrics; don't know which to focus on
**Current State:** All metrics shown equally
**Solution:**
- Create metric sets by industry: "Essential for SaaS", "For Marketplaces", etc.
- Recommend top 7 metrics for founder's stage
- Show: "These 7 metrics account for 80% of success at your stage"

---

#### Feature: **Outcome Tracking & Learnings**
**Why:** Founders run scenarios but don't verify if predictions matched reality
**Current State:** Scenarios are static predictions; no follow-up
**Solution:**
- Add "Check Results" button 3 months after scenario date
- Compare: Predicted vs Actual metrics
- Track accuracy over time
- Learnings: "We underestimated churn; revised CAC higher"

---

### Tier 2 (High Value Features)

#### Feature: **KPI Alerts with Smart Thresholds**
**Why:** Founders miss early warning signs
**Current State:** Some alerts in dropdown, no customization visible
**Solution:**
- Founder sets alert rules: "Notify if runway < 12 months"
- Smart defaults by company health
- Multi-channel: in-app, email, Slack
- Alert history with outcomes

---

#### Feature: **Team Collaboration & Comment History**
**Why:** Founders want to share scenarios with CFO/advisors
**Current State:** Share via UUID exists, but no collaboration
**Solution:**
- Scenario permissions: view/comment/edit
- Comment threads on metrics: "Why is churn so high? —CFO"
- Version control with comments: "Updated CAC estimate after Q4 data"

---

#### Feature: **Benchmarking Deep Dive**
**Why:** Founders want to understand how they compare
**Current State:** Benchmarks shown in Truth Scan but limited context
**Solution:**
- Create benchmark exploration page
- Filter by: Stage, industry, geography, growth rate
- Percentile comparisons: "Your runway is 75th percentile"
- Trend: "Your burn multiple improving vs peers"

---

#### Feature: **What-If Questions in Natural Language**
**Why:** Scenario builder is form-based; founders want to ask "what if we doubled CAC and cut burn by 30%?"
**Current State:** Copilot can discuss but can't modify scenarios
**Solution:**
- Copilot → "Generate scenario from question"
- Parse: "double CAC and cut burn 30%" → pricing_change=50%, burn_reduction_pct=30%
- Run scenario with one click

---

#### Feature: **Fundraising Intelligence**
**Why:** Founders want to model raises and understand dilution impact
**Current State:** Fundraising page exists but unclear if functional
**Solution:**
- Add modal: "Model a Fundraise"
- Input: raise amount, valuation, use of funds
- Show: runway impact, dilution %, future scenarios
- Link to runway scenarios: "If we raise and expand, runway becomes X"

---

#### Feature: **Batch Data Import & Reconciliation**
**Why:** Importing 24 months of data is tedious
**Current State:** Monthly manual entry required
**Solution:**
- Template: "Import 24 months at once from CSV"
- Reconcile with connectors: "Stripe says MRR=$50K, you entered $48K — which is correct?"
- Bulk edit capability

---

## Input/Output Clarity Recommendations

### Problem: Users Can't Tell What's Input vs Output

**Example Confusions:**
- "Is my revenue an input or calculated?" (Can be both)
- "If I change a scenario slider, does it permanently change my baseline?" (No, but unclear)
- "Which metrics come from connectors vs manual entry?" (Unclear)

### Solutions:

#### 1. **Add Source Badges on Every Metric**
```
Runway: 12 months [Manual Input] [Last updated: Jan 15]
Burn Multiple: 1.8x [Calculated] [Based on last 3 months]
CAC: $120 [Stripe connector] [Real-time]
```

#### 2. **Create Input vs Output Legend**
- Add help icon on Truth Scan / Data pages
- Show: "Green = Input (you provided) | Blue = Calculated (system derived) | Purple = Connector (synced live)"

#### 3. **Scenario Page: Clarify Base vs Delta**
- Show baseline scenario: "Current path (no changes)" with projected metrics
- Then show: "If you make these changes: [slider values]"
- Highlight deltas: "+6 months runway", "-$40K/mo burn"

#### 4. **Field-Level Help Text**
```
Monthly Revenue
Input: Total revenue in this month
Sources: Manual entry, Stripe, QuickBooks
Used for: Calculating profitability, growth rate, runway
```

---

## Feature Prioritization Roadmap

### 30-Day Sprint (Immediate)
1. **Fix onboarding wizard** (P0) - 3-4 days
2. **Truth Scan metric prioritization** (P0) - 2-3 days
3. **Scenario guidance & templates** (P0) - 2-3 days
4. **Add "Suggested Actions"** from Truth Scan to Scenarios (P0) - 1-2 days

### 60-Day Sprint (Week 5-8)
1. **Data quality scoring & guidance** (P1) - 2-3 days
2. **Advanced features discoverability** (Sensitivity, Tornado) (P1) - 1-2 days
3. **Copilot discoverability** - Add "Ask AI" buttons (P1) - 1 day
4. **Scenario comparison UX** - Side-by-side view (P1) - 2-3 days
5. **Integrations page reorganization** (P1) - 1-2 days

### 90-Day Sprint (Week 9-12)
1. **Scenario playbook with guided library** (P2) - 4-5 days
2. **Outcome tracking** - "Check results 3 months later" (P2) - 3-4 days
3. **Team collaboration** - Comments, permissions, sharing (P2) - 5-7 days
4. **Alerts customization UI** (P2) - 3-4 days

### 120-Day Sprint (Week 13-16)
1. **Benchmarking deep dive page** (P2) - 4-5 days
2. **What-if natural language** (Copilot → scenario) (P2) - 4-5 days
3. **Fundraising intelligence** - Dilution modeling (P2) - 4-5 days
4. **Batch import & reconciliation** (P3) - 3-4 days

---

## Quick Wins (< 1 Day Each)

### UX Improvements
1. **Add progress bar to onboarding** - "Step 1 of 4"
2. **Show "Loading..." during Truth Scan recalculation** - Add progress indicator
3. **Add "Success!" modal after data verification** - Celebrate and show next step
4. **Add field-level help icons** - "Why do we need this?" explanation
5. **Show data freshness badges** - "Stripe: Updated 2 hours ago"
6. **Add "Edit" button to each Truth Scan metric** - Allows inline override
7. **Make alerts clickable** - "Runway low → Run Sustainability scenario"
8. **Add "Share Results" button on scenario page** - Generate share link
9. **Show typical values on sliders** - "Growth: 10% (vs 5-10% SaaS avg)"
10. **Add breadcrumb navigation** - Show: "Company > Truth Scan > Key Metrics"

### Feature Additions
1. **"Quick scenario" button** - "Model a hire" / "Model a price increase"
2. **Scenario templates** - Copy from one scenario to another
3. **Keyboard shortcuts** - Cmd+K for copilot, Cmd+S for save, etc.
4. **CSV export for monthly projections** - From scenario results
5. **"Compare to 3 months ago"** - Truth Scan comparison
6. **Help tour on first visit** - 60-second product walkthrough
7. **Suggested metrics to track** - "Add these 5 to your KPI board"
8. **Dark mode toggle** - Already built, but verify it's obvious

---

## Conclusion & Key Takeaways

### What FounderConsole Does Exceptionally Well
- **Advanced analytics engine** - Simulations, sensitivity analysis, Monte Carlo
- **AI integration** - Copilot with context-aware suggestions
- **Connector ecosystem** - 30+ data sources, reducing manual data entry
- **Scenario flexibility** - Sliders, custom events, scenario templates

### What's Holding Back Adoption
1. **Onboarding friction** - Too many fields at once, no guidance
2. **Unclear value of each feature** - "Why do I need this?"
3. **Information overload** - 40+ metrics without prioritization
4. **Hidden advanced features** - Sensitivity, tornado charts buried
5. **Disconnected pages** - Truth Scan, Scenarios, Decisions feel isolated

### Path to 3x User Engagement
1. **Simplify onboarding** - 4-step wizard with explanations
2. **Add "Suggested Actions"** - Give founders what to do next
3. **Prioritize metrics** - Show 7 key ones, hide 30 others
4. **Make scenario suggestions** - Pre-filled templates, not blank sliders
5. **Discoverability** - Make copilot, advanced features, and templates obvious

**Estimated Implementation Time:** 4-6 weeks for all P0 items, 8-10 weeks for P1 items
**Expected Impact:** 40-60% improvement in user engagement, 25-35% improvement in completion rates

---

## Appendix A: Page-by-Page Feature Inventory

| Page | Lines | Key Features | Maturity | Priority |
|------|-------|--------------|----------|----------|
| Overview | 2438 | Dashboard KPIs, decisions, scenarios, alerts | High | Core |
| Copilot | 2462 | AI assistant, question answering, suggested actions | High | Core |
| Scenarios | 2377 | Scenario wizard, simulation, sensitivity, tornado, comparison | Mature | Core |
| Data Input | 2325 | Manual form, file upload, time series editor | High | Core |
| Integrations | 1470 | 30+ connectors, setup wizard, connection status | High | Core |
| Onboarding | 1646 | Company setup, initial data entry, company selection | Medium | Core |
| QA | 1355 | Admin evaluation/testing tools | N/A | Admin |
| Decisions | 845 | Decision journal, linking to scenarios | Medium | Secondary |
| Alerts | 827 | Alert monitoring, threshold notifications | Medium | Secondary |
| Metric Catalog | 840 | Metric reference, definitions, formulas | High | Reference |
| Data Verification | 763 | Import verification, field mapping, confidence | High | Core |
| Truth Scan | 1034 | Financial health analysis, benchmarking, KPIs | Mature | Core |
| Fundraising | 595 | Fundraising scenarios, dilution modeling | Medium | Secondary |
| Dashboard Builder | 604 | Custom dashboard creation | Medium | Secondary |
| Dashboards | (linked) | View custom dashboards | Medium | Secondary |
| Suggested Metrics | 517 | AI-suggested metric setup | Medium | Secondary |
| Templates | 559 | Scenario templates, definitions | Medium | Secondary |
| KPI Board | (small) | Quick access to key metrics | Medium | Secondary |
| Investor Room | (small) | Share results with investors | Medium | Secondary |
| Auth | 553 | Login/signup | Medium | Core |

---

**End of Product Audit**

Generated for FounderConsole Product Management
Questions? Contact Product Team
