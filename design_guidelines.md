# Design Guidelines: FounderConsole

## Design Approach

**Selected System**: Modern "AI-tech" minimal design
**Rationale**: This is an investor-grade financial intelligence platform requiring precision, clarity, and trust. Dark mode default with electric blue/teal accents.

## Core Design Elements

### A. Color Palette

#### Dark Mode (Default)
- Background: `hsl(222 47% 8%)` - Deep navy
- Card: `hsl(222 40% 12%)` - Slightly elevated surface
- Primary: `hsl(199 89% 55%)` - Electric teal accent
- Secondary: `hsl(222 30% 18%)` - Soft dark
- Foreground: `hsl(210 20% 98%)` - Off-white text
- Muted: `hsl(210 15% 60%)` - Secondary text

#### Light Mode
- Background: `hsl(210 20% 98%)` - Clean off-white
- Card: `hsl(0 0% 100%)` - Pure white
- Primary: `hsl(199 89% 48%)` - Electric blue/teal
- Secondary: `hsl(210 15% 92%)` - Soft gray
- Foreground: `hsl(222 47% 11%)` - Near black
- Muted: `hsl(210 15% 40%)` - Gray text

#### Status Colors
- Success: `hsl(142 70% 45%)` - Green (healthy metrics)
- Warning: `hsl(38 92% 50%)` - Amber (caution)
- Danger: `hsl(0 84% 60%)` - Red (critical flags)

### B. Typography
- **Primary Font**: Inter (via Google Fonts CDN)
- **Monospace**: IBM Plex Mono for financial figures and metrics
- **Hierarchy**:
  - Page Titles: text-2xl, font-semibold
  - Section Headers: text-lg, font-medium
  - Body Text: text-sm, font-normal
  - Labels/Captions: text-xs, font-medium
  - Financial Figures: text-xl to text-3xl, font-mono, font-semibold
  - Small Metrics: text-sm, font-mono

### C. Layout System
**Spacing Units**: Consistent use of Tailwind units
- Small: 0.5rem (8px) - tight gaps
- Medium: 1rem (16px) - standard gaps
- Large: 1.5rem (24px) - section separation
- XL: 2rem (32px) - major sections

**Grid Structure**:
- Dashboard: 6 KPI cards in 2 rows x 3 columns
- Scenario Builder: 2-column split (left: knobs, right: preview)
- Main content: max-w-7xl centered with p-6 padding

### D. Component Library

**Cards**:
- Border radius: rounded-2xl (1rem)
- Subtle border: 1px solid with low opacity
- Soft shadow for elevation
- High whitespace (p-6)

**Buttons**:
- Primary: Electric teal background
- Secondary/Ghost: Transparent with hover elevation
- Size "icon" for icon-only buttons

**MetricCard (KPI Cards)**:
- Value in font-mono for financial data
- Direction arrows for trends (up/down)
- Benchmark badges (Above p50, Below p25)
- Status color coding

**BenchmarkBar**:
- Visual p25/p50/p75 markers
- Company value dot position
- Direction label (higher/lower is better)

**Data Confidence Pill**:
- Red: < 60 (critical)
- Amber: 60-80 (caution)
- Green: > 80 (healthy)

**Charts**:
- Use Recharts with consistent color scheme
- P10/P50/P90 bands with gradients
- Survival curves with clear labeling
- Tooltips with currency formatting

### E. Layout Patterns

**AppShell**:
- Left sidebar (collapsible, 280px default)
- Top bar with stepper + confidence pill + user menu
- Main content area with max-w-7xl

**Sidebar**:
- Logo at top (FounderConsole)
- Company switcher dropdown
- Navigation menu with icons
- Investor items hidden when FEATURE_INVESTOR_MODE=false

**Stepper (in Topbar)**:
- Truth → Simulation → Decision
- Current step highlighted with accent color
- Previous steps show checkmark
- Future steps dimmed

**Onboarding Wizard**:
- Progress indicator at top (6 steps)
- Single-column centered form
- Clear CTAs for each step

### F. Interactions
- Hover states with subtle elevation (hover-elevate class)
- Loading skeletons for async states (never blank)
- Smooth transitions (200ms ease)
- No layout shift on hover

### G. Accessibility
- High contrast ratios for financial data
- Focus rings visible on all interactive elements
- data-testid on all interactive elements
- Semantic HTML structure

## Page-Specific Guidelines

### Overview Dashboard
- 6 KPI cards: Runway, Burn, Growth, Margin, Retention, Concentration
- Top 3 recommendations section
- Copilot quick input

### Truth Scan
- Two large score cards: Quality of Growth, Data Confidence
- Benchmark bars for each metric
- Risk flags panel with severity badges

### Scenarios
- Template cards for quick start
- Left panel: Scenario knobs (sliders)
- Right panel: Instant preview

### Decisions
- 3 ranked DecisionCards with impact metrics
- Comparison table
- Survival curve + bands charts

### Copilot
- Split view: chat left, context panel right
- Quick action buttons
- Evidence citations in responses
