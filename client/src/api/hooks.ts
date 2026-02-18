import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from './client';
import { useFounderStore } from '../store/founderStore';

export function useCompanies() {
  return useQuery({
    queryKey: ['companies'],
    queryFn: () => api.companies.list(),
  });
}

export function useCompany(id: number) {
  return useQuery({
    queryKey: ['companies', id],
    queryFn: () => api.companies.get(id),
    enabled: !!id,
  });
}

export function useCreateCompany() {
  const queryClient = useQueryClient();
  const setCurrentCompany = useFounderStore((s) => s.setCurrentCompany);
  
  return useMutation({
    mutationFn: api.companies.create,
    onSuccess: (company) => {
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      setCurrentCompany(company);
    },
  });
}

export function useUpdateCompany() {
  const queryClient = useQueryClient();
  const { currentCompany, setCurrentCompany } = useFounderStore();
  
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: { name?: string; website?: string; industry?: string; stage?: string; currency?: string } }) =>
      api.companies.update(id, data),
    onSuccess: (updatedCompany) => {
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      if (currentCompany?.id === updatedCompany.id) {
        setCurrentCompany(updatedCompany);
      }
    },
  });
}

export function useDeleteCompany() {
  const queryClient = useQueryClient();
  const { currentCompany, setCurrentCompany } = useFounderStore();
  
  return useMutation({
    mutationFn: (id: number) => api.companies.delete(id),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      if (currentCompany?.id === deletedId) {
        setCurrentCompany(null);
      }
    },
  });
}

export function useComputedMetrics(companyId: number | null) {
  return useQuery({
    queryKey: ['computed-metrics', companyId],
    queryFn: () => api.metrics.computed(companyId!),
    enabled: !!companyId,
    staleTime: 30_000,
    retry: 2,
    retryDelay: 1000,
  });
}

export function useTruthScan(companyId: number | null) {
  return useQuery({
    queryKey: ['truth', companyId],
    queryFn: () => api.truth.latest(companyId!),
    enabled: !!companyId,
    retry: false,
  });
}

export function useRunTruthScan() {
  const queryClient = useQueryClient();
  const setTruthScan = useFounderStore((s) => s.setTruthScan);
  
  return useMutation({
    mutationFn: (companyId: number) => api.truth.run(companyId),
    onSuccess: (data, companyId) => {
      queryClient.invalidateQueries({ queryKey: ['truth', companyId] });
      setTruthScan(data);
    },
  });
}

export function useScenarios(companyId: number | null) {
  return useQuery({
    queryKey: ['scenarios', companyId],
    queryFn: () => api.scenarios.list(companyId!),
    enabled: !!companyId,
  });
}

export function useCreateScenario() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ companyId, data }: { companyId: number; data: any }) =>
      api.scenarios.create(companyId, data),
    onSuccess: (_, { companyId }) => {
      queryClient.invalidateQueries({ queryKey: ['scenarios', companyId] });
    },
  });
}

export function useRunSimulation() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ scenarioId, nSims, seed }: { scenarioId: number; nSims?: number; seed?: number }) =>
      api.simulations.run(scenarioId, nSims, seed),
    onSuccess: (_, { scenarioId }) => {
      queryClient.invalidateQueries({ queryKey: ['simulations', scenarioId] });
      queryClient.invalidateQueries({ queryKey: ['timeseries', scenarioId] });
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });
    },
  });
}

export function useCounterMoves(scenarioId: number | null) {
  return useMutation({
    mutationFn: () => api.simulations.counterMoves(scenarioId!),
  });
}

export function useSimulation(scenarioId: number | null) {
  return useQuery({
    queryKey: ['simulations', scenarioId],
    queryFn: () => api.simulations.latest(scenarioId!),
    enabled: !!scenarioId,
    retry: (failureCount, error: any) => {
      if (error?.message?.includes('404') || error?.status === 404) return false;
      return failureCount < 2;
    },
    retryDelay: 1000,
  });
}

export function useScenarioTimeseries(scenarioId: number | null) {
  return useQuery({
    queryKey: ['timeseries', scenarioId],
    queryFn: () => api.simulations.getTimeseries(scenarioId!),
    enabled: !!scenarioId,
    retry: (failureCount, error: any) => {
      if (error?.message?.includes('404') || error?.status === 404) return false;
      return failureCount < 2;
    },
    retryDelay: 1000,
  });
}

export function useGenerateDecisions() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (runId: number) => api.decisions.generate(runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['decisions'] });
    },
  });
}

export function useDecisions(companyId: number | null) {
  return useQuery({
    queryKey: ['decisions', companyId],
    queryFn: () => api.decisions.latest(companyId!),
    enabled: !!companyId,
    retry: false,
  });
}

export function useStrategicDiagnosis() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (companyId: number) => api.decisions.regenerateDiagnosis(companyId),
    onSuccess: (data, companyId) => {
      queryClient.setQueryData(['strategic-diagnosis', companyId], data);
    },
  });
}

export function useStrategicDiagnosisQuery(companyId: number | null, enabled: boolean) {
  return useQuery({
    queryKey: ['strategic-diagnosis', companyId],
    queryFn: async () => {
      const result = await api.decisions.strategicDiagnosis(companyId!);
      return result;
    },
    enabled: !!companyId && enabled,
    retry: false,
    staleTime: Infinity,
    gcTime: 30 * 60 * 1000,
    placeholderData: (previousData: any) => previousData,
  });
}

export function useContext(companyId: number | null) {
  return useQuery({
    queryKey: ['context', companyId],
    queryFn: () => api.copilot.context(companyId!),
    enabled: !!companyId,
    retry: false,
  });
}

export function useQuickSimulate() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ companyId, deltas }: { companyId: number; deltas: any }) =>
      api.copilot.simulate(companyId, deltas),
    onSuccess: (_, { companyId }) => {
      queryClient.invalidateQueries({ queryKey: ['context', companyId] });
    },
  });
}

export function useManualBaseline() {
  const queryClient = useQueryClient();
  const setFinancialBaseline = useFounderStore((s) => s.setFinancialBaseline);
  
  return useMutation({
    mutationFn: ({ companyId, data }: { companyId: number; data: any }) =>
      api.datasets.manualBaseline(companyId, data),
    onSuccess: (_, { companyId, data }) => {
      queryClient.invalidateQueries({ queryKey: ['companies', companyId] });
      queryClient.invalidateQueries({ queryKey: ['truth', companyId] });
      
      // Sync onboarding data to store's financialBaseline format
      const totalExpenses = (data.opex || 0) + (data.payroll || 0) + (data.other_costs || 0);
      setFinancialBaseline({
        cashOnHand: data.cash_balance || null,
        monthlyRevenue: data.monthly_revenue || null,
        totalMonthlyExpenses: totalExpenses || null,
        monthlyGrowthRate: data.growth_rate || null,
        expenseBreakdown: {
          payroll: data.payroll || null,
          marketing: null, // Not captured in onboarding
          operating: data.opex || null,
          cogs: null,
          otherOpex: data.other_costs || null,
        },
        hasManualExpenseOverride: false,
        currency: 'USD',
        asOfDate: new Date().toISOString().split('T')[0],
      });
    },
  });
}

export function useMultiScenarioSimulation() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ companyId, options }: { 
      companyId: number; 
      options?: { 
        n_sims?: number; 
        horizon_months?: number; 
        scenario_keys?: string[];
        seed?: number;
      } 
    }) => api.simulations.runMulti(companyId, options),
    onSuccess: (_, { companyId }) => {
      queryClient.invalidateQueries({ queryKey: ['multi-simulation', companyId] });
    },
  });
}

export function useDefaultScenarios(companyId: number | null) {
  return useQuery({
    queryKey: ['default-scenarios', companyId],
    queryFn: () => api.simulations.getDefaultScenarios(companyId!),
    enabled: !!companyId,
  });
}

export function useEnhancedSimulation() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ companyId, options }: { 
      companyId: number; 
      options: Parameters<typeof api.simulations.runEnhanced>[1]
    }) => api.simulations.runEnhanced(companyId, options),
    onSuccess: (_, { companyId }) => {
      queryClient.invalidateQueries({ queryKey: ['enhanced-simulation', companyId] });
    },
  });
}

export function useEnhancedMultiScenarioSimulation() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ companyId, options }: { 
      companyId: number; 
      options: Parameters<typeof api.simulations.runEnhancedMulti>[1]
    }) => api.simulations.runEnhancedMulti(companyId, options),
    onSuccess: (_, { companyId }) => {
      queryClient.invalidateQueries({ queryKey: ['enhanced-multi-simulation', companyId] });
    },
  });
}

export function useSensitivityAnalysis() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ companyId, targetRunway, targetProbability }: { 
      companyId: number; 
      targetRunway?: number;
      targetProbability?: number;
    }) => api.simulations.runSensitivityAnalysis(companyId, targetRunway, targetProbability),
    onSuccess: (_, { companyId }) => {
      queryClient.invalidateQueries({ queryKey: ['sensitivity', companyId] });
    },
  });
}

export function useTerminaPdfUpload() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ companyId, file, saveAsBaseline }: { 
      companyId: number; 
      file: File;
      saveAsBaseline?: boolean;
    }) => api.datasets.uploadTerminaPdf(companyId, file, saveAsBaseline),
    onSuccess: (_, { companyId }) => {
      queryClient.invalidateQueries({ queryKey: ['companies', companyId] });
      queryClient.invalidateQueries({ queryKey: ['truth', companyId] });
    },
  });
}

export function useTerminaExcelUpload() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ companyId, file, saveAsBaseline }: { 
      companyId: number; 
      file: File;
      saveAsBaseline?: boolean;
    }) => api.datasets.uploadTerminaExcel(companyId, file, saveAsBaseline),
    onSuccess: (_, { companyId }) => {
      queryClient.invalidateQueries({ queryKey: ['companies', companyId] });
      queryClient.invalidateQueries({ queryKey: ['truth', companyId] });
    },
  });
}

export function useBenchmarkSearch(industry: string | null, stage: string | null) {
  return useQuery({
    queryKey: ['benchmarks', industry, stage],
    queryFn: () => api.benchmarks.search(industry!, stage!),
    enabled: !!industry && !!stage,
    staleTime: 1000 * 60 * 60,
    gcTime: 1000 * 60 * 60 * 24,
  });
}

export function useBenchmarkIndustries() {
  return useQuery({
    queryKey: ['benchmark-industries'],
    queryFn: () => api.benchmarks.industries(),
    staleTime: 1000 * 60 * 60 * 24,
  });
}

export function useClearBenchmarkCache() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: () => api.benchmarks.clearCache(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['benchmarks'] });
    },
  });
}
