# Predixen QA Lab Report

**Generated**: 2026-02-14 16:12:21
**Duration**: 12.2s
**Monte Carlo**: seed=42, iterations=1000

## Summary

| Metric | Count |
|--------|-------|
| Total Tests | 150 |
| Passed | 150 |
| Failed | 0 |
| Pass Rate | 100.0% |
| Datasets | 15 |
| Scenarios | 8 |

## Baseline Validation

| Dataset | Company | Currency | Scale | COGS | Expenses | Net Burn | Runway | Status |
|---------|---------|----------|-------|------|----------|----------|--------|--------|
| DS01 | FlowForge | USD | UNITS | 11250.0 | 126250.0 | 51250.0 | 11.71 | PASS |
| DS02 | CloudLedger | USD | UNITS | 48000.0 | 388000.0 | -12000.0 | Infinite | PASS |
| DS03 | GlowCart | INR | MILLIONS | 1500.0 | 2800.0 | 300.0 | 6.67 | PASS |
| DS04 | BazaarBridge | INR | MILLIONS | 900.0 | 1750.0 | 550.0 | 5.45 | PASS |
| DS05 | Shadowbox Logistics | INR | MILLIONS | 1905.32 | 2065.32 | -5.68 | Infinite | PASS |
| DS06 | CredPulse | INR | MILLIONS | 122.5 | 522.5 | 172.5 | 5.22 | PASS |
| DS07 | ProtoFab | INR | MILLIONS | 560.0 | 820.0 | 20.0 | 25.0 | PASS |
| DS08 | StudioSprint | INR | MILLIONS | 40.5 | 130.5 | 40.5 | 2.96 | PASS |
| DS09 | ArenaNova | USD | UNITS | 45000.0 | 215000.0 | 65000.0 | 18.46 | PASS |
| DS10 | CareArc Clinics | INR | MILLIONS | 200.0 | 620.0 | 120.0 | 5.0 | PASS |
| DS11 | TutorLoop | INR | MILLIONS | 90.0 | 340.0 | 160.0 | 6.25 | PASS |
| DS12 | ApexExchange | INR | MILLIONS | 100.0 | 800.0 | -200.0 | Infinite | PASS |
| DS13 | ZeroRev Labs | USD | UNITS | 0.0 | 17000.0 | 17000.0 | 4.71 | PASS |
| DS14 | MaxGM Co | USD | UNITS | 0.0 | 40000.0 | -10000.0 | Infinite | PASS |
| DS15 | MinGM Co | USD | UNITS | 50000.0 | 90000.0 | 40000.0 | 7.5 | PASS |

## Scenario Tests

| Dataset | Scenario | Status | Notes |
|---------|----------|--------|-------|
| DS01 | S0 Baseline (identity) | PASS |  |
| DS01 | S1 Pricing Lift (+5% Revenue) | PASS | Directional check passed |
| DS01 | S2 Demand Shock (-15% Revenue, months 1-3, revert) | PASS | Directional check passed |
| DS01 | S3 Cost Optimization (GM +3pp, capped at 100%) | PASS | Directional check passed |
| DS01 | S4 Hiring Wave (Payroll +10%) | PASS | Directional check passed |
| DS01 | S5 Marketing Push (Opex +20%) | PASS | Directional check passed |
| DS01 | S6 Cash Event (Cash -30%) | PASS | Directional check passed |
| DS01 | S7 Mixed Stack (S1+S4+S5 → then Reset) | PASS | Mixed applied + reset verified |
| DS02 | S0 Baseline (identity) | PASS |  |
| DS02 | S1 Pricing Lift (+5% Revenue) | PASS | Directional check passed |
| DS02 | S2 Demand Shock (-15% Revenue, months 1-3, revert) | PASS | Directional check passed |
| DS02 | S3 Cost Optimization (GM +3pp, capped at 100%) | PASS | Directional check passed |
| DS02 | S4 Hiring Wave (Payroll +10%) | PASS | Directional check passed |
| DS02 | S5 Marketing Push (Opex +20%) | PASS | Directional check passed |
| DS02 | S6 Cash Event (Cash -30%) | PASS | Directional check passed |
| DS02 | S7 Mixed Stack (S1+S4+S5 → then Reset) | PASS | Mixed applied + reset verified |
| DS03 | S0 Baseline (identity) | PASS |  |
| DS03 | S1 Pricing Lift (+5% Revenue) | PASS | Directional check passed |
| DS03 | S2 Demand Shock (-15% Revenue, months 1-3, revert) | PASS | Directional check passed |
| DS03 | S3 Cost Optimization (GM +3pp, capped at 100%) | PASS | Directional check passed |
| DS03 | S4 Hiring Wave (Payroll +10%) | PASS | Directional check passed |
| DS03 | S5 Marketing Push (Opex +20%) | PASS | Directional check passed |
| DS03 | S6 Cash Event (Cash -30%) | PASS | Directional check passed |
| DS03 | S7 Mixed Stack (S1+S4+S5 → then Reset) | PASS | Mixed applied + reset verified |
| DS04 | S0 Baseline (identity) | PASS |  |
| DS04 | S1 Pricing Lift (+5% Revenue) | PASS | Directional check passed |
| DS04 | S2 Demand Shock (-15% Revenue, months 1-3, revert) | PASS | Directional check passed |
| DS04 | S3 Cost Optimization (GM +3pp, capped at 100%) | PASS | Directional check passed |
| DS04 | S4 Hiring Wave (Payroll +10%) | PASS | Directional check passed |
| DS04 | S5 Marketing Push (Opex +20%) | PASS | Directional check passed |
| DS04 | S6 Cash Event (Cash -30%) | PASS | Directional check passed |
| DS04 | S7 Mixed Stack (S1+S4+S5 → then Reset) | PASS | Mixed applied + reset verified |
| DS05 | S0 Baseline (identity) | PASS |  |
| DS05 | S1 Pricing Lift (+5% Revenue) | PASS | Directional check passed |
| DS05 | S2 Demand Shock (-15% Revenue, months 1-3, revert) | PASS | Directional check passed |
| DS05 | S3 Cost Optimization (GM +3pp, capped at 100%) | PASS | Directional check passed |
| DS05 | S4 Hiring Wave (Payroll +10%) | PASS | Directional check passed |
| DS05 | S5 Marketing Push (Opex +20%) | PASS | Directional check passed |
| DS05 | S6 Cash Event (Cash -30%) | PASS | Directional check passed |
| DS05 | S7 Mixed Stack (S1+S4+S5 → then Reset) | PASS | Mixed applied + reset verified |
| DS06 | S0 Baseline (identity) | PASS |  |
| DS06 | S1 Pricing Lift (+5% Revenue) | PASS | Directional check passed |
| DS06 | S2 Demand Shock (-15% Revenue, months 1-3, revert) | PASS | Directional check passed |
| DS06 | S3 Cost Optimization (GM +3pp, capped at 100%) | PASS | Directional check passed |
| DS06 | S4 Hiring Wave (Payroll +10%) | PASS | Directional check passed |
| DS06 | S5 Marketing Push (Opex +20%) | PASS | Directional check passed |
| DS06 | S6 Cash Event (Cash -30%) | PASS | Directional check passed |
| DS06 | S7 Mixed Stack (S1+S4+S5 → then Reset) | PASS | Mixed applied + reset verified |
| DS07 | S0 Baseline (identity) | PASS |  |
| DS07 | S1 Pricing Lift (+5% Revenue) | PASS | Directional check passed |
| DS07 | S2 Demand Shock (-15% Revenue, months 1-3, revert) | PASS | Directional check passed |
| DS07 | S3 Cost Optimization (GM +3pp, capped at 100%) | PASS | Directional check passed |
| DS07 | S4 Hiring Wave (Payroll +10%) | PASS | Directional check passed |
| DS07 | S5 Marketing Push (Opex +20%) | PASS | Directional check passed |
| DS07 | S6 Cash Event (Cash -30%) | PASS | Directional check passed |
| DS07 | S7 Mixed Stack (S1+S4+S5 → then Reset) | PASS | Mixed applied + reset verified |
| DS08 | S0 Baseline (identity) | PASS |  |
| DS08 | S1 Pricing Lift (+5% Revenue) | PASS | Directional check passed |
| DS08 | S2 Demand Shock (-15% Revenue, months 1-3, revert) | PASS | Directional check passed |
| DS08 | S3 Cost Optimization (GM +3pp, capped at 100%) | PASS | Directional check passed |
| DS08 | S4 Hiring Wave (Payroll +10%) | PASS | Directional check passed |
| DS08 | S5 Marketing Push (Opex +20%) | PASS | Directional check passed |
| DS08 | S6 Cash Event (Cash -30%) | PASS | Directional check passed |
| DS08 | S7 Mixed Stack (S1+S4+S5 → then Reset) | PASS | Mixed applied + reset verified |
| DS09 | S0 Baseline (identity) | PASS |  |
| DS09 | S1 Pricing Lift (+5% Revenue) | PASS | Directional check passed |
| DS09 | S2 Demand Shock (-15% Revenue, months 1-3, revert) | PASS | Directional check passed |
| DS09 | S3 Cost Optimization (GM +3pp, capped at 100%) | PASS | Directional check passed |
| DS09 | S4 Hiring Wave (Payroll +10%) | PASS | Directional check passed |
| DS09 | S5 Marketing Push (Opex +20%) | PASS | Directional check passed |
| DS09 | S6 Cash Event (Cash -30%) | PASS | Directional check passed |
| DS09 | S7 Mixed Stack (S1+S4+S5 → then Reset) | PASS | Mixed applied + reset verified |
| DS10 | S0 Baseline (identity) | PASS |  |
| DS10 | S1 Pricing Lift (+5% Revenue) | PASS | Directional check passed |
| DS10 | S2 Demand Shock (-15% Revenue, months 1-3, revert) | PASS | Directional check passed |
| DS10 | S3 Cost Optimization (GM +3pp, capped at 100%) | PASS | Directional check passed |
| DS10 | S4 Hiring Wave (Payroll +10%) | PASS | Directional check passed |
| DS10 | S5 Marketing Push (Opex +20%) | PASS | Directional check passed |
| DS10 | S6 Cash Event (Cash -30%) | PASS | Directional check passed |
| DS10 | S7 Mixed Stack (S1+S4+S5 → then Reset) | PASS | Mixed applied + reset verified |
| DS11 | S0 Baseline (identity) | PASS |  |
| DS11 | S1 Pricing Lift (+5% Revenue) | PASS | Directional check passed |
| DS11 | S2 Demand Shock (-15% Revenue, months 1-3, revert) | PASS | Directional check passed |
| DS11 | S3 Cost Optimization (GM +3pp, capped at 100%) | PASS | Directional check passed |
| DS11 | S4 Hiring Wave (Payroll +10%) | PASS | Directional check passed |
| DS11 | S5 Marketing Push (Opex +20%) | PASS | Directional check passed |
| DS11 | S6 Cash Event (Cash -30%) | PASS | Directional check passed |
| DS11 | S7 Mixed Stack (S1+S4+S5 → then Reset) | PASS | Mixed applied + reset verified |
| DS12 | S0 Baseline (identity) | PASS |  |
| DS12 | S1 Pricing Lift (+5% Revenue) | PASS | Directional check passed |
| DS12 | S2 Demand Shock (-15% Revenue, months 1-3, revert) | PASS | Directional check passed |
| DS12 | S3 Cost Optimization (GM +3pp, capped at 100%) | PASS | Directional check passed |
| DS12 | S4 Hiring Wave (Payroll +10%) | PASS | Directional check passed |
| DS12 | S5 Marketing Push (Opex +20%) | PASS | Directional check passed |
| DS12 | S6 Cash Event (Cash -30%) | PASS | Directional check passed |
| DS12 | S7 Mixed Stack (S1+S4+S5 → then Reset) | PASS | Mixed applied + reset verified |
| DS13 | S0 Baseline (identity) | PASS |  |
| DS13 | S1 Pricing Lift (+5% Revenue) | PASS | Zero-revenue: 5% of 0 = 0 (expected) |
| DS13 | S2 Demand Shock (-15% Revenue, months 1-3, revert) | PASS | Zero-revenue: -15% of 0 = 0 (expected) |
| DS13 | S3 Cost Optimization (GM +3pp, capped at 100%) | PASS | Directional check passed |
| DS13 | S4 Hiring Wave (Payroll +10%) | PASS | Directional check passed |
| DS13 | S5 Marketing Push (Opex +20%) | PASS | Directional check passed |
| DS13 | S6 Cash Event (Cash -30%) | PASS | Directional check passed |
| DS13 | S7 Mixed Stack (S1+S4+S5 → then Reset) | PASS | Mixed applied + reset verified |
| DS14 | S0 Baseline (identity) | PASS |  |
| DS14 | S1 Pricing Lift (+5% Revenue) | PASS | Directional check passed |
| DS14 | S2 Demand Shock (-15% Revenue, months 1-3, revert) | PASS | Directional check passed |
| DS14 | S3 Cost Optimization (GM +3pp, capped at 100%) | PASS | Directional check passed |
| DS14 | S4 Hiring Wave (Payroll +10%) | PASS | Directional check passed |
| DS14 | S5 Marketing Push (Opex +20%) | PASS | Directional check passed |
| DS14 | S6 Cash Event (Cash -30%) | PASS | Directional check passed |
| DS14 | S7 Mixed Stack (S1+S4+S5 → then Reset) | PASS | Mixed applied + reset verified |
| DS15 | S0 Baseline (identity) | PASS |  |
| DS15 | S1 Pricing Lift (+5% Revenue) | PASS | Directional check passed |
| DS15 | S2 Demand Shock (-15% Revenue, months 1-3, revert) | PASS | Directional check passed |
| DS15 | S3 Cost Optimization (GM +3pp, capped at 100%) | PASS | Directional check passed |
| DS15 | S4 Hiring Wave (Payroll +10%) | PASS | Directional check passed |
| DS15 | S5 Marketing Push (Opex +20%) | PASS | Directional check passed |
| DS15 | S6 Cash Event (Cash -30%) | PASS | Directional check passed |
| DS15 | S7 Mixed Stack (S1+S4+S5 → then Reset) | PASS | Mixed applied + reset verified |

## Monte Carlo Reproducibility

| Dataset | Company | Reproducible | Runway | Survival | P10 | P50 | P90 |
|---------|---------|--------------|--------|----------|-----|-----|-----|
| DS01 | FlowForge | PASS | {'p10': 9.0, 'p25': 9.0, 'p50': 10.0, 'p75': 10.0, 'p90': 10.0, 'mean': 9.7, 'stdDev': 0.5, 'min': 9.0, 'max': 11.0} | {'6m': np.float64(100.0), '12m': np.float64(0.0), '18m': np.float64(0.0), '24m': np.float64(0.0)} | None | None | None |
| DS02 | CloudLedger | PASS | {'p10': 19.0, 'p25': 19.0, 'p50': 20.0, 'p75': 22.0, 'p90': 23.0, 'mean': 20.5, 'stdDev': 1.6, 'min': 16.0, 'max': 26.5} | {'6m': np.float64(100.0), '12m': np.float64(100.0), '18m': np.float64(91.8), '24m': np.float64(1.0)} | None | None | None |
| DS03 | GlowCart | PASS | {'p10': 5.0, 'p25': 5.0, 'p50': 5.0, 'p75': 5.0, 'p90': 6.0, 'mean': 5.2, 'stdDev': 0.5, 'min': 4.0, 'max': 7.0} | {'6m': np.float64(0.1), '12m': np.float64(0.0), '18m': np.float64(0.0), '24m': np.float64(0.0)} | None | None | None |
| DS04 | BazaarBridge | PASS | {'p10': 5.0, 'p25': 5.0, 'p50': 6.0, 'p75': 6.0, 'p90': 6.0, 'mean': 5.7, 'stdDev': 0.5, 'min': 5.0, 'max': 6.0} | {'6m': np.float64(0.0), '12m': np.float64(0.0), '18m': np.float64(0.0), '24m': np.float64(0.0)} | None | None | None |
| DS05 | Shadowbox Logistics | PASS | {'p10': 27.4, 'p25': 28.7, 'p50': 30.3, 'p75': 32.0, 'p90': 33.9, 'mean': 30.5, 'stdDev': 2.6, 'min': 24.1, 'max': 41.6} | {'6m': np.float64(100.0), '12m': np.float64(100.0), '18m': np.float64(100.0), '24m': np.float64(100.0)} | None | None | None |
| DS06 | CredPulse | PASS | {'p10': 5.0, 'p25': 5.0, 'p50': 5.0, 'p75': 5.0, 'p90': 5.0, 'mean': 5.0, 'stdDev': 0.1, 'min': 4.0, 'max': 6.0} | {'6m': np.float64(0.0), '12m': np.float64(0.0), '18m': np.float64(0.0), '24m': np.float64(0.0)} | None | None | None |
| DS07 | ProtoFab | PASS | {'p10': 7.0, 'p25': 7.8, 'p50': 8.0, 'p75': 9.0, 'p90': 9.0, 'mean': 8.1, 'stdDev': 1.0, 'min': 6.0, 'max': 11.0} | {'6m': np.float64(97.8), '12m': np.float64(0.0), '18m': np.float64(0.0), '24m': np.float64(0.0)} | None | None | None |
| DS08 | StudioSprint | PASS | {'p10': 3.0, 'p25': 3.0, 'p50': 3.0, 'p75': 3.0, 'p90': 3.0, 'mean': 3.0, 'stdDev': 0.1, 'min': 3.0, 'max': 4.0} | {'6m': np.float64(0.0), '12m': np.float64(0.0), '18m': np.float64(0.0), '24m': np.float64(0.0)} | None | None | None |
| DS09 | ArenaNova | PASS | {'p10': 12.0, 'p25': 13.0, 'p50': 13.0, 'p75': 14.0, 'p90': 14.0, 'mean': 13.2, 'stdDev': 0.6, 'min': 12.0, 'max': 15.0} | {'6m': np.float64(100.0), '12m': np.float64(89.3), '18m': np.float64(0.0), '24m': np.float64(0.0)} | None | None | None |
| DS10 | CareArc Clinics | PASS | {'p10': 4.0, 'p25': 4.0, 'p50': 4.0, 'p75': 5.0, 'p90': 5.0, 'mean': 4.3, 'stdDev': 0.5, 'min': 4.0, 'max': 5.0} | {'6m': np.float64(0.0), '12m': np.float64(0.0), '18m': np.float64(0.0), '24m': np.float64(0.0)} | None | None | None |
| DS11 | TutorLoop | PASS | {'p10': 6.0, 'p25': 6.0, 'p50': 6.0, 'p75': 6.0, 'p90': 6.0, 'mean': 6.0, 'stdDev': 0.2, 'min': 6.0, 'max': 7.0} | {'6m': np.float64(2.7), '12m': np.float64(0.0), '18m': np.float64(0.0), '24m': np.float64(0.0)} | None | None | None |
| DS12 | ApexExchange | PASS | {'p10': 24.0, 'p25': 25.3, 'p50': 26.9, 'p75': 28.8, 'p90': 30.8, 'mean': 27.2, 'stdDev': 2.6, 'min': 21.0, 'max': 40.1} | {'6m': np.float64(100.0), '12m': np.float64(100.0), '18m': np.float64(100.0), '24m': np.float64(90.2)} | None | None | None |
| DS13 | ZeroRev Labs | PASS | {'p10': 5.0, 'p25': 5.0, 'p50': 5.0, 'p75': 5.0, 'p90': 5.0, 'mean': 5.0, 'stdDev': 0.0, 'min': 5.0, 'max': 5.0} | {'6m': np.float64(0.0), '12m': np.float64(0.0), '18m': np.float64(0.0), '24m': np.float64(0.0)} | None | None | None |
| DS14 | MaxGM Co | PASS | {'p10': 21.0, 'p25': 22.0, 'p50': 24.0, 'p75': 24.6, 'p90': 26.2, 'mean': 23.7, 'stdDev': 2.0, 'min': 19.0, 'max': 33.2} | {'6m': np.float64(100.0), '12m': np.float64(100.0), '18m': np.float64(100.0), '24m': np.float64(33.7)} | None | None | None |
| DS15 | MinGM Co | PASS | {'p10': 9.0, 'p25': 9.0, 'p50': 9.0, 'p75': 9.0, 'p90': 9.0, 'mean': 9.0, 'stdDev': 0.0, 'min': 9.0, 'max': 9.0} | {'6m': np.float64(100.0), '12m': np.float64(0.0), '18m': np.float64(0.0), '24m': np.float64(0.0)} | None | None | None |

## Feature & UI/UX Improvement Ideas

### Trust (P0)

| # | Problem | Evidence | Suggested Fix | Size |
|---|---------|----------|---------------|------|
| 1 | Runway mismatch across pages if financial record has stale data | Baseline tests with multiple periods | Add "last updated" badge + auto-recalc trigger | M |
| 2 | No visual indicator when simulation uses 0 for missing metrics | ZeroRev Labs baseline test | Show "estimated" badge next to metrics sourced from fallback | S |
| 3 | Currency symbol not shown in simulation output charts | INR datasets display validation | Thread company.currency through all chart formatters | M |

### Onboarding

| # | Problem | Evidence | Suggested Fix | Size |
|---|---------|----------|---------------|------|
| 4 | No guided path for pre-revenue companies | ZeroRev Labs (DS13) edge case | Add pre-revenue onboarding flow with milestone tracking | L |
| 5 | Amount scale selection lacks visual preview | INR MILLIONS datasets | Show example: '₹25M displays as ₹25' with live preview | S |

### Scenario Builder

| # | Problem | Evidence | Suggested Fix | Size |
|---|---------|----------|---------------|------|
| 6 | No time-phased scenario support in UI | S2 demand shock (months 1-3) | Add start/end month pickers for each scenario lever | M |
| 7 | Cannot stack multiple scenarios visually | S7 mixed stack test | Add scenario composition builder with drag-and-drop | L |
| 8 | No 'Reset to Baseline' button after applying scenarios | S7 reset verification | Add prominent reset button with confirmation | S |

### Outputs & Explainability

| # | Problem | Evidence | Suggested Fix | Size |
|---|---------|----------|---------------|------|
| 9 | Simulation results don't show which inputs changed from baseline | All scenario tests | Add delta indicators showing input changes vs baseline | M |
| 10 | No export of simulation results for board decks | All datasets | Add PDF/PNG export of simulation summary cards | L |
| 11 | Monte Carlo seed/iterations not visible in results | Reproducibility tests | Display seed + iteration count in results footer | S |
| 12 | No comparison view for before/after scenario application | S1-S6 tests | Side-by-side baseline vs scenario output cards | M |

### Data Quality

| # | Problem | Evidence | Suggested Fix | Size |
|---|---------|----------|---------------|------|
| 13 | COGS computation may drift with floating point in edge cases | MinGM/MaxGM tests | Use Decimal for financial calculations in critical paths | M |
| 14 | No validation that GM stays 0-100 after scenario application | S3 cost optimization | Add server-side clamp + UI warning for out-of-range GM | S |
| 15 | Scale multiplier not applied consistently in all API responses | INR MILLIONS datasets | Centralize scale conversion in response serializer | M |

## Founder Takeaways by Persona

### FlowForge (Seed SaaS)
- **Persona**: First-time technical founder, ex-Google engineer
- **Runway**: 11.7 months (moderate)
- **Key Insight**: Start fundraising conversations now, optimize burn

### CloudLedger (Profitable SaaS)
- **Persona**: Serial entrepreneur, 3rd company, finance background
- **Runway**: Infinite (profitable)
- **Key Insight**: Focus on growth investment - burn is covered by revenue

### GlowCart (D2C E-commerce)
- **Persona**: Brand-first founder, ex-Nykaa marketing lead
- **Runway**: 6.7 months (moderate)
- **Key Insight**: Start fundraising conversations now, optimize burn

### BazaarBridge (Marketplace)
- **Persona**: Ops-heavy founder, ex-Flipkart supply chain
- **Runway**: 5.5 months (critical)
- **Key Insight**: Immediate action needed - consider fundraising or cost cuts

### Shadowbox Logistics (Logistics / Supply Chain)
- **Persona**: Industry veteran, 15yr logistics experience
- **Runway**: Infinite (profitable)
- **Key Insight**: Focus on growth investment - burn is covered by revenue

### CredPulse (Fintech)
- **Persona**: Ex-banker, regulatory expertise, risk-averse
- **Runway**: 5.2 months (critical)
- **Key Insight**: Immediate action needed - consider fundraising or cost cuts

### ProtoFab (Manufacturing)
- **Persona**: Hardware engineer, capital-intensive mindset
- **Runway**: 25.0 months (healthy)
- **Key Insight**: Good position to invest in growth while maintaining discipline

### StudioSprint (Agency / Services)
- **Persona**: Creative director turned founder, people-heavy cost structure
- **Runway**: 3.0 months (critical)
- **Key Insight**: Immediate action needed - consider fundraising or cost cuts

### ArenaNova (Gaming)
- **Persona**: Ex-Riot Games developer, product-obsessed
- **Runway**: 18.5 months (healthy)
- **Key Insight**: Good position to invest in growth while maintaining discipline

### CareArc Clinics (Healthcare)
- **Persona**: Doctor-turned-entrepreneur, patient outcomes focused
- **Runway**: 5.0 months (critical)
- **Key Insight**: Immediate action needed - consider fundraising or cost cuts

### TutorLoop (Edtech)
- **Persona**: Teacher-turned-founder, mission-driven
- **Runway**: 6.2 months (moderate)
- **Key Insight**: Start fundraising conversations now, optimize burn

### ApexExchange (Crypto / Web3)
- **Persona**: Quant trader, high-risk tolerance
- **Runway**: Infinite (profitable)
- **Key Insight**: Focus on growth investment - burn is covered by revenue

### ZeroRev Labs (Pre-revenue / Deep Tech)
- **Persona**: PhD researcher, zero revenue edge case
- **Runway**: 4.7 months (critical)
- **Key Insight**: Immediate action needed - consider fundraising or cost cuts

### MaxGM Co (Edge Case — 100% GM)
- **Persona**: Pure software, zero COGS test case
- **Runway**: Infinite (profitable)
- **Key Insight**: Focus on growth investment - burn is covered by revenue

### MinGM Co (Edge Case — 0% GM)
- **Persona**: Hardware-only, all revenue = COGS test case
- **Runway**: 7.5 months (moderate)
- **Key Insight**: Start fundraising conversations now, optimize burn

---
*Report generated by Predixen QA Lab v1.0 on 2026-02-14 16:12:21*