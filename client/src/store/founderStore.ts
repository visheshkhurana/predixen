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

interface FounderState {
  token: string | null;
  user: User | null;
  currentCompany: Company | null;
  companies: Company[];
  truthScan: TruthScan | null;
  currentStep: 'truth' | 'simulation' | 'decision';
  investorModeEnabled: boolean;
  
  setToken: (token: string | null) => void;
  setUser: (user: User | null) => void;
  setCurrentCompany: (company: Company | null) => void;
  setCompanies: (companies: Company[]) => void;
  setTruthScan: (scan: TruthScan | null) => void;
  setCurrentStep: (step: 'truth' | 'simulation' | 'decision') => void;
  logout: () => void;
}

export const useFounderStore = create<FounderState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      currentCompany: null,
      companies: [],
      truthScan: null,
      currentStep: 'truth',
      investorModeEnabled: false,
      
      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
      setCurrentCompany: (company) => set({ currentCompany: company }),
      setCompanies: (companies) => set({ companies }),
      setTruthScan: (scan) => set({ truthScan: scan }),
      setCurrentStep: (step) => set({ currentStep: step }),
      logout: () => set({ token: null, user: null, currentCompany: null, companies: [], truthScan: null }),
    }),
    {
      name: 'predixen-founder-storage',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        currentCompany: state.currentCompany,
      }),
    }
  )
);
