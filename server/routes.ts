import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { runSimulation } from "./simulation";
import { financialInputSchema, insertScenarioSchema } from "@shared/schema";
import { z } from "zod";

const simulationInputSchema = z.object({
  name: z.string().min(1, "Scenario name is required"),
  description: z.string().optional(),
  cashOnHand: z.coerce.number().min(0),
  monthlyRevenue: z.coerce.number().min(0),
  monthlyExpenses: z.coerce.number().min(0),
  growthRate: z.coerce.number(),
  avgCostPerHire: z.coerce.number().min(0).default(10000),
  priceChangePercent: z.coerce.number().default(0),
  newHires: z.coerce.number().default(0),
  costCutPercent: z.coerce.number().min(0).max(100).default(0),
  costCutAmount: z.coerce.number().min(0).default(0),
  newGrowthRate: z.coerce.number().optional(),
  fundingAmount: z.coerce.number().min(0).default(0),
  fundingMonth: z.coerce.number().min(1).max(24).default(6),
  projectionMonths: z.coerce.number().min(1).max(36).default(18),
});

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  
  // Simulate scenario
  app.post("/api/simulate", async (req, res) => {
    try {
      const input = simulationInputSchema.parse(req.body);
      const result = runSimulation(input);
      
      // Save the simulation result
      await storage.saveSimulation(result);
      
      // Also save as a scenario
      const scenario = {
        name: input.name,
        description: input.description,
        financialInput: {
          cashOnHand: input.cashOnHand,
          monthlyRevenue: input.monthlyRevenue,
          monthlyExpenses: input.monthlyExpenses,
          growthRate: input.growthRate,
          avgCostPerHire: input.avgCostPerHire,
        },
        params: {
          priceChangePercent: input.priceChangePercent,
          newHires: input.newHires,
          costCutPercent: input.costCutPercent,
          costCutAmount: input.costCutAmount,
          newGrowthRate: input.newGrowthRate,
          fundingAmount: input.fundingAmount,
          fundingMonth: input.fundingMonth,
        },
        projectionMonths: input.projectionMonths,
      };
      await storage.createScenario(scenario);
      
      res.json(result);
    } catch (error) {
      if (error instanceof z.ZodError) {
        res.status(400).json({ error: "Validation failed", details: error.errors });
      } else {
        res.status(500).json({ error: "Simulation failed" });
      }
    }
  });

  // Get latest simulation
  app.get("/api/simulations/latest", async (req, res) => {
    try {
      const result = await storage.getLatestSimulation();
      if (!result) {
        res.status(404).json({ error: "No simulations found" });
        return;
      }
      res.json(result);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch simulation" });
    }
  });

  // Get all scenarios
  app.get("/api/scenarios", async (req, res) => {
    try {
      const scenarios = await storage.getScenarios();
      res.json(scenarios);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch scenarios" });
    }
  });

  // Get single scenario
  app.get("/api/scenarios/:id", async (req, res) => {
    try {
      const scenario = await storage.getScenario(req.params.id);
      if (!scenario) {
        res.status(404).json({ error: "Scenario not found" });
        return;
      }
      res.json(scenario);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch scenario" });
    }
  });

  // Delete scenario
  app.delete("/api/scenarios/:id", async (req, res) => {
    try {
      const deleted = await storage.deleteScenario(req.params.id);
      if (!deleted) {
        res.status(404).json({ error: "Scenario not found" });
        return;
      }
      res.json({ success: true });
    } catch (error) {
      res.status(500).json({ error: "Failed to delete scenario" });
    }
  });

  // Save financial data
  app.post("/api/financial-data", async (req, res) => {
    try {
      const data = financialInputSchema.parse(req.body);
      const saved = await storage.saveFinancialData(data);
      res.json(saved);
    } catch (error) {
      if (error instanceof z.ZodError) {
        res.status(400).json({ error: "Validation failed", details: error.errors });
      } else {
        res.status(500).json({ error: "Failed to save financial data" });
      }
    }
  });

  // Get financial data
  app.get("/api/financial-data", async (req, res) => {
    try {
      const data = await storage.getFinancialData();
      if (!data) {
        res.status(404).json({ error: "No financial data found" });
        return;
      }
      res.json(data);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch financial data" });
    }
  });

  // File upload endpoint (mock implementation for MVP)
  app.post("/api/upload", async (req, res) => {
    try {
      // For MVP, return mock parsed data
      // In production, this would parse CSV/PDF files
      const mockParsedData = {
        cashOnHand: 500000,
        monthlyRevenue: 45000,
        monthlyExpenses: 75000,
        growthRate: 8,
        source: "csv",
      };
      res.json(mockParsedData);
    } catch (error) {
      res.status(500).json({ error: "Failed to parse file" });
    }
  });

  return httpServer;
}
