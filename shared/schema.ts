import { sql } from "drizzle-orm";
import { pgTable, text, varchar, integer, real, jsonb } from "drizzle-orm/pg-core";
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
