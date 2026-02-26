# FounderConsole

## Overview
FounderConsole is an AI-powered financial intelligence platform for startups, designed to enhance survival and growth while mitigating risk and dilution. It provides investor-grade diligence, probabilistic simulations, and ranked decision recommendations to support financial planning, helping startups understand financial health, predict outcomes, and make strategic decisions. The platform aims to revolutionize how startups manage their finances and interact with investors.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Design Principles
The platform uses a modern full-stack architecture with React/TypeScript for the frontend and FastAPI/Python for the backend. It emphasizes data-driven insights, probabilistic modeling, and AI-powered recommendations through a modular design. Key architectural components include data ingestion, truth scanning, simulation, decision-making, and AI copilot functionalities. Scalability is achieved using FastAPI and PostgreSQL, while UI/UX focuses on data visualization and interactive components built with Tailwind CSS and shadcn/ui. Data integrity is enforced via Zod, Pydantic, and Alembic, with security based on JWT authentication and RBAC.

### Frontend Architecture
-   **Frameworks**: React 18 with TypeScript, Wouter, Zustand, TanStack React Query.
-   **UI/UX**: Tailwind CSS (dark mode default), shadcn/ui, Recharts for data visualization.
-   **Forms**: React Hook Form with Zod validation.

### Backend Architecture
-   **Framework**: FastAPI (Python 3.11).
-   **Database**: PostgreSQL with SQLAlchemy ORM, Alembic for migrations.
-   **Authentication**: JWT-based.
-   **Validation**: Pydantic models.

### Key Features and Technical Implementations
1.  **Data Management**: Supports CSV upload, manual entry, AI-powered extraction, and multi-currency handling.
2.  **Truth Scan**: A multi-stage data validation layer ensuring data quality.
3.  **Simulation Engine**: Enhanced Monte Carlo simulations with 24-month projections, asynchronous execution, custom event modeling, sensitivity analysis, and scenario versioning.
4.  **Optimization & Recommendations**: Features constrained multi-objective optimization and an automated recommendations engine.
5.  **AI Copilot System**: A Multi-Agent Fund Flow Copilot with a Router/Orchestrator Agent directing queries to specialized agents. Uses a Company Knowledge Base (CKB) for context, provides structured responses, and integrates multi-LLM for task-specific model selection.
6.  **Real-Time Simulation Copilot**: AI guidance integrated into the simulation workflow, offering context-aware prompts and narrative summaries.
7.  **Fundraising OS**: Module for cap table management, dilution calculations, fundraising round tracking, and an Investor Room.
8.  **Forecasting & Alerts**: Utilizes Holt-Winters exponential smoothing and linear regression for forecasting, and Z-score anomaly detection, threshold monitoring, and runway warnings for alerts.
9.  **Data Connectors**: Framework for payroll & ERP connectors and 37 production data connectors across financial and operational categories.
10. **Enhanced AI Interaction**: Includes a Copilot Trust Module for data veracity, natural conversational AI, and web research capabilities for market benchmarks.
11. **Consultant-Grade Copilot Persona**: System prompts are upgraded to provide structured, data-backed recommendations with a strategic persona.
12. **Simulation Experience Upgrade**: Features Before/After Delta Cards, Payback Clock Widget, Risk Alert Banner, data-driven recommendations (GO/CONDITIONAL/NO-GO), second-order effects detection, and confidence scoring.
13. **Automatic Counter-Move Simulation**: System automatically runs 3 counter-move simulations (Cost Cut 20%, Raise Prices 10%, Freeze Hiring) when a scenario is simulated.
14. **AI Decision Summary**: Provides a 1-2 sentence recommendation, Decision Score, verdict, and supporting bullet points.
15. **Narrative Strategic Briefing**: Transforms the Decisions page into a text-based "founder's briefing document" covering situation, recommendations, consequences, execution playbook, and risks.

### User Roles
-   **Platform Admin**: Application owner.
-   **Company Level Roles**: `owner`, `admin`, `analyst`, `viewer` with varying access levels.

## External Dependencies

-   **OpenAI**: For financial analysis, metrics extraction, and vision tasks.
-   **Anthropic**: For complex reasoning, coding, and strategy.
-   **Google Gemini**: For general chat and high-volume tasks.
-   **Perplexity**: For real-time web search, market research, and benchmark data in the copilot.
-   **PostgreSQL**: Primary relational database.
-   **Google Fonts**: Inter, IBM Plex Mono.
-   **Resend**: Email delivery service (verified sender: noreply@founderconsole.ai).
-   **Twilio**: SMS/phone notifications (credentials configured).

## Error Handling Architecture
-   **`getErrorMessage()`**: Central utility in `client/src/lib/errors.ts` that safely extracts string messages from any error type, preventing React Error #185.
-   **ErrorBoundary**: Supports both full-page and inline (`inline` prop) modes for component-level isolation. Error Details panel always visible (collapsed by default).
-   **QueryClient**: `throwOnError: false` prevents query errors from propagating to ErrorBoundary. Smart retry skips 401/403/404.
-   **Runway display**: Values >=900 months rendered as "Sustainable" or "infinity" via `isRunwaySustainable()` / `formatRunway()` / `formatRunwayInline()` in `utils.ts`. RUNWAY_SUSTAINABLE constant = 900 everywhere.
-   **useFinancialMetrics**: Threshold `< 900` to correctly identify sustainable runway values.
-   **Paginated API responses**: Backend list endpoints return paginated `{items, total, page, page_size}`. `api.companies.list()` and `api.scenarios.list()` extract `.items` to return plain arrays.
-   **Burn Rate**: Labeled as "Net Burn Rate" on Dashboard; dynamically labeled "Net Burn" or "Monthly Surplus" on Health Check.
-   **Burn label clarity**: "Burn Cut: -96%" changed to "Burn Increase: +96%" with red styling when `burn_reduction_pct < 0`. Applied across: `scenarios.tsx`, `ScenarioCard.tsx`, `copilot.tsx`, `ScenarioWizard.tsx`.
-   **Churn Rate**: Truth scan backend populates `churn_rate` key; frontend normalizes percentage vs decimal. Distinguishes missing data (N/A) from actual 0% churn.
-   **CSRF token fix**: `api/client.ts` `request()` includes `credentials: "include"` + automatic CSRF retry (fetch `/api/health` to refresh cookie, retry once).
-   **Simulation search bar**: Input text persists after clicking Simulate (removed `setQuestionInput('')` calls). Supports iteration on custom scenarios.
-   **NLP parser**: Handles combined hiring, CAC changes, churn direction, VC funding decline. Growth uplift per hire = `Math.min(totalHires * 1.5, 15)` (was 3x, capped at 15%).
-   **NLP parser guardrails**: All parsed parameters clamped to backend guardrail limits before submission: burn_reduction_pct [-100, 80], growth_uplift_pct [-30, 50], pricing_change_pct [-50, 100], churn_change_pct [-20, 30], cac_change_pct [-50, 200]. Prevents 422 validation errors on custom scenarios.
-   **Monte Carlo P10/P50/P90**: All three engines use 120-month cap with stochastic volatility for meaningful percentile spread.
-   **Monte Carlo burn handling**: `burn_reduction_pct` now properly handles negative values (burn increases). `clamped_burn_change = max(-100, min(100, value))`. A -50% burn reduction means costs increase by 50%.
-   **Monte Carlo CAC impact**: CAC changes now affect net_cashflow. Incremental CAC cost = (new_customers × adjusted_cac) - (new_customers × baseline_cac). Higher CAC properly reduces runway.
-   **VC funding decline NLP**: "VC funding declines 30%" now properly models: CAC +18% (60% of decline), growth -12% (40% of decline), burn increase +4.5% (15% of decline). Previously only affected CAC and growth without burn impact.
-   **Decision engine calibration**: Escalating risk penalties for burn increases: >30% gets -0.10, >50% adds -0.15, >75% adds -0.10 more. Risk text warns about burn increases.
-   **AI Decision Summary**: Burn-increase caveats added when actual burn increases >50% vs baseline. Score penalty: -0.75 for >50%, -1.5 for extreme. Uses actual burn data, not name heuristics.
-   **Briefing progress indicator**: `LOADING_STEPS` in `decisions.tsx` total 35s (5+8+10+12). Fourth step: "Generating strategic briefing".
-   **Onboarding Step 3 pre-fill**: Payroll and OpEx pre-filled from Step 2 baselineData when transitioning.
-   **PageErrorFallback**: Uses `import.meta.env.DEV` for Vite compatibility.
-   **Scenario retry buttons**: Use React Query `refetch()` instead of `window.location.reload()` to preserve user input state.
-   **Metrics partial degradation**: `useFinancialMetrics` returns `isPartiallyDegraded` flag when any (but not all) data queries fail.
-   **Onboarding Step 3 data persistence**: "Next: Data Sources" button saves expense breakdown to backend via `manualBaselineMutation` before advancing to Step 4.
-   **StrategyCard burn warning**: Cards with `burnChange > 50%` show a red warning with phased execution advice. `data-testid="warning-high-burn-{strategyId}"`.
-   **"Run Another Scenario" button**: Now resets `selectedScenarioId` to null (clears previous results), clears input, and scrolls to top. Previously only cleared input.
-   **KPI source labels**: Metrics now properly distinguish user-provided data ("Verified") from backend-computed ("Computed") and AI-estimated ("Estimated"). Only marks as "reported" when data comes from truth scan or manual user entry, not from seed/demo data.
-   **Phased startup**: Critical routes (auth, billing, onboarding) register in <1s. Remaining modules (simulation, connectors, copilot) load in a background thread. Connectors lazy-load via `load_all_connectors()`.
-   **SIGHUP resilience**: Node process ignores SIGHUP signals (lets workflow manager handle restarts instead of shutting down).
-   **Database reliability**: `pool_pre_ping=True`, `pool_recycle=1800` for automatic connection recovery.
-   **Password validation**: Simplified to 8 chars + 1 number (frontend and backend aligned).
-   **Billing API**: `/billing/plans` (Free/Pro/Team), `/billing/subscription`, `/billing/subscribe/{plan_id}`, `/billing/cancel`. Registered as critical route.
-   **Onboarding API**: `/onboarding/steps` (4 steps), `/onboarding/industries` (7 industries with benchmark flags). Registered as critical route.
-   **Demo metrics**: `/demo/metrics` returns sample SaaS KPIs (MRR, ARR, burn, runway, CAC, LTV, etc.) for unauthenticated demo experience.
-   **Stripe integration listing**: `/integrations/available` now includes `payments` category with Stripe connector.
-   **Proxy error message**: Changed from "simulation engine temporarily unavailable" to "Our servers are warming up" with retry guidance.
-   **401 redirect**: Only fires on mutation 401s (POST/PUT/PATCH/DELETE), not GET queries. Prevents infinite redirect loops.
