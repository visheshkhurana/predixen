# RunwayAI - Startup Financial Simulator

## Overview

RunwayAI is an AI-powered financial simulation tool designed for startup founders and CEOs. The application enables users to model "what-if" scenarios around key business levers like pricing, hiring, burn rate, and growth to understand how strategic decisions impact their startup's finances and runway. Users can input financial data manually or via file uploads (CSV/PDF), run simulations with various scenario parameters, and visualize projected cash flow, runway, and key metrics through charts and data tables.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: React 18 with TypeScript
- **Routing**: Wouter (lightweight React router)
- **State Management**: TanStack React Query for server state
- **Styling**: Tailwind CSS with CSS variables for theming (light/dark mode support)
- **UI Components**: shadcn/ui component library built on Radix UI primitives
- **Charts**: Recharts for data visualization
- **Forms**: React Hook Form with Zod validation
- **Build Tool**: Vite with hot module replacement

### Backend Architecture
- **Framework**: Express.js with TypeScript
- **API Design**: RESTful JSON API with `/api` prefix
- **Database ORM**: Drizzle ORM configured for PostgreSQL
- **Schema Validation**: Zod with drizzle-zod integration
- **Storage**: Memory-based storage implementation (IStorage interface) with PostgreSQL-ready schema

### Data Flow Pattern
1. Client components use React Query to fetch/mutate data via API endpoints
2. Express routes validate input using Zod schemas
3. Simulation engine processes financial inputs and scenario parameters
4. Results are stored and returned to the client for visualization

### Key Design Decisions
- **Shared Schema**: TypeScript types and Zod schemas in `/shared/schema.ts` ensure type safety across client and server
- **In-Memory Storage with DB-Ready Schema**: Uses MemStorage class implementing IStorage interface, allowing easy swap to PostgreSQL when needed
- **Component-Based UI**: Reusable components for KPI cards, charts, data tables, and forms
- **Scenario Simulation Engine**: Server-side calculation of monthly projections based on financial inputs and scenario modifiers (pricing changes, hiring, cost cuts, funding rounds)

### Project Structure
```
├── client/src/          # React frontend
│   ├── components/      # UI components (app-specific and shadcn/ui)
│   ├── pages/           # Route pages (dashboard, scenarios, data-input)
│   ├── hooks/           # Custom React hooks
│   └── lib/             # Utilities and query client
├── server/              # Express backend
│   ├── routes.ts        # API endpoint definitions
│   ├── simulation.ts    # Financial simulation engine
│   └── storage.ts       # Data persistence layer
├── shared/              # Shared types and schemas
│   └── schema.ts        # Drizzle schema + Zod validation
└── migrations/          # Database migrations (Drizzle Kit)
```

## External Dependencies

### Database
- **PostgreSQL**: Primary database (configured via DATABASE_URL environment variable)
- **Drizzle ORM**: Database toolkit for schema definition and queries
- **Drizzle Kit**: Migration tooling (`npm run db:push`)

### UI Framework
- **Radix UI**: Accessible component primitives (dialogs, dropdowns, forms, etc.)
- **Recharts**: React charting library for financial visualizations
- **Lucide React**: Icon library
- **Tailwind CSS**: Utility-first CSS framework

### Form & Validation
- **React Hook Form**: Form state management
- **Zod**: Schema validation for both client and server
- **@hookform/resolvers**: Zod resolver for React Hook Form

### Development
- **Vite**: Frontend build tool with HMR
- **TSX**: TypeScript execution for development server
- **esbuild**: Production bundling for server code

### Fonts
- Google Fonts: Inter, DM Sans, Fira Code, Geist Mono (loaded via CDN in index.html)