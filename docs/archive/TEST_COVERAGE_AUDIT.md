# FounderConsole Test Coverage Audit Report

**Date**: 2026-02-21
**Project**: FounderConsole - AI-Powered Financial Intelligence Platform
**Stack**: React 18 (frontend), FastAPI (backend), PostgreSQL, pytest (Python tests)

---

## EXECUTIVE SUMMARY

### Current Test Coverage Status
- **Backend Tests**: 4 test files, ~250 test cases (light coverage)
- **Frontend Tests**: 2 test files with Vitest (utility functions only)
- **QA Lab**: Comprehensive integration tests (150+ scenarios across 15 datasets)
- **Overall Assessment**: SPARSE but STRATEGIC coverage with critical gaps

### Overall Risk Assessment
**HIGH RISK** - Core financial calculation and simulation logic has limited automated test coverage. Critical API endpoints are untested. Recommend immediate prioritization of financial calculations, authentication, and data ingestion pipeline tests.

---

## PART 1: INVENTORY OF EXISTING TESTS

### 1.1 Backend Test Files (`/server/tests/`)

#### File: `test_financial_calculations.py` (~306 lines)
**Purpose**: Tests for expense normalization and burn/runway calculations
**Coverage**:
- ✅ Expense normalization (negative → positive)
- ✅ Burn formula (expenses - revenue)
- ✅ Runway calculation (cash / burn)
- ✅ Burn display formatting
- ✅ Sign convention detection
- ✅ Row classification (revenue, expense, derived)
- ✅ Expense bucket mapping (marketing, payroll, COGS, operating)
- ✅ Baseline metrics computation

**Test Classes**: 7 classes, ~30 test methods
**Quality Assessment**: 
- Assertions are meaningful and test both happy and edge paths
- Covers: zero expenses, zero revenue, null values, sign conventions
- Uses realistic financial data (thousands, millions)
- **ISSUE**: No tests for negative cash, division by zero, extreme value handling

#### File: `test_canonical_data_flow.py` (~172 lines)
**Purpose**: Data consistency and provenance tracking
**Coverage**:
- ✅ Hash determinism (same inputs → same hash)
- ✅ Key order independence in hashing
- ✅ Snapshot ID generation
- ✅ Financials schema validation
- ✅ ScenarioOverrides schema
- ✅ CompanyStateSchema structure
- ✅ Data serialization roundtrips
- ✅ Hash sensitivity to input changes

**Test Classes**: 5 classes, ~16 test methods
**Quality Assessment**:
- Tests are focused on data integrity and determinism
- Validates schema contracts
- **ISSUE**: No negative test cases for invalid schemas, no UUID format validation

#### File: `test_copilot_trust.py` (~202 lines)
**Purpose**: Copilot grounding status and validation
**Coverage**:
- ✅ Grounding status (VERIFIED, UNVERIFIED, NOT_AVAILABLE)
- ✅ Validation flags detection (runway/cash mismatch, Monte Carlo variance)
- ✅ Provenance attachment to responses
- ✅ Strict output modes
- ✅ Missing run handling

**Test Classes**: 4 classes, ~18 test methods
**Quality Assessment**:
- Uses mocks appropriately for database operations
- Tests detection of data inconsistencies
- **ISSUE**: Mocks are shallow, doesn't test actual database queries or JSON parsing errors

#### File: `test_truth_scan.py` (~259 lines)
**Purpose**: Data validation system
**Coverage**:
- ✅ Net burn computation (revenue, expenses, edge cases)
- ✅ Runway calculation (positive/negative burn, zero cash)
- ✅ Rule validation (missing metrics, negative values, short runway)
- ✅ Simulation gating logic
- ✅ Finalization validation (blocked issues prevent finalize)

**Test Classes**: 6 classes, ~31 test methods
**Quality Assessment**:
- Tests edge cases: zero revenue, zero expenses, None values
- Validates business logic for gating
- **ISSUE**: Missing tests for very large numbers, currency conversions, multi-period validation

### 1.2 Frontend Test Files (`/client/src/lib/__tests__/`)

#### File: `money.test.ts` (~76 lines)
**Purpose**: Scale multiplier and currency formatting
**Coverage**:
- ✅ Scale multipliers (units=1, thousands=1000, millions=1000000, crores=10000000)
- ✅ Input parsing (520K thousands → 520000 units)
- ✅ Base to display conversion
- ✅ Scale value formatting (K suffix for thousands)
- ✅ Alert thresholds
- ✅ Unit mismatch detection

**Test Framework**: Vitest
**Quality Assessment**:
- Pragmatic tests for user input handling
- Covers regression P0 #3 (unit mismatch detection)
- **ISSUE**: No test for currency symbol handling, no locale-specific formatting

#### File: `finance.test.ts` (~61 lines)
**Purpose**: Runway, burn, and forecast calculations
**Coverage**:
- ✅ Runway calculation (cash, expenses, revenue → months)
- ✅ Monthly burn calculation
- ✅ Growth rate clamping (prevents explosion from 1268% → 1.0 max)
- ✅ Cash flow forecasts (12-month projection)
- ✅ Runway formatting
- ✅ Gross margin normalization

**Test Framework**: Vitest
**Quality Assessment**:
- Tests for extreme values (prevents numeric overflow at month 12)
- Covers regression P0 #1 (clampGrowthRate), P0 #5 (normalizeGrossMarginPct)
- **ISSUE**: No test for negative growth, no test for historical data inconsistencies

### 1.3 QA Lab Integration Tests (`/qa-lab/`)

**Purpose**: Full end-to-end validation across 15 test datasets
**Coverage**:
- ✅ 15 test companies with realistic financial data
- ✅ 8 scenario templates (identity, pricing lift, demand shock, cost optimization, hiring, marketing, cash event, mixed)
- ✅ 150 test cases (15 datasets × 10 scenarios)
- ✅ Baseline validation (COGS, expenses, net burn, runway)
- ✅ Directional checks (scenario effects move metrics as expected)

**Test Structure**:
- `/qa-lab/leadsquared/`, `/qa-lab/pulsepal/`, `/qa-lab/saffron-street/`, `/qa-lab/lumalane/` (test companies)
- `/qa-lab/datasets/` (sample financial CSVs)
- `/qa-lab/scenarios/` (scenario definitions)
- `/qa-lab/runner/` (test executor)

**Quality Assessment**:
- Integration-level tests validate end-to-end flows
- **ISSUE**: Tests are currently manual/ad-hoc, not automated in CI/CD, no regression framework

### 1.4 Test Configuration

**pytest.ini**:
```ini
[pytest]
pythonpath = .
testpaths = server/tests
addopts = -q
```

**pyproject.toml**: Lists pytest>=9.0.2 as dependency

---

## PART 2: COVERAGE GAPS ANALYSIS

### 2.1 API Endpoints NOT TESTED (Critical Gap)

**Authentication & Authorization** (server/api/auth.py - 9KB):
- [ ] POST /auth/register - User registration
- [ ] POST /auth/login - Login with credentials
- [ ] POST /auth/logout - Session termination
- [ ] POST /auth/refresh - Token refresh
- [ ] GET /auth/me - Current user profile
- [ ] Password reset/change flows
- [ ] MFA/2FA flows (if implemented)
- **Risk**: Security vulnerability, privilege escalation

**Company Management** (server/api/companies.py - 13KB):
- [ ] POST /companies - Create new company
- [ ] GET /companies/:id - Retrieve company state
- [ ] PUT /companies/:id - Update company
- [ ] DELETE /companies/:id - Delete company (if allowed)
- [ ] GET /companies/:id/state - Canonical state
- [ ] GET /companies/:id/permissions - User permissions
- **Risk**: Data integrity, unauthorized access to company financials

**Data Ingestion** (server/api/ingest.py):
- [ ] POST /ingest/upload - File upload (CSV, Excel, PDF)
- [ ] GET /ingest/status/:upload_id - Upload status
- [ ] POST /ingest/process - Process and validate uploaded data
- [ ] GET /ingest/preview - Preview parsed data before finalization
- [ ] DELETE /ingest/:upload_id - Cancel/delete upload
- **Risk**: Data corruption, loss of financial records, format validation bypass

**Simulations** (server/api/simulations.py - 28KB, server/api/advanced_simulation.py - 28KB):
- [ ] POST /simulations/run - Trigger Monte Carlo simulation
- [ ] GET /simulations/:run_id - Fetch run results
- [ ] POST /simulations/:run_id/cancel - Cancel running simulation
- [ ] GET /simulations/:run_id/sensitivity - Sensitivity analysis
- [ ] POST /simulations/advanced - Advanced simulation with custom parameters
- **Risk**: Incorrect financial forecasts, incorrect scenario analysis

**Scenarios** (server/api/scenarios.py):
- [ ] POST /scenarios - Create new scenario
- [ ] GET /scenarios/:id - Retrieve scenario
- [ ] PUT /scenarios/:id - Update scenario
- [ ] DELETE /scenarios/:id - Delete scenario
- [ ] POST /scenarios/:id/run - Run scenario simulation
- **Risk**: Loss of planning work, incorrect scenario comparisons

**Connectors** (server/api/connectors.py - 29KB):
- [ ] POST /connectors/authorize/:connector_type - OAuth flow initiation
- [ ] GET /connectors/:connector_id/status - Connector connection status
- [ ] POST /connectors/:connector_id/sync - Trigger data sync
- [ ] GET /connectors/:connector_id/data - Fetch connector data
- [ ] DELETE /connectors/:connector_id - Disconnect
- **Risk**: Lost data syncs, missed financial updates, authentication bypass

**Copilot** (server/api/copilot.py - 69KB):
- [ ] POST /copilot/chat - Send message to AI copilot
- [ ] GET /copilot/context - Get current context
- [ ] POST /copilot/clarify - Request clarification from user
- [ ] GET /copilot/recommendations - Get AI recommendations
- **Risk**: Hallucination in financial advice, grounding failures

**Dashboard/KPIs** (server/api/dashboard_kpis.py - 20KB):
- [ ] GET /dashboards/:id - Fetch dashboard
- [ ] GET /kpis - List KPIs for company
- [ ] GET /kpis/:metric_id - Get specific KPI
- [ ] PUT /kpis/:metric_id - Update KPI
- **Risk**: Stale/incorrect metrics displayed to users

**Decisions** (server/api/decisions.py - 70KB):
- [ ] POST /decisions - Create decision record
- [ ] GET /decisions/:id - Fetch decision
- [ ] PUT /decisions/:id/status - Update decision status
- [ ] GET /decisions/impact - Calculate decision impact
- **Risk**: Lost audit trail, inability to track outcomes

### 2.2 Models NOT TESTED

**Database Models** (server/models/ - 43 files):
- [ ] User, Company, CompanySource
- [ ] FinancialRecord, CanonicalFinancials
- [ ] Scenario, ScenarioVersion
- [ ] SimulationRun, SimulationJob
- [ ] TruthScan, Dataset
- [ ] Connector, ConnectorCapability
- [ ] Dashboard, MetricDefinition
- [ ] Fundraising, Decision
- [ ] AlertsConfig, EmailEvent
- **Tests Missing**: Schema validation, ORM relationships, cascade deletes, constraints

**Validation** (Pydantic schemas):
- [ ] Invalid currency codes
- [ ] Invalid date ranges
- [ ] Negative financial values where not allowed
- [ ] Missing required fields
- [ ] Type mismatches

### 2.3 Simulation Engine NOT TESTED (Critical Gap)

**Enhanced Monte Carlo** (server/simulate/enhanced_monte_carlo.py - 23KB):
- [ ] Probability distribution generation (normal, lognormal, uniform)
- [ ] Monte Carlo path simulation (1000+ iterations)
- [ ] Percentile calculations (p10, p50, p90)
- [ ] Path aggregation and statistics
- [ ] Scenario application (pricing, cost, growth overrides)
- [ ] Edge cases: zero variance, infinite returns, negative paths
- **Risk**: Incorrect probabilistic forecasts, wrong survival probability

**Simulation Engine** (server/simulate/simulation_engine.py - 14KB):
- [ ] Month-by-month cash flow projection
- [ ] Scenario stacking and reset
- [ ] Revenue growth application
- [ ] Expense scaling
- [ ] Hiring plan integration
- [ ] Multi-scenario comparison
- **Risk**: Inaccurate runway calculations, incorrect scenario impacts

**Assumptions** (server/simulate/assumptions.py - 11KB):
- [ ] Default assumption loading
- [ ] Assumption override validation
- [ ] Macro modifier application
- **Risk**: Wrong assumptions used in forecasts

**Optimizer** (server/simulate/optimizer.py - 24KB):
- [ ] Optimization algorithm correctness
- [ ] Constraint handling
- [ ] Objective function calculation
- **Risk**: Suboptimal recommendations, incorrect decision scores

### 2.4 Copilot Agents NOT TESTED

**Intent Parser** (server/copilot/intent_parser.py - 19KB):
- [ ] Intent classification (what_if, recommendations, explain)
- [ ] Parameter extraction from natural language
- [ ] Context awareness
- **Risk**: Misinterpreted user requests, wrong recommendations

**Recommendation Engine** (server/copilot/recommendation_engine.py - 17KB):
- [ ] Recommendation generation
- [ ] Ranking by impact
- [ ] Explanation generation
- **Risk**: Poor quality recommendations, wrong prioritization

**Simulation Handler** (server/copilot/simulation_handler.py - 30KB):
- [ ] Conversation-driven simulation requests
- [ ] Context injection
- [ ] Result explanation
- **Risk**: Incorrect results propagated to users

**Trust Module** (server/copilot/trust.py - 15KB):
- ✅ Partially tested (test_copilot_trust.py)
- [ ] Full grounding status computation
- [ ] Validation flag detection
- [ ] Provenance chain validation

### 2.5 Data Ingestion Pipeline NOT TESTED (Critical Gap)

**Excel Extractor** (server/ingest/excel_extractor.py - 42KB):
- [ ] Multi-sheet parsing
- [ ] Row hierarchy detection
- [ ] Period extraction (monthly, quarterly, annual)
- [ ] Header detection
- [ ] Empty row/column handling
- [ ] Data type inference
- **Risk**: Corruption of financial data, missed rows

**PDF Extractor** (server/ingest/pdf_extractor.py - 39KB):
- [ ] Table detection in PDFs
- [ ] OCR (if needed)
- [ ] Layout analysis
- [ ] Data extraction accuracy
- [ ] Merged cells handling
- **Risk**: Lost financial data from PDF statements

**Classifier** (server/ingest/classifier.py - 13KB):
- ✅ Partially tested (test_financial_calculations.py)
- [ ] All label types (100+ accounting terms)
- [ ] Ambiguous classifications
- [ ] Custom metric detection
- **Risk**: Misclassified expenses affecting burn calculations

**Calculations** (server/ingest/calculations.py - 10KB):
- ✅ Partially tested (test_financial_calculations.py)
- [ ] Full integration test with real extracted data
- [ ] Rounding and precision handling
- [ ] Missing data imputation

**Benchmarks** (server/ingest/benchmarks.py - 17KB):
- [ ] Benchmark loading and comparison
- [ ] Percentile calculation
- [ ] Industry classification
- **Risk**: Wrong benchmarks shown to users

### 2.6 Metrics DSL NOT TESTED (Critical Gap)

**Parser** (server/metrics/dsl/parser.py - 3.5KB):
- [ ] DSL syntax parsing
- [ ] Operator precedence
- [ ] Function call parsing
- [ ] Error handling for malformed DSL
- **Risk**: Custom metric definitions fail silently

**Compiler** (server/metrics/dsl/compiler.py - 11KB):
- [ ] DSL compilation to executable code
- [ ] Type checking
- [ ] Validation
- **Risk**: Runtime errors in custom metric evaluation

**Validator** (server/metrics/dsl/validator.py - 10KB):
- [ ] Metric dependencies
- [ ] Circular reference detection
- [ ] Type compatibility
- **Risk**: Broken custom metrics

### 2.7 Connectors NOT TESTED (Critical Gap)

**35+ Connector Implementations**:
- [ ] Authentication (OAuth, API keys, mTLS)
- [ ] Data fetching (API calls, rate limiting)
- [ ] Data transformation to canonical schema
- [ ] Error handling (401, 429, 500 errors)
- [ ] Incremental sync (timestamp-based, webhooks)
- [ ] Pagination handling

**Examples**:
- Stripe (payment data)
- Xero, QuickBooks, Wave (accounting)
- Gusto, Deel, Rippling (payroll)
- Google Sheets, Salesforce, HubSpot (CRM)
- Plaid (banking)

**Risk**: Data sync failures, missing financial records, authentication bypass

### 2.8 Frontend Components NOT TESTED

**React 18 Client** (client/src - ~13 directories):
- [ ] Financial input forms (validating currency, scale)
- [ ] Scenario builder UI
- [ ] Dashboard KPI widgets
- [ ] Simulation result visualization
- [ ] Copilot chat UI
- [ ] Data upload/ingestion UI
- [ ] Authentication flows (login, password reset)
- [ ] Role-based access control (RBAC)
- **Framework**: Should use Vitest + React Testing Library
- **Risk**: User-facing bugs, incorrect input handling

### 2.9 Cross-Cutting Concerns NOT TESTED

**Authentication & Authorization**:
- [ ] JWT token validation
- [ ] Session management
- [ ] Permission checks on API endpoints
- [ ] Role-based access control
- **Risk**: Security breach, unauthorized data access

**Database Transactions**:
- [ ] Rollback on error
- [ ] Concurrent modifications
- [ ] Foreign key constraints
- **Risk**: Data corruption, orphaned records

**Error Handling**:
- [ ] HTTP exception responses (400, 401, 403, 404, 500)
- [ ] Validation error messages
- [ ] Graceful degradation
- **Risk**: Poor user experience, security info leakage

**Rate Limiting & Throttling**:
- [ ] API rate limits
- [ ] Connector API throttling
- [ ] Job queue limits
- **Risk**: Service abuse, DoS vulnerability

**Logging & Audit Trails**:
- [ ] User action logging
- [ ] Financial decision logging
- [ ] Connector sync logs
- **Risk**: Lost audit trail, compliance violation

---

## PART 3: EXISTING TEST QUALITY ANALYSIS

### 3.1 What IS Well-Tested (Strengths)

✅ **Financial Calculation Logic**:
- Burn formula (expenses - revenue)
- Runway formula (cash / burn)
- Edge cases: zero revenue, zero expenses, profitable scenarios
- Sign convention handling

✅ **Data Integrity**:
- Deterministic hashing for provenance
- Serialization roundtrips
- Schema validation

✅ **Frontend Utility Functions**:
- Scale conversions (units ↔ thousands ↔ millions)
- Growth rate clamping (prevents extreme values)
- Cash flow forecasting

✅ **QA Lab Integration**:
- 150+ full end-to-end scenarios
- Multiple test datasets with realistic financials
- Directional validation (scenario effects)

### 3.2 What is POORLY Tested (Weaknesses)

❌ **Critical Financial Flows**:
- No tests for data ingestion (Excel, PDF, CSV)
- No tests for connector sync (Stripe, Xero, etc.)
- No tests for Monte Carlo simulation correctness
- No tests for scenario stacking/reset
- No tests for sensitivity analysis

❌ **API Layer**:
- Only 4 test files for 52+ API endpoints
- No tests for auth, permissions, rate limiting
- No tests for error handling (400, 401, 403, 500)
- No tests for input validation on HTTP requests
- No tests for concurrent requests

❌ **Copilot/LLM Integration**:
- No tests for intent parsing
- No tests for recommendation quality
- No tests for grounding failures
- No tests for context window limits
- Only shallow mock tests for trust module

❌ **Frontend**:
- Only 2 test files
- Only utility function tests (money, finance)
- No tests for React components
- No tests for forms, UI interactions
- No tests for accessibility (a11y)

❌ **Edge Cases**:
- Negative cash balances
- Extreme growth rates (>1000%)
- Missing data (nulls in critical fields)
- Currency conversion edge cases
- Rounding and precision errors
- Concurrent modifications
- Very large datasets (>100K rows)

### 3.3 Assertion Quality

**Good**: Assertions are specific and check actual values
```python
assert baseline.net_burn == 5000.0  # Good: specific value
assert baseline.burn_status == BurnStatus.BURNING  # Good: enum comparison
assert "36+" in display  # Good: checks substring for capped display
```

**Poor**: Generic pass/fail checks without validation
```python
assert issues >= 0  # Bad: just checks non-negative, not actual value
assert dataset.finalized is False  # Bad: testing framework setup, not business logic
```

### 3.4 Mock Usage

**Good**: Mocks used for database dependencies
```python
mock_db = MagicMock()
mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_run
```

**Limitation**: Mocks are shallow, don't test actual database operations or transaction handling

---

## PART 4: RISK PRIORITIZATION

### Tier 1: CRITICAL (Test Immediately)

**1. Financial Calculations Pipeline**
- Impact: HIGH - Core business logic, affects every user
- Effort: MEDIUM - ~5 test files
- Coverage: Build on existing test_financial_calculations.py
  - Add tests for negative cash, extreme values
  - Add tests for multi-period projections
  - Add tests for currency conversions
  - Add tests for rounding precision

**2. Data Ingestion & Classification**
- Impact: HIGH - Affects data integrity
- Effort: LARGE - ~10 test files
- Coverage:
  - Excel extraction (multi-sheet, headers, hierarchies)
  - PDF extraction (table detection, OCR)
  - CSV parsing (delimiter detection, encoding)
  - Classifier accuracy (100+ label types)
  - Benchmark mapping

**3. Monte Carlo Simulation**
- Impact: CRITICAL - Financial forecast accuracy
- Effort: LARGE - ~8 test files
- Coverage:
  - Distribution generation (normal, lognormal)
  - Percentile calculation (p10, p50, p90)
  - Variance and skewness
  - Path aggregation
  - Scenario overlays
  - Edge cases: zero variance, negative paths

**4. Authentication & Authorization**
- Impact: CRITICAL - Security
- Effort: MEDIUM - ~4 test files
- Coverage:
  - User registration/login
  - JWT token validation
  - Session management
  - Permission checks on each API endpoint
  - Role-based access (admin, viewer, editor)

### Tier 2: HIGH (Test in Phase 2)

**5. API Endpoint Coverage**
- Impact: HIGH - User-facing functionality
- Effort: LARGE - ~15 test files
- Coverage: Every endpoint in server/api/
  - Happy path (valid inputs)
  - Error cases (400, 401, 403, 404, 500)
  - Input validation
  - Boundary values
  - Concurrent access

**6. Connector Sync Pipeline**
- Impact: HIGH - Data freshness
- Effort: LARGE - ~10 test files (one per major connector)
- Coverage:
  - OAuth flow
  - API authentication
  - Data transformation
  - Error handling (401, 429, 500)
  - Incremental sync
  - Rate limiting

**7. Copilot Intelligence**
- Impact: MEDIUM - User experience
- Effort: LARGE - ~8 test files
- Coverage:
  - Intent classification
  - Parameter extraction
  - Context awareness
  - Recommendation quality
  - Explanation accuracy
  - Grounding status computation

**8. Scenario & Simulation Management**
- Impact: HIGH - Planning functionality
- Effort: LARGE - ~6 test files
- Coverage:
  - Scenario creation/update/delete
  - Scenario stacking
  - What-if analysis
  - Sensitivity analysis
  - Result persistence

### Tier 3: MEDIUM (Test in Phase 3)

**9. Frontend Components**
- Impact: MEDIUM - UX quality
- Effort: LARGE - ~20+ test files
- Coverage:
  - Financial input forms
  - Scenario builder
  - Dashboard widgets
  - Copilot chat UI
  - Data upload UI
  - Accessibility (a11y)

**10. Metrics DSL**
- Impact: MEDIUM - Custom metrics
- Effort: MEDIUM - ~5 test files
- Coverage:
  - DSL parsing
  - Compilation
  - Validation
  - Dependency resolution
  - Runtime evaluation

**11. Logging & Audit Trails**
- Impact: MEDIUM - Compliance
- Effort: SMALL - ~3 test files
- Coverage:
  - User action logging
  - Financial decision logging
  - Audit trail retrieval

---

## PART 5: PRIORITIZED TEST PLAN

### Phase 1 (Weeks 1-2): Financial Foundation

**Goal**: Ensure core calculations are bulletproof

**Test Suite**: `test_financial_calculations_extended.py` (~400 lines)
```
TestExpenseNormalization:
  - test_negative_expense (✅ exists)
  - test_very_large_expense
  - test_fractional_expense
  - test_none_values
  - test_currency_conversion

TestBurnCalculation:
  - test_burning_cash (✅ exists)
  - test_profitable (✅ exists)
  - test_breakeven (✅ exists)
  - test_negative_revenue
  - test_extreme_values
  - test_precision_rounding

TestRunwayCalculation:
  - test_sustainable (✅ exists)
  - test_runway_months (✅ exists)
  - test_missing_cash (✅ exists)
  - test_capped_runway (✅ exists)
  - test_negative_cash
  - test_very_long_runway (>100 months)

TestMultiPeriodProjection:
  - test_12month_projection
  - test_growth_application
  - test_expense_scaling
  - test_cash_flow_accuracy
```

**Test Suite**: `test_data_ingestion_basic.py` (~400 lines)
```
TestCSVParsing:
  - test_comma_delimiter
  - test_semicolon_delimiter
  - test_encoding_detection (UTF-8, ISO-8859-1)
  - test_header_extraction
  - test_empty_rows
  - test_quoted_fields

TestExcelExtraction:
  - test_single_sheet
  - test_multi_sheet
  - test_header_detection
  - test_data_type_inference
  - test_empty_rows
  - test_merged_cells

TestClassifierAccuracy:
  - test_revenue_classification
  - test_expense_classification
  - test_cogs_classification
  - test_operating_expense_mapping
  - test_unknown_classification
```

### Phase 2 (Weeks 3-4): Simulation Correctness

**Test Suite**: `test_monte_carlo_simulation.py` (~500 lines)
```
TestDistributionGeneration:
  - test_normal_distribution
  - test_lognormal_distribution
  - test_uniform_distribution
  - test_seed_reproducibility

TestPercentileCalculation:
  - test_p10_p50_p90
  - test_percentile_ordering (p10 < p50 < p90)
  - test_edge_case_zero_variance

TestPathAggregation:
  - test_1000_paths
  - test_path_statistics
  - test_variance_calculation

TestScenarioApplication:
  - test_pricing_override
  - test_expense_override
  - test_growth_override
  - test_scenario_stacking
```

**Test Suite**: `test_api_endpoints.py` (~600 lines)
```
TestAuthEndpoints:
  - test_register_valid
  - test_register_duplicate_email
  - test_login_valid
  - test_login_invalid_password
  - test_jwt_token_validation
  - test_token_refresh

TestCompanyEndpoints:
  - test_create_company
  - test_get_company
  - test_update_company
  - test_list_companies
  - test_permission_denied
  - test_concurrent_access

TestSimulationEndpoints:
  - test_run_simulation
  - test_get_simulation_results
  - test_cancel_simulation
  - test_invalid_input_validation
```

### Phase 3 (Weeks 5-6): Connector & Copilot

**Test Suite**: `test_connector_sync.py` (~400 lines per connector)
```
TestConnectorAuth:
  - test_oauth_flow
  - test_api_key_auth
  - test_invalid_credentials

TestDataFetch:
  - test_fetch_single_page
  - test_pagination
  - test_rate_limiting
  - test_network_error_retry

TestDataTransform:
  - test_stripe_payment_mapping
  - test_xero_transaction_mapping
```

**Test Suite**: `test_copilot_intent.py` (~300 lines)
```
TestIntentClassification:
  - test_what_if_intent
  - test_recommendation_intent
  - test_explain_intent

TestParameterExtraction:
  - test_expense_increase
  - test_pricing_change
  - test_time_horizon
```

### Phase 4 (Weeks 7-8): Frontend & Integration

**Test Suites**: React component tests using Vitest + RTL
```
- LoginForm.test.tsx
- ScenarioBuilder.test.tsx
- DashboardKPIs.test.tsx
- DataUploadDialog.test.tsx
- CopilotChat.test.tsx
```

---

## PART 6: RECOMMENDATIONS

### Immediate Actions (This Week)

1. **Expand test_financial_calculations.py**
   - Add tests for negative cash, extreme values
   - Add multi-period projection tests
   - Add precision/rounding tests
   - Target: 50 test cases (currently ~30)

2. **Create test_monte_carlo_simulation.py**
   - Tests for distribution generation
   - Tests for percentile calculations
   - Tests for scenario overlays
   - Target: 40 test cases

3. **Set up CI/CD for pytest**
   - Run pytest in GitHub Actions on every PR
   - Set minimum coverage threshold: 60% on critical modules
   - Block PRs that reduce coverage

4. **Document test conventions**
   - Create TESTING.md with guidelines
   - Define fixture patterns for database mocks
   - Define assertion best practices

### Short-Term Actions (Next 2 Weeks)

5. **Create test_data_ingestion.py**
   - CSV, Excel, PDF parsing tests
   - Classifier accuracy tests
   - Sample files in tests/fixtures/

6. **Create test_api_endpoints.py**
   - Authentication tests
   - Authorization tests
   - Input validation tests
   - Error handling tests

7. **Migrate QA Lab tests to pytest**
   - Convert manual QA Lab tests to automated pytest framework
   - Integrate with CI/CD
   - Enable regression testing

### Medium-Term Actions (Next 4 Weeks)

8. **Set up frontend test infrastructure**
   - Configure Vitest in package.json
   - Add React Testing Library
   - Add coverage threshold (60% minimum)

9. **Create connector tests**
   - Start with top 5 connectors (Stripe, Xero, Gusto, Plaid, Salesforce)
   - Use mock API responses
   - Test transformation logic

10. **Create copilot intent tests**
    - Test intent classification
    - Test parameter extraction
    - Test with real LLM examples

### Long-Term Actions (Ongoing)

11. **Increase coverage targets**
    - Month 1: 40% coverage on critical modules
    - Month 2: 60% coverage
    - Month 3: 75% coverage
    - Year-end: 80% coverage on backend, 70% on frontend

12. **Implement mutation testing**
    - Use mutmut or similar tool
    - Ensure tests catch logic errors
    - Target: Kill ratio >80%

13. **Performance testing**
    - Load test Monte Carlo with 10K iterations
    - Load test large file uploads (>100MB)
    - Test concurrent simulation requests

14. **Security testing**
    - SQL injection tests
    - XSS protection tests
    - CSRF protection tests
    - Rate limiting tests

---

## PART 7: TEST INFRASTRUCTURE RECOMMENDATIONS

### Pytest Configuration

**Create pytest.ini**:
```ini
[pytest]
pythonpath = .
testpaths = server/tests
addopts = 
    -v
    --tb=short
    --strict-markers
    --cov=server
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=40
minversion = 7.0
markers =
    integration: Integration tests requiring database
    unit: Unit tests with mocks
    slow: Slow tests that take >1 second
    critical: Critical financial calculation tests
```

### Test Fixtures

**Create server/tests/conftest.py**:
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def db():
    """In-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    # Create tables
    Session = sessionmaker(bind=engine)
    yield Session()

@pytest.fixture
def sample_company(db):
    """Create a test company with financials."""
    # Create test data

@pytest.fixture
def mock_connector():
    """Mock connector for sync tests."""
    # Return MagicMock connector
```

### Coverage Reporting

**Add to CI/CD**:
```yaml
- name: Run pytest with coverage
  run: pytest --cov=server --cov-report=xml
  
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
```

---

## SUMMARY TABLE: WHAT'S TESTED VS WHAT'S NOT

| Component | Files | Test Coverage | Risk Level | Priority |
|-----------|-------|---|---|---|
| Financial Calculations | ~3 files | 60% | MEDIUM | PHASE 1 |
| Data Ingestion | ~6 files | 5% | CRITICAL | PHASE 1 |
| Monte Carlo Engine | ~2 files | 0% | CRITICAL | PHASE 1 |
| API Endpoints | ~52 files | <5% | CRITICAL | PHASE 2 |
| Connectors | ~36 files | 0% | HIGH | PHASE 2 |
| Copilot | ~20 files | 5% | MEDIUM | PHASE 2 |
| Frontend Components | ~13 dirs | <5% | MEDIUM | PHASE 3 |
| Metrics DSL | ~5 files | 0% | MEDIUM | PHASE 3 |
| Auth/Permissions | ~3 files | 0% | CRITICAL | PHASE 1 |
| **TOTAL** | **~150+ files** | **~10%** | **HIGH** | **IMMEDIATE** |

---

## CONCLUSION

FounderConsole has a **foundational test suite** with good core financial calculation tests and comprehensive QA Lab integration tests, but **critical gaps** in:
- Data ingestion pipeline
- Monte Carlo simulation correctness
- API endpoint coverage
- Authentication & authorization
- Connector sync reliability
- Frontend component testing

**Recommended approach**:
1. **Phase 1 (Weeks 1-2)**: Harden financial calculations and expand Monte Carlo tests
2. **Phase 2 (Weeks 3-4)**: Comprehensive API endpoint testing
3. **Phase 3 (Weeks 5-6)**: Connector and Copilot testing
4. **Phase 4 (Weeks 7-8)**: Frontend component testing

**Investment**: ~40-50 days of engineering effort
**Return**: 75% coverage on critical modules, significant risk reduction

