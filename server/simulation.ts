import type { FinancialInput, ScenarioParams, MonthlyProjection, SimulationResult } from "@shared/schema";

interface SimulationInput {
  name: string;
  description?: string;
  cashOnHand: number;
  monthlyRevenue: number;
  monthlyExpenses: number;
  growthRate: number;
  avgCostPerHire: number;
  priceChangePercent: number;
  newHires: number;
  costCutPercent: number;
  costCutAmount: number;
  newGrowthRate?: number;
  fundingAmount: number;
  fundingMonth: number;
  projectionMonths: number;
}

export function runSimulation(input: SimulationInput): SimulationResult {
  const {
    name,
    cashOnHand,
    monthlyRevenue,
    monthlyExpenses,
    growthRate,
    avgCostPerHire,
    priceChangePercent,
    newHires,
    costCutPercent,
    costCutAmount,
    newGrowthRate,
    fundingAmount,
    fundingMonth,
    projectionMonths,
  } = input;

  const projections: MonthlyProjection[] = [];
  
  // Calculate adjusted starting values based on scenario parameters
  let currentRevenue = monthlyRevenue * (1 + priceChangePercent / 100);
  let currentExpenses = monthlyExpenses;
  
  // Apply hiring changes
  currentExpenses += newHires * avgCostPerHire;
  
  // Apply cost cuts (ensure expenses never go below zero)
  if (costCutPercent > 0) {
    currentExpenses = Math.max(0, currentExpenses * (1 - costCutPercent / 100));
  }
  if (costCutAmount > 0) {
    currentExpenses = Math.max(0, currentExpenses - costCutAmount);
  }
  
  // Ensure minimum expenses (can't be negative)
  currentExpenses = Math.max(0, currentExpenses);
  
  // Use new growth rate if specified
  const effectiveGrowthRate = newGrowthRate !== undefined ? newGrowthRate : growthRate;
  const monthlyGrowthMultiplier = 1 + effectiveGrowthRate / 100;
  
  let currentCash = cashOnHand;
  let runwayMonth: number | null = null;
  
  const now = new Date();
  
  for (let month = 1; month <= projectionMonths; month++) {
    // Apply funding if this is the funding month
    if (fundingAmount > 0 && month === fundingMonth) {
      currentCash += fundingAmount;
    }
    
    const netBurn = currentExpenses - currentRevenue;
    currentCash = currentCash - netBurn;
    
    // Calculate date for this month
    const projectionDate = new Date(now);
    projectionDate.setMonth(projectionDate.getMonth() + month);
    const dateStr = projectionDate.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
    
    // Calculate remaining runway at this point
    let remainingRunway: number | null = null;
    if (netBurn > 0 && currentCash > 0) {
      remainingRunway = Math.ceil(currentCash / netBurn);
    } else if (netBurn <= 0) {
      remainingRunway = null; // Profitable
    }
    
    projections.push({
      month,
      date: dateStr,
      revenue: Math.round(currentRevenue),
      expenses: Math.round(currentExpenses),
      netBurn: Math.round(netBurn),
      cashBalance: Math.round(currentCash),
      runway: remainingRunway,
    });
    
    // Track when cash runs out
    if (currentCash <= 0 && runwayMonth === null) {
      runwayMonth = month;
    }
    
    // Apply growth for next month
    currentRevenue = currentRevenue * monthlyGrowthMultiplier;
  }
  
  // Calculate summary metrics
  const totalRevenue = projections.reduce((sum, p) => sum + p.revenue, 0);
  const totalExpenses = projections.reduce((sum, p) => sum + p.expenses, 0);
  const avgMonthlyBurn = Math.round(
    projections.reduce((sum, p) => sum + Math.max(0, p.netBurn), 0) / projections.length
  );
  
  // Calculate runway from initial state
  const initialNetBurn = projections[0]?.netBurn || 0;
  let runwayMonths: number | null = null;
  if (initialNetBurn > 0) {
    runwayMonths = runwayMonth || Math.ceil(cashOnHand / initialNetBurn);
  }
  
  // Cash out date
  let cashOutDate: string | null = null;
  if (runwayMonth) {
    const cashOutDateObj = new Date(now);
    cashOutDateObj.setMonth(cashOutDateObj.getMonth() + runwayMonth);
    cashOutDate = cashOutDateObj.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  }
  
  return {
    scenarioId: `sim-${Date.now()}`,
    scenarioName: name,
    projections,
    summary: {
      initialCash: cashOnHand,
      finalCash: projections[projections.length - 1]?.cashBalance || 0,
      avgMonthlyBurn,
      runwayMonths,
      cashOutDate,
      totalRevenue,
      totalExpenses,
    },
  };
}
