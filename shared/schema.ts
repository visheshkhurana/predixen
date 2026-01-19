import { sql } from "drizzle-orm";
import { pgTable, text, varchar, integer, real, jsonb, serial, timestamp } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
});

export const insertUserSchema = createInsertSchema(users).pick({
  username: true,
  password: true,
});

export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;

// Financial Input Schema - core financial data
export const financialInputSchema = z.object({
  cashOnHand: z.number().min(0, "Cash must be positive"),
  monthlyRevenue: z.number().min(0, "Revenue must be positive"),
  monthlyExpenses: z.number().min(0, "Expenses must be positive"),
  growthRate: z.number().min(-100).max(1000, "Growth rate must be between -100% and 1000%"),
  avgCostPerHire: z.number().min(0).default(10000),
});

export type FinancialInput = z.infer<typeof financialInputSchema>;

// Scenario Parameters Schema
export const scenarioParamsSchema = z.object({
  priceChangePercent: z.number().min(-100).max(1000).default(0),
  newHires: z.number().min(-1000).max(1000).default(0),
  costCutPercent: z.number().min(0).max(100).default(0),
  costCutAmount: z.number().min(0).default(0),
  newGrowthRate: z.number().min(-100).max(1000).optional(),
  fundingAmount: z.number().min(0).default(0),
  fundingMonth: z.number().min(1).max(24).default(6),
});

export type ScenarioParams = z.infer<typeof scenarioParamsSchema>;

// Full Scenario Schema
export const scenarioSchema = z.object({
  id: z.string(),
  name: z.string().min(1, "Scenario name is required"),
  description: z.string().optional(),
  financialInput: financialInputSchema,
  params: scenarioParamsSchema,
  projectionMonths: z.number().min(1).max(36).default(18),
});

export type Scenario = z.infer<typeof scenarioSchema>;

export const insertScenarioSchema = scenarioSchema.omit({ id: true });
export type InsertScenario = z.infer<typeof insertScenarioSchema>;

// Monthly Projection - single month's data
export const monthlyProjectionSchema = z.object({
  month: z.number(),
  date: z.string(),
  revenue: z.number(),
  expenses: z.number(),
  netBurn: z.number(),
  cashBalance: z.number(),
  runway: z.number().nullable(),
});

export type MonthlyProjection = z.infer<typeof monthlyProjectionSchema>;

// Simulation Result
export const simulationResultSchema = z.object({
  scenarioId: z.string(),
  scenarioName: z.string(),
  projections: z.array(monthlyProjectionSchema),
  summary: z.object({
    initialCash: z.number(),
    finalCash: z.number(),
    avgMonthlyBurn: z.number(),
    runwayMonths: z.number().nullable(),
    cashOutDate: z.string().nullable(),
    totalRevenue: z.number(),
    totalExpenses: z.number(),
  }),
});

export type SimulationResult = z.infer<typeof simulationResultSchema>;

// KPI Metrics for Dashboard
export const kpiMetricsSchema = z.object({
  cashOnHand: z.number(),
  monthlyBurn: z.number(),
  runwayMonths: z.number().nullable(),
  mrr: z.number(),
  burnTrend: z.enum(["up", "down", "stable"]),
  revenueTrend: z.enum(["up", "down", "stable"]),
});

export type KPIMetrics = z.infer<typeof kpiMetricsSchema>;

// Distribution Types for Monte Carlo Simulations
export const distributionTypeSchema = z.enum([
  "fixed",
  "normal",
  "lognormal",
  "uniform",
  "triangular",
  "discrete"
]);

export type DistributionType = z.infer<typeof distributionTypeSchema>;

// Distribution Parameters based on type
export const distributionParamsSchema = z.object({
  type: distributionTypeSchema,
  value: z.number().optional(),
  mean: z.number().optional(),
  stdDev: z.number().optional(),
  min: z.number().optional(),
  max: z.number().optional(),
  mode: z.number().optional(),
  values: z.array(z.object({
    value: z.number(),
    probability: z.number().min(0).max(1)
  })).optional()
});

export type DistributionParams = z.infer<typeof distributionParamsSchema>;

// Event Types for Scenario Simulation
export const eventTypeSchema = z.enum([
  "pricing_change",
  "layoff",
  "hiring_surge",
  "fundraise",
  "product_launch",
  "market_expansion",
  "cost_reduction",
  "churn_spike",
  "macroeconomic_shock",
  "competitor_action",
  "regulatory_change",
  "custom"
]);

export type EventType = z.infer<typeof eventTypeSchema>;

// Custom Event Definition with Distribution Support
export const scenarioEventSchema = z.object({
  id: z.string(),
  type: eventTypeSchema,
  name: z.string(),
  description: z.string().optional(),
  month: z.number().min(1).max(36),
  duration: distributionParamsSchema.optional(),
  probability: z.number().min(0).max(1).default(1),
  impact: z.object({
    revenue: distributionParamsSchema.optional(),
    costs: distributionParamsSchema.optional(),
    growth: distributionParamsSchema.optional(),
    churn: distributionParamsSchema.optional(),
    margin: distributionParamsSchema.optional(),
    headcount: distributionParamsSchema.optional(),
    cash: distributionParamsSchema.optional()
  }),
  conditions: z.array(z.object({
    metric: z.string(),
    operator: z.enum(["gt", "lt", "eq", "gte", "lte"]),
    value: z.number()
  })).optional()
});

export type ScenarioEvent = z.infer<typeof scenarioEventSchema>;

// Simulation Configuration
export const simulationConfigSchema = z.object({
  iterations: z.number().min(100).max(10000).default(1000),
  horizonMonths: z.number().min(6).max(60).default(24),
  seed: z.number().optional(),
  confidenceIntervals: z.array(z.number()).default([10, 25, 50, 75, 90]),
  parallelWorkers: z.number().min(1).max(8).default(4)
});

export type SimulationConfig = z.infer<typeof simulationConfigSchema>;

// Simulation Job Status
export const simulationJobStatusSchema = z.enum([
  "pending",
  "running",
  "completed",
  "failed",
  "cancelled"
]);

export type SimulationJobStatus = z.infer<typeof simulationJobStatusSchema>;

// Simulation Job for Async Execution
export const simulationJobSchema = z.object({
  id: z.string(),
  scenarioId: z.number(),
  status: simulationJobStatusSchema,
  progress: z.number().min(0).max(100).default(0),
  config: simulationConfigSchema,
  createdAt: z.string(),
  startedAt: z.string().optional(),
  completedAt: z.string().optional(),
  error: z.string().optional()
});

export type SimulationJob = z.infer<typeof simulationJobSchema>;

// Percentile Results
export const percentileResultsSchema = z.object({
  p10: z.number(),
  p25: z.number(),
  p50: z.number(),
  p75: z.number(),
  p90: z.number(),
  mean: z.number(),
  stdDev: z.number(),
  min: z.number(),
  max: z.number()
});

export type PercentileResults = z.infer<typeof percentileResultsSchema>;

// Monthly Percentile Band
export const monthlyPercentileBandSchema = z.object({
  month: z.number(),
  p10: z.number(),
  p25: z.number(),
  p50: z.number(),
  p75: z.number(),
  p90: z.number()
});

export type MonthlyPercentileBand = z.infer<typeof monthlyPercentileBandSchema>;

// Enhanced Simulation Results
export const enhancedSimulationResultSchema = z.object({
  jobId: z.string(),
  scenarioId: z.number(),
  config: simulationConfigSchema,
  runway: percentileResultsSchema,
  survivalProbability: z.object({
    "6m": z.number(),
    "12m": z.number(),
    "18m": z.number(),
    "24m": z.number()
  }),
  survivalCurve: z.array(z.object({
    month: z.number(),
    survivalRate: z.number()
  })),
  metrics: z.object({
    revenue: z.array(monthlyPercentileBandSchema),
    cash: z.array(monthlyPercentileBandSchema),
    burn: z.array(monthlyPercentileBandSchema),
    mrr: z.array(monthlyPercentileBandSchema).optional(),
    headcount: z.array(monthlyPercentileBandSchema).optional()
  }),
  distributions: z.object({
    runway: z.array(z.number()),
    finalCash: z.array(z.number()),
    finalRevenue: z.array(z.number())
  }),
  eventImpacts: z.array(z.object({
    eventId: z.string(),
    eventName: z.string(),
    occurrenceRate: z.number(),
    avgRunwayImpact: z.number(),
    avgCashImpact: z.number()
  })).optional(),
  executionTime: z.number(),
  timestamp: z.string()
});

export type EnhancedSimulationResult = z.infer<typeof enhancedSimulationResultSchema>;

// Sensitivity Analysis Parameter
export const sensitivityParameterSchema = z.object({
  name: z.string(),
  label: z.string(),
  baselineValue: z.number(),
  minValue: z.number(),
  maxValue: z.number(),
  steps: z.number().default(11)
});

export type SensitivityParameter = z.infer<typeof sensitivityParameterSchema>;

// Sensitivity Analysis Result (for Tornado Charts)
export const sensitivityResultSchema = z.object({
  parameter: z.string(),
  label: z.string(),
  baselineValue: z.number(),
  lowValue: z.number(),
  highValue: z.number(),
  runwayAtLow: z.number(),
  runwayAtHigh: z.number(),
  runwayAtBaseline: z.number(),
  impact: z.number(),
  direction: z.enum(["positive", "negative", "mixed"])
});

export type SensitivityResult = z.infer<typeof sensitivityResultSchema>;

// Tornado Chart Data
export const tornadoChartDataSchema = z.object({
  scenarioId: z.number(),
  targetMetric: z.string(),
  baselineValue: z.number(),
  parameters: z.array(sensitivityResultSchema)
});

export type TornadoChartData = z.infer<typeof tornadoChartDataSchema>;

// Scenario Version for Diff/Rollback
export const scenarioVersionSchema = z.object({
  id: z.number(),
  scenarioId: z.number(),
  version: z.number(),
  name: z.string(),
  description: z.string().optional(),
  inputs: z.record(z.any()),
  events: z.array(scenarioEventSchema),
  tags: z.array(z.string()),
  createdAt: z.string(),
  createdBy: z.number(),
  changeNotes: z.string().optional()
});

export type ScenarioVersion = z.infer<typeof scenarioVersionSchema>;

// Scenario Diff for Comparison
export const scenarioDiffSchema = z.object({
  versionA: z.number(),
  versionB: z.number(),
  changes: z.array(z.object({
    field: z.string(),
    path: z.string(),
    oldValue: z.any(),
    newValue: z.any(),
    changeType: z.enum(["added", "removed", "modified"])
  })),
  inputChanges: z.number(),
  eventChanges: z.number(),
  tagChanges: z.number()
});

export type ScenarioDiff = z.infer<typeof scenarioDiffSchema>;
