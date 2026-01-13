import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: number;
  email: string;
}

interface Company {
  id: number;
  name: string;
  website?: string;
  industry?: string;
  stage?: string;
  currency: string;
}

interface TruthScan {
  id: number;
  metrics: Record<string, any>;
  flags: Array<{ severity: string; title: string; description: string }>;
  data_confidence_score: number;
  quality_of_growth_index: number;
  benchmark_comparisons: any[];
  computed_at: string;
}

export interface FinancialBaseline {
  cashOnHand: number | null;
  monthlyRevenue: number | null;
  totalMonthlyExpenses: number | null;
  monthlyGrowthRate: number | null;
  expenseBreakdown: {
    payroll: number | null;
    marketing: number | null;
    operating: number | null;
    cogs: number | null;
    otherOpex: number | null;
  };
  hasManualExpenseOverride?: boolean;
  currency: string | null;
  asOfDate: string | null;
}

export interface ExtractionField {
  value: number | string | null;
  confidence: number;
  evidence: string | null;
}

export interface ExtractionResult {
  extracted: Record<string, ExtractionField>;
  normalized: FinancialBaseline;
  missingFields: string[];
  confidence: Record<string, number>;
  source: 'pdf' | 'excel';
  fileName: string;
  uploadId?: number;
}

interface FounderState {
  token: string | null;
  user: User | null;
  currentCompany: Company | null;
  companies: Company[];
  truthScan: TruthScan | null;
  currentStep: 'truth' | 'simulation' | 'decision';
  investorModeEnabled: boolean;
  
  financialBaseline: FinancialBaseline | null;
  lastExtraction: ExtractionResult | null;
  extractionInProgress: boolean;
  
  setToken: (token: string | null) => void;
  setUser: (user: User | null) => void;
  setCurrentCompany: (company: Company | null) => void;
  setCompanies: (companies: Company[]) => void;
  setTruthScan: (scan: TruthScan | null) => void;
  setCurrentStep: (step: 'truth' | 'simulation' | 'decision') => void;
  logout: () => void;
  
  setFinancialBaseline: (baseline: FinancialBaseline) => void;
  setLastExtraction: (extraction: ExtractionResult | null) => void;
  setExtractionInProgress: (inProgress: boolean) => void;
  clearFinancialBaseline: () => void;
  
  getCalculatedMetrics: () => { netBurnRate: number; runwayMonths: number | null };
}

const EMPTY_BASELINE: FinancialBaseline = {
  cashOnHand: null,
  monthlyRevenue: null,
  totalMonthlyExpenses: null,
  monthlyGrowthRate: null,
  expenseBreakdown: {
    payroll: null,
    marketing: null,
    operating: null,
    cogs: null,
    otherOpex: null,
  },
  hasManualExpenseOverride: false,
  currency: null,
  asOfDate: null,
};

export const useFounderStore = create<FounderState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      currentCompany: null,
      companies: [],
      truthScan: null,
      currentStep: 'truth',
      investorModeEnabled: false,
      
      financialBaseline: null,
      lastExtraction: null,
      extractionInProgress: false,
      
      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
      setCurrentCompany: (company) => set({ currentCompany: company }),
      setCompanies: (companies) => set({ companies }),
      setTruthScan: (scan) => set({ truthScan: scan }),
      setCurrentStep: (step) => set({ currentStep: step }),
      logout: () => set({ 
        token: null, 
        user: null, 
        currentCompany: null, 
        companies: [], 
        truthScan: null,
        financialBaseline: null,
        lastExtraction: null,
      }),
      
      setFinancialBaseline: (baseline) => set({ financialBaseline: baseline }),
      setLastExtraction: (extraction) => set({ lastExtraction: extraction }),
      setExtractionInProgress: (inProgress) => set({ extractionInProgress: inProgress }),
      clearFinancialBaseline: () => set({ 
        financialBaseline: null, 
        lastExtraction: null 
      }),
      
      getCalculatedMetrics: () => {
        const baseline = get().financialBaseline;
        if (!baseline) {
          return { netBurnRate: 0, runwayMonths: null, isProfitable: false, isSustainable: false };
        }
        
        const revenue = baseline.monthlyRevenue || 0;
        const cash = baseline.cashOnHand || 0;
        
        const breakdownSum = 
          (baseline.expenseBreakdown?.payroll || 0) +
          (baseline.expenseBreakdown?.marketing || 0) +
          (baseline.expenseBreakdown?.operating || 0) +
          (baseline.expenseBreakdown?.cogs || 0) +
          (baseline.expenseBreakdown?.otherOpex || 0);
        
        const expenses = baseline.hasManualExpenseOverride
          ? (baseline.totalMonthlyExpenses || 0)
          : (breakdownSum > 0 ? breakdownSum : (baseline.totalMonthlyExpenses || 0));
        
        const netBurnRate = expenses - revenue;
        const isProfitable = netBurnRate < 0;
        const isSustainable = netBurnRate <= 0;
        const runwayMonths = netBurnRate > 0 ? cash / netBurnRate : null;
        
        return { netBurnRate, runwayMonths, isProfitable, isSustainable };
      },
    }),
    {
      name: 'predixen-founder-storage',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        currentCompany: state.currentCompany,
        financialBaseline: state.financialBaseline,
      }),
    }
  )
);
