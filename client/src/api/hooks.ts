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
    mutationFn: ({ scenarioId, nSims }: { scenarioId: number; nSims?: number }) =>
      api.simulations.run(scenarioId, nSims),
    onSuccess: (_, { scenarioId }) => {
      queryClient.invalidateQueries({ queryKey: ['simulations', scenarioId] });
    },
  });
}

export function useSimulation(scenarioId: number | null) {
  return useQuery({
    queryKey: ['simulations', scenarioId],
    queryFn: () => api.simulations.latest(scenarioId!),
    enabled: !!scenarioId,
    retry: false,
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
  
  return useMutation({
    mutationFn: ({ companyId, data }: { companyId: number; data: any }) =>
      api.datasets.manualBaseline(companyId, data),
    onSuccess: (_, { companyId }) => {
      queryClient.invalidateQueries({ queryKey: ['companies', companyId] });
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
