# Design Guidelines: AI-Powered Startup Financial Simulator

## Design Approach

**Selected System**: Hybrid approach combining Linear's modern aesthetic, Stripe's data clarity, and Carbon Design's enterprise patterns

**Rationale**: This is a utility-focused, data-intensive productivity tool requiring precision, clarity, and trust. The design must prioritize information hierarchy, data visualization excellence, and efficient workflows over decorative elements.

## Core Design Elements

### A. Typography
- **Primary Font**: Inter or SF Pro (via Google Fonts CDN)
- **Secondary/Monospace**: IBM Plex Mono for financial figures and data tables
- **Hierarchy**:
  - Page Titles: text-2xl to text-3xl, font-semibold
  - Section Headers: text-xl, font-medium
  - Body Text: text-base, font-normal
  - Labels/Captions: text-sm, font-medium
  - Financial Figures: text-lg to text-2xl, font-mono, font-semibold
  - Small Data/Metrics: text-xs, font-mono

### B. Layout System
**Spacing Units**: Consistent use of Tailwind units: 2, 4, 6, 8, 12, 16, 24
- Component padding: p-4 to p-6
- Section margins: mb-8 to mb-12
- Card spacing: gap-6 to gap-8
- Form field gaps: space-y-4

**Grid Structure**:
- Dashboard: 12-column grid for metric cards (3-4 columns on desktop, stack on mobile)
- Scenario Builder: 2-column split (60/40) - inputs left, preview right
- Data tables: Full-width with horizontal scroll on mobile

### C. Component Library

**Core UI Elements**:
- Cards: Subtle borders (border border-gray-200), rounded-lg, minimal shadow, bg-white
- Buttons: Primary (solid), Secondary (outline), Tertiary (ghost) - rounded-md, px-4 py-2
- Input Fields: Consistent height (h-10), rounded-md borders, focus rings
- Tabs: Underline style for section switching
- Badges: Rounded-full for status indicators (runway warnings, confidence levels)

**Navigation**:
- Top nav bar: Sticky, bg-white with bottom border, contains logo, main nav, AI assistant trigger
- Sidebar (optional): Left-aligned navigation for Dashboard, Scenarios, Data, Settings
- Breadcrumbs: For deep navigation in scenario editing

**Data Displays**:
- Metric Cards: Large numbers with context labels, trend indicators (↑↓), sparkline charts
- Data Tables: Zebra striping, sortable columns, fixed headers on scroll
- Charts: Line charts for projections, bar charts for comparisons, range areas for confidence intervals
- Timeline View: Horizontal month-by-month runway visualization

**Forms**:
- Multi-step wizard for data input (Step indicators at top)
- Grouped form sections with clear labels
- Upload zones: Drag-and-drop areas with CSV/PDF icons, file type indicators
- Inline validation with green checkmarks/red warnings

**AI Assistant**:
- Floating chat bubble (bottom-right) or slide-out panel
- Message bubbles with clear AI vs User distinction
- Code/data snippets in monospace with copy buttons
- Suggestion chips for quick actions

### D. Layout Patterns

**Dashboard**:
- Hero metrics row: 3-4 key KPIs (Cash on Hand, Monthly Burn, Runway, MRR)
- Chart section: Primary cash balance projection (full-width)
- Scenario comparison grid: 2-3 columns comparing active scenarios
- Recent activity feed: Sidebar or bottom section

**Scenario Builder**:
- Left panel: Accordion-style input sections (Pricing, Hiring, Costs, Growth, Funding)
- Right panel: Live preview of impact with mini-charts
- Bottom: Primary action button "Run Simulation"

**Results View**:
- Full-width interactive chart with zoom/pan
- Metrics summary cards above chart
- Confidence interval visualization (shaded ranges)
- Tabbed detailed views: Cash Flow Table, P&L Projection, Assumptions
- AI insights panel: Recommendations and risk flags

**Data Input**:
- Three-tab interface: Manual Entry | CSV Upload | PDF Upload
- Manual: Form grid with logical grouping (Current State | Assumptions | Scenarios)
- Upload: Large drop zones with format specifications and example downloads
- Confirmation step: Editable table showing parsed data

## Images
No hero images needed - this is a productivity tool focused on data and functionality. Use icons from Heroicons for:
- Financial metrics (chart icons, currency symbols)
- Upload states (document, cloud-upload)
- Status indicators (warning, check-circle, information)
- Navigation (dashboard, settings, data)

## Accessibility
- High contrast ratios for all financial data (WCAG AAA for numbers)
- Keyboard navigation for all interactive elements
- Screen reader labels for charts and data visualizations
- Focus indicators on all form inputs and controls
- Color-blind safe palettes for chart lines and status indicators