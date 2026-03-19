import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSEO } from "@/lib/seo";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { useFounderStore } from '@/store/founderStore';
import { getErrorMessage } from '@/lib/errors';
import { apiRequest } from '@/lib/queryClient';
import {
  Plus, PieChart, Users, TrendingUp, FileText, Building2,
  ArrowRightLeft, Award, AlertTriangle,
  Calculator, ChevronDown, ChevronUp, Shield,
  Download, BarChart3, Layers, ScrollText, FlaskConical,
  Trash2, Briefcase
} from 'lucide-react';
import { EmptyStateCard } from '@/components/ui/empty-state';
import { trackEvent } from '@/lib/posthog';
import {
  PieChart as RechartsPie, Pie, Cell, ResponsiveContainer, Tooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid
} from 'recharts';

interface ShareholderData {
  id: string;
  name: string;
  email: string | null;
  type: string;
  relationship_type: string | null;
  is_active: boolean;
  total_shares: number;
  total_options_granted: number;
  total_options_vested: number;
  tax_id?: string;
  address?: string;
}

interface OwnershipEntry {
  shareholder_id: string;
  name: string;
  type: string;
  common_shares: number;
  preferred_shares: number;
  options_granted: number;
  options_vested: number;
  options_exercised: number;
  total_fully_diluted: number;
  ownership_percent: number;
}

interface CapTableSummary {
  total_shares_issued: number;
  total_options_granted: number;
  total_options_vested: number;
  total_options_exercised: number;
  total_options_unvested: number;
  fully_diluted_shares: number;
  ownership: OwnershipEntry[];
  latest_409a: any;
}

interface GrantData {
  id: string;
  shareholder_name: string;
  grant_type: string;
  shares_granted: number;
  exercise_price: number;
  grant_date: string | null;
  vesting_type: string;
  shares_vested: number;
  shares_exercised: number;
  shares_unvested: number;
  shares_exercisable: number;
  status: string;
}

interface TransactionData {
  id: string;
  transaction_type: string;
  from_shareholder_name: string | null;
  to_shareholder_name: string | null;
  share_class: string | null;
  shares: number;
  price_per_share: number | null;
  total_value: number | null;
  effective_date: string | null;
  notes: string | null;
  created_at: string;
}

interface ConvertibleData {
  id: string;
  type: string;
  holder: string;
  principal: number;
  valuation_cap: number | null;
  discount_rate: number | null;
  interest_rate: number | null;
  maturity_date: string | null;
  conversion_status: string;
  terms_json: any;
}

interface ScenarioData {
  id: string;
  name: string;
  description: string | null;
  scenario_type: string;
  inputs_json: any;
  results_json: any;
  created_at: string;
  updated_at: string;
}

interface AuditLogData {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  user_id: string | null;
  changes_json: any;
  timestamp: string;
}

const OWNERSHIP_COLORS = [
  '#10b981', '#059669', '#047857', '#065f46',
  '#6366f1', '#8b5cf6', '#a855f7', '#d946ef',
  '#3b82f6', '#06b6d4', '#14b8a6', '#f59e0b',
];

const SHAREHOLDER_TYPES = [
  { value: 'founder', label: 'Founder' },
  { value: 'employee', label: 'Employee' },
  { value: 'investor', label: 'Investor' },
  { value: 'advisor', label: 'Advisor' },
  { value: 'board_member', label: 'Board Member' },
  { value: 'contractor', label: 'Contractor' },
];

const GRANT_TYPES = [
  { value: 'iso', label: 'ISO (Incentive Stock Option)' },
  { value: 'nso', label: 'NSO (Non-Qualified Stock Option)' },
  { value: 'rsa', label: 'RSA (Restricted Stock Award)' },
  { value: 'rsu', label: 'RSU (Restricted Stock Unit)' },
];

const VESTING_TYPES = [
  { value: '4y_1y_cliff', label: '4-Year with 1-Year Cliff' },
  { value: 'monthly_no_cliff', label: 'Monthly (No Cliff)' },
  { value: 'custom', label: 'Custom Schedule' },
];

const SCENARIO_TYPES = [
  { value: 'new_round', label: 'New Round' },
  { value: 'option_pool', label: 'Option Pool Expansion' },
  { value: 'exit_waterfall', label: 'Exit / Waterfall' },
  { value: 'secondary_sale', label: 'Secondary Sale' },
];

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

function formatCurrency(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);
}

function TypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    founder: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
    employee: 'bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/30',
    investor: 'bg-violet-500/15 text-violet-600 dark:text-violet-400 border-violet-500/30',
    advisor: 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30',
    board_member: 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 border-cyan-500/30',
    contractor: 'bg-gray-500/15 text-gray-600 dark:text-gray-400 border-gray-500/30',
  };
  return (
    <Badge variant="outline" className={colors[type] || colors.contractor}>
      {type.replace('_', ' ')}
    </Badge>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
    exercised: 'bg-blue-500/15 text-blue-600 dark:text-blue-400',
    cancelled: 'bg-red-500/15 text-red-600 dark:text-red-400',
    expired: 'bg-gray-500/15 text-gray-600 dark:text-gray-400',
    draft: 'bg-yellow-500/15 text-yellow-600 dark:text-yellow-400',
    pending: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
    converted: 'bg-violet-500/15 text-violet-600 dark:text-violet-400',
  };
  return <Badge className={colors[status] || colors.draft}>{status}</Badge>;
}

function TxTypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    issuance: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
    transfer: 'bg-blue-500/15 text-blue-600 dark:text-blue-400',
    exercise: 'bg-violet-500/15 text-violet-600 dark:text-violet-400',
    cancellation: 'bg-red-500/15 text-red-600 dark:text-red-400',
    conversion: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
    repurchase: 'bg-gray-500/15 text-gray-600 dark:text-gray-400',
  };
  return <Badge className={colors[type] || 'bg-gray-500/15 text-gray-600 dark:text-gray-400'}>{type}</Badge>;
}

function ScenarioTypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    new_round: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
    option_pool: 'bg-blue-500/15 text-blue-600 dark:text-blue-400',
    exit_waterfall: 'bg-violet-500/15 text-violet-600 dark:text-violet-400',
    secondary_sale: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  };
  return <Badge className={colors[type] || 'bg-gray-500/15 text-gray-600 dark:text-gray-400'}>{type.replace('_', ' ')}</Badge>;
}

type OwnershipView = 'fully_diluted' | 'by_class' | 'as_converted' | 'as_exercised';

export default function CapTablePage() {
  useSEO({
    title: "Cap Table Management — Equity Tracking for Startups | FounderConsole",
    description: "Manage your cap table with real-time ownership visualization. Model SAFE and convertible note conversions, track dilution, and generate investor-ready reports.",
    path: "/cap-table",
    robots: "noindex, nofollow",
  });
  const { currentCompany } = useFounderStore();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const companyId = currentCompany?.id;

  const [activeTab, setActiveTab] = useState('overview');
  const [ownershipView, setOwnershipView] = useState<OwnershipView>('fully_diluted');
  const [expandedShareholder, setExpandedShareholder] = useState<string | null>(null);
  const [txTypeFilter, setTxTypeFilter] = useState<string>('all');
  const [sortColumn, setSortColumn] = useState<string>('ownership_percent');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const [showShareholderDialog, setShowShareholderDialog] = useState(false);
  const [showIssueDialog, setShowIssueDialog] = useState(false);
  const [showGrantDialog, setShowGrantDialog] = useState(false);
  const [showTransferDialog, setShowTransferDialog] = useState(false);
  const [showExerciseDialog, setShowExerciseDialog] = useState(false);
  const [showConvertibleDialog, setShowConvertibleDialog] = useState(false);
  const [showScenarioDialog, setShowScenarioDialog] = useState(false);
  const [showWaterfallDialog, setShowWaterfallDialog] = useState(false);
  const [selectedGrantId, setSelectedGrantId] = useState<string | null>(null);

  const [newShareholder, setNewShareholder] = useState({ name: '', email: '', type: 'founder', tax_id: '', address: '' });
  const [issueData, setIssueData] = useState({
    shareholder_id: '', share_class: 'common', series: '', shares: '', price_per_share: '', notes: ''
  });
  const [grantData, setGrantData] = useState({
    shareholder_id: '', grant_type: 'iso', shares_granted: '', exercise_price: '',
    vesting_type: '4y_1y_cliff', cliff_months: '12', vesting_months: '48', grant_date: '', notes: ''
  });
  const [transferData, setTransferData] = useState({
    from_shareholder_id: '', to_shareholder_id: '', holding_id: '', shares: '', price_per_share: '', notes: ''
  });
  const [exerciseData, setExerciseData] = useState({ shares_to_exercise: '', notes: '' });
  const [convertibleData, setConvertibleData] = useState({
    type: 'safe', holder: '', principal: '', valuation_cap: '', discount_rate: '', interest_rate: '', maturity_date: '', terms_json: ''
  });
  const [scenarioFormData, setScenarioFormData] = useState({
    name: '', description: '', scenario_type: 'new_round',
    pre_money: '', raise_amount: '', option_pool_refresh: '', investor_name: '', exit_value: ''
  });
  const [waterfallExitValue, setWaterfallExitValue] = useState('');
  const [waterfallResult, setWaterfallResult] = useState<any>(null);
  const [lastScenarioResult, setLastScenarioResult] = useState<any>(null);

  const { data: summaryData, isLoading: summaryLoading } = useQuery<CapTableSummary>({
    queryKey: ['/api/companies', companyId, 'cap-table', 'summary'],
    queryFn: async () => {
      const res = await apiRequest('GET', `/api/companies/${companyId}/cap-table/summary`);
      return res.json();
    },
    enabled: !!companyId,
  });

  const { data: shareholdersData, isLoading: shareholdersLoading } = useQuery({
    queryKey: ['/api/companies', companyId, 'cap-table', 'shareholders'],
    queryFn: async () => {
      const res = await apiRequest('GET', `/api/companies/${companyId}/cap-table/shareholders`);
      return res.json();
    },
    enabled: !!companyId,
  });

  const { data: holdingsData } = useQuery({
    queryKey: ['/api/companies', companyId, 'cap-table', 'holdings'],
    queryFn: async () => {
      const res = await apiRequest('GET', `/api/companies/${companyId}/cap-table/holdings`);
      return res.json();
    },
    enabled: !!companyId,
  });

  const { data: grantsData, isLoading: grantsLoading } = useQuery({
    queryKey: ['/api/companies', companyId, 'cap-table', 'grants'],
    queryFn: async () => {
      const res = await apiRequest('GET', `/api/companies/${companyId}/cap-table/grants`);
      return res.json();
    },
    enabled: !!companyId,
  });

  const { data: transactionsData, isLoading: transactionsLoading } = useQuery({
    queryKey: ['/api/companies', companyId, 'cap-table', 'transactions'],
    queryFn: async () => {
      const res = await apiRequest('GET', `/api/companies/${companyId}/cap-table/transactions`);
      return res.json();
    },
    enabled: !!companyId,
  });

  const { data: valuationsData } = useQuery({
    queryKey: ['/api/companies', companyId, 'cap-table', 'valuations'],
    queryFn: async () => {
      const res = await apiRequest('GET', `/api/companies/${companyId}/cap-table/valuations`);
      return res.json();
    },
    enabled: !!companyId,
  });

  const { data: convertiblesData, isLoading: convertiblesLoading } = useQuery({
    queryKey: ['/api/companies', companyId, 'cap-table', 'convertibles'],
    queryFn: async () => {
      const res = await apiRequest('GET', `/api/companies/${companyId}/cap-table/convertibles`);
      return res.json();
    },
    enabled: !!companyId,
  });

  const { data: scenariosData, isLoading: scenariosLoading } = useQuery({
    queryKey: ['/api/companies', companyId, 'cap-table', 'scenarios'],
    queryFn: async () => {
      const res = await apiRequest('GET', `/api/companies/${companyId}/cap-table/scenarios`);
      return res.json();
    },
    enabled: !!companyId,
  });

  const { data: auditLogData, isLoading: auditLogLoading } = useQuery({
    queryKey: ['/api/companies', companyId, 'cap-table', 'audit-log'],
    queryFn: async () => {
      const res = await apiRequest('GET', `/api/companies/${companyId}/cap-table/audit-log`);
      return res.json();
    },
    enabled: !!companyId,
  });

  const { data: summary409aData } = useQuery({
    queryKey: ['/api/companies', companyId, 'cap-table', 'summary-409a'],
    queryFn: async () => {
      const res = await apiRequest('GET', `/api/companies/${companyId}/cap-table/summary-409a`);
      return res.json();
    },
    enabled: !!companyId,
  });

  const viewEndpoint = ownershipView === 'fully_diluted' ? 'views/fully-diluted'
    : ownershipView === 'by_class' ? 'views/by-class'
    : ownershipView === 'as_converted' ? 'views/as-converted'
    : 'views/as-exercised';

  const { data: viewData, isLoading: viewLoading } = useQuery({
    queryKey: ['/api/companies', companyId, 'cap-table', viewEndpoint],
    queryFn: async () => {
      const res = await apiRequest('GET', `/api/companies/${companyId}/cap-table/${viewEndpoint}`);
      return res.json();
    },
    enabled: !!companyId && ownershipView !== 'fully_diluted',
  });

  const shareholders: ShareholderData[] = Array.isArray(shareholdersData?.shareholders) ? shareholdersData.shareholders : [];
  const grants: GrantData[] = Array.isArray(grantsData?.grants) ? grantsData.grants : [];
  const transactions: TransactionData[] = Array.isArray(transactionsData?.transactions) ? transactionsData.transactions : [];
  const holdings = Array.isArray(holdingsData?.holdings) ? holdingsData.holdings : [];
  const valuations = Array.isArray(valuationsData?.valuations) ? valuationsData.valuations : [];
  const convertibles: ConvertibleData[] = Array.isArray(convertiblesData?.convertibles) ? convertiblesData.convertibles : [];
  const scenarios: ScenarioData[] = Array.isArray(scenariosData?.scenarios) ? scenariosData.scenarios : [];
  const auditLog: AuditLogData[] = Array.isArray(auditLogData?.entries) ? auditLogData.entries : Array.isArray(auditLogData?.audit_log) ? auditLogData.audit_log : [];
  const summary = summaryData;

  const filteredTransactions = useMemo(() => {
    if (txTypeFilter === 'all') return transactions;
    return transactions.filter(tx => tx.transaction_type === txTypeFilter);
  }, [transactions, txTypeFilter]);

  const sortedOwnership = useMemo(() => {
    if (!summary?.ownership?.length) return [];
    const sorted = [...summary.ownership];
    sorted.sort((a: any, b: any) => {
      const aVal = a[sortColumn] ?? 0;
      const bVal = b[sortColumn] ?? 0;
      return sortDir === 'desc' ? bVal - aVal : aVal - bVal;
    });
    return sorted;
  }, [summary, sortColumn, sortDir]);

  const pieData = useMemo(() => {
    if (ownershipView === 'by_class' && viewData?.classes) {
      return viewData.classes.map((c: any) => ({
        name: c.share_class + (c.series ? ` (${c.series})` : ''),
        value: c.percent,
        shares: c.total_shares,
      }));
    }
    if (ownershipView === 'as_converted' && viewData?.as_converted) {
      return viewData.as_converted.map((v: any) => ({
        name: v.name,
        value: v.percent,
        shares: v.converted_shares,
      }));
    }
    if (ownershipView === 'as_exercised' && viewData?.as_exercised) {
      return viewData.as_exercised.map((v: any) => ({
        name: v.name,
        value: v.percent,
        shares: v.total_shares,
      }));
    }
    if (!summary?.ownership?.length) return [];
    return summary.ownership.map((o: OwnershipEntry) => ({
      name: o.name,
      value: o.ownership_percent,
      shares: o.total_fully_diluted,
    }));
  }, [summary, ownershipView, viewData]);

  const handleSort = (col: string) => {
    if (sortColumn === col) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(col);
      setSortDir('desc');
    }
  };

  const createShareholderMutation = useMutation({
    mutationFn: async (data: any) => {
      const res = await apiRequest('POST', `/api/companies/${companyId}/cap-table/shareholders`, data);
      return res.json();
    },
    onSuccess: () => {
      trackEvent('captable_createShareholder', {});
      queryClient.invalidateQueries({ queryKey: ['/api/companies', companyId, 'cap-table'] });
      toast({ title: 'Shareholder Added' });
      setShowShareholderDialog(false);
      setNewShareholder({ name: '', email: '', type: 'founder', tax_id: '', address: '' });
    },
    onError: (e: unknown) => toast({ title: 'Error', description: getErrorMessage(e), variant: 'destructive' }),
  });

  const issueEquityMutation = useMutation({
    mutationFn: async (data: any) => {
      const res = await apiRequest('POST', `/api/companies/${companyId}/cap-table/issue`, data);
      return res.json();
    },
    onSuccess: () => {
      trackEvent('captable_issueEquity', {});
      queryClient.invalidateQueries({ queryKey: ['/api/companies', companyId, 'cap-table'] });
      toast({ title: 'Equity Issued' });
      setShowIssueDialog(false);
      setIssueData({ shareholder_id: '', share_class: 'common', series: '', shares: '', price_per_share: '', notes: '' });
    },
    onError: (e: unknown) => toast({ title: 'Error', description: getErrorMessage(e), variant: 'destructive' }),
  });

  const createGrantMutation = useMutation({
    mutationFn: async (data: any) => {
      const res = await apiRequest('POST', `/api/companies/${companyId}/cap-table/grants`, data);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/companies', companyId, 'cap-table'] });
      toast({ title: 'Option Grant Created' });
      setShowGrantDialog(false);
      setGrantData({ shareholder_id: '', grant_type: 'iso', shares_granted: '', exercise_price: '', vesting_type: '4y_1y_cliff', cliff_months: '12', vesting_months: '48', grant_date: '', notes: '' });
    },
    onError: (e: unknown) => toast({ title: 'Error', description: getErrorMessage(e), variant: 'destructive' }),
  });

  const transferMutation = useMutation({
    mutationFn: async (data: any) => {
      const res = await apiRequest('POST', `/api/companies/${companyId}/cap-table/transfer`, data);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/companies', companyId, 'cap-table'] });
      toast({ title: 'Transfer Complete' });
      setShowTransferDialog(false);
      setTransferData({ from_shareholder_id: '', to_shareholder_id: '', holding_id: '', shares: '', price_per_share: '', notes: '' });
    },
    onError: (e: unknown) => toast({ title: 'Error', description: getErrorMessage(e), variant: 'destructive' }),
  });

  const exerciseMutation = useMutation({
    mutationFn: async (data: any) => {
      const res = await apiRequest('POST', `/api/companies/${companyId}/cap-table/grants/${selectedGrantId}/exercise`, data);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/companies', companyId, 'cap-table'] });
      toast({ title: 'Options Exercised' });
      setShowExerciseDialog(false);
      setExerciseData({ shares_to_exercise: '', notes: '' });
      setSelectedGrantId(null);
    },
    onError: (e: unknown) => toast({ title: 'Error', description: getErrorMessage(e), variant: 'destructive' }),
  });

  const createConvertibleMutation = useMutation({
    mutationFn: async (data: any) => {
      const res = await apiRequest('POST', `/api/companies/${companyId}/cap-table/convertibles`, data);
      return res.json();
    },
    onSuccess: () => {
      trackEvent('captable_createConvertible', {});
      queryClient.invalidateQueries({ queryKey: ['/api/companies', companyId, 'cap-table'] });
      toast({ title: 'Convertible Security Created' });
      setShowConvertibleDialog(false);
      setConvertibleData({ type: 'safe', holder: '', principal: '', valuation_cap: '', discount_rate: '', interest_rate: '', maturity_date: '', terms_json: '' });
    },
    onError: (e: unknown) => toast({ title: 'Error', description: getErrorMessage(e), variant: 'destructive' }),
  });

  const createScenarioMutation = useMutation({
    mutationFn: async (data: any) => {
      const res = await apiRequest('POST', `/api/companies/${companyId}/cap-table/scenarios`, data);
      return res.json();
    },
    onSuccess: (data: any) => {
      trackEvent('captable_createScenario', {});
      queryClient.invalidateQueries({ queryKey: ['/api/companies', companyId, 'cap-table'] });
      toast({ title: 'Scenario Created' });
      setShowScenarioDialog(false);
      if (data?.results_json) setLastScenarioResult(data.results_json);
      setScenarioFormData({ name: '', description: '', scenario_type: 'new_round', pre_money: '', raise_amount: '', option_pool_refresh: '', investor_name: '', exit_value: '' });
    },
    onError: (e: unknown) => toast({ title: 'Error', description: getErrorMessage(e), variant: 'destructive' }),
  });

  const deleteScenarioMutation = useMutation({
    mutationFn: async (scenarioId: string) => {
      await apiRequest('DELETE', `/api/companies/${companyId}/cap-table/scenarios/${scenarioId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/companies', companyId, 'cap-table'] });
      toast({ title: 'Scenario Deleted' });
    },
    onError: (e: unknown) => toast({ title: 'Error', description: getErrorMessage(e), variant: 'destructive' }),
  });

  const waterfallMutation = useMutation({
    mutationFn: async (data: any) => {
      const res = await apiRequest('POST', `/api/companies/${companyId}/cap-table/waterfall`, data);
      return res.json();
    },
    onSuccess: (data: any) => {
      trackEvent('captable_waterfall', {});
      setWaterfallResult(data);
      toast({ title: 'Waterfall Analysis Complete' });
    },
    onError: (e: unknown) => toast({ title: 'Error', description: getErrorMessage(e), variant: 'destructive' }),
  });

  const handleExportCSV = async () => {
    try {
      const res = await apiRequest('GET', `/api/companies/${companyId}/cap-table/export/csv`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cap-table-${companyId}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      trackEvent('captable_exportCSV', {});
      toast({ title: 'CSV Exported' });
    } catch (e) {
      toast({ title: 'Export Failed', description: getErrorMessage(e), variant: 'destructive' });
    }
  };

  const handleExportJSON = async () => {
    try {
      const res = await apiRequest('GET', `/api/companies/${companyId}/cap-table/export/json`);
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cap-table-${companyId}.json`;
      a.click();
      URL.revokeObjectURL(url);
      trackEvent('captable_exportJSON', {});
      toast({ title: 'JSON Exported' });
    } catch (e) {
      toast({ title: 'Export Failed', description: getErrorMessage(e), variant: 'destructive' });
    }
  };

  if (!currentCompany) {
    return (
      <div className="p-6 flex items-center justify-center h-[60vh]">
        <Card className="max-w-md">
          <CardContent className="pt-6 text-center">
            <Building2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2" data-testid="text-no-company">No Company Selected</h3>
            <p className="text-muted-foreground">Select a company to manage your cap table.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-emerald-500/10 flex items-center justify-center">
            <PieChart className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold" data-testid="text-cap-table-title">Cap Table & Ownership</h1>
            <p className="text-muted-foreground text-sm">Equity management, scenarios, and compliance</p>
          </div>
        </div>
      </div>

      {summaryLoading ? (
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24" />)}
        </div>
      ) : summary && summary.fully_diluted_shares > 0 ? (
        <div className="grid gap-4 md:grid-cols-4">
          <Card data-testid="stat-fully-diluted">
            <CardContent className="pt-4 pb-4">
              <div className="flex items-center gap-2 mb-1">
                <Layers className="h-4 w-4 text-emerald-500" />
                <p className="text-sm text-muted-foreground">Fully Diluted Shares</p>
              </div>
              <p className="text-2xl font-bold">{formatNumber(summary.fully_diluted_shares)}</p>
              <p className="text-xs text-muted-foreground mt-1">{summary.total_shares_issued.toLocaleString()} issued</p>
            </CardContent>
          </Card>
          <Card data-testid="stat-shareholders">
            <CardContent className="pt-4 pb-4">
              <div className="flex items-center gap-2 mb-1">
                <Users className="h-4 w-4 text-blue-500" />
                <p className="text-sm text-muted-foreground">Total Shareholders</p>
              </div>
              <p className="text-2xl font-bold">{shareholders.length}</p>
              <p className="text-xs text-muted-foreground mt-1">{summary.ownership.length} with equity</p>
            </CardContent>
          </Card>
          <Card data-testid="stat-options">
            <CardContent className="pt-4 pb-4">
              <div className="flex items-center gap-2 mb-1">
                <Award className="h-4 w-4 text-violet-500" />
                <p className="text-sm text-muted-foreground">Options Outstanding</p>
              </div>
              <p className="text-2xl font-bold">{formatNumber(summary.total_options_granted - summary.total_options_exercised)}</p>
              <p className="text-xs text-muted-foreground mt-1">{formatNumber(summary.total_options_vested)} vested</p>
            </CardContent>
          </Card>
          <Card data-testid="stat-409a">
            <CardContent className="pt-4 pb-4">
              <div className="flex items-center gap-2 mb-1">
                <Shield className="h-4 w-4 text-amber-500" />
                <p className="text-sm text-muted-foreground">Latest 409A FMV</p>
              </div>
              {summary.latest_409a ? (
                <>
                  <p className="text-2xl font-bold">{formatCurrency(summary.latest_409a.price_per_share)}/sh</p>
                  <p className="text-xs text-muted-foreground mt-1">As of {summary.latest_409a.valuation_date}</p>
                </>
              ) : (
                <>
                  <p className="text-2xl font-bold text-muted-foreground">--</p>
                  <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">No 409A on file</p>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      ) : null}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <div className="overflow-x-auto">
          <TabsList className="inline-flex w-auto">
            <TabsTrigger value="overview" data-testid="tab-overview">
              <PieChart className="h-4 w-4 mr-1.5" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="stakeholders" data-testid="tab-stakeholders">
              <Users className="h-4 w-4 mr-1.5" />
              Stakeholders
            </TabsTrigger>
            <TabsTrigger value="securities" data-testid="tab-securities">
              <Layers className="h-4 w-4 mr-1.5" />
              Securities
            </TabsTrigger>
            <TabsTrigger value="transactions" data-testid="tab-transactions">
              <ArrowRightLeft className="h-4 w-4 mr-1.5" />
              Transactions
            </TabsTrigger>
            <TabsTrigger value="scenarios" data-testid="tab-scenarios">
              <FlaskConical className="h-4 w-4 mr-1.5" />
              Scenarios
            </TabsTrigger>
            <TabsTrigger value="reports" data-testid="tab-reports">
              <FileText className="h-4 w-4 mr-1.5" />
              Reports
            </TabsTrigger>
          </TabsList>
        </div>

        {/* ─── Overview Tab ──────────────────────────────────── */}
        <TabsContent value="overview" className="space-y-4">
          {!summary || summary.fully_diluted_shares === 0 ? (
            <EmptyStateCard
              icon={PieChart}
              title="No Equity Issued Yet"
              description="Add shareholders and issue equity to see your cap table. Start by adding founders and their share allocations."
              action={{
                label: "Add Shareholder",
                onClick: () => setShowShareholderDialog(true),
                icon: Plus,
              }}
            />
          ) : (
            <>
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                <h2 className="text-lg font-semibold">Ownership Overview</h2>
                <Select value={ownershipView} onValueChange={(v) => setOwnershipView(v as OwnershipView)}>
                  <SelectTrigger className="w-[200px]" data-testid="select-ownership-view">
                    <SelectValue placeholder="View" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="fully_diluted">Fully Diluted</SelectItem>
                    <SelectItem value="by_class">By Security Class</SelectItem>
                    <SelectItem value="as_converted">As-Converted</SelectItem>
                    <SelectItem value="as_exercised">As-Exercised</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-6 lg:grid-cols-5">
                <Card className="lg:col-span-2">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">Ownership Breakdown</CardTitle>
                    <CardDescription>
                      {ownershipView === 'fully_diluted' ? 'Fully diluted ownership by shareholder' :
                       ownershipView === 'by_class' ? 'Ownership grouped by security class' :
                       ownershipView === 'as_converted' ? 'All preferred converted to common equivalent' :
                       'Including all vested exercisable options'}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[320px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <RechartsPie>
                          <Pie
                            data={pieData}
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={110}
                            paddingAngle={2}
                            dataKey="value"
                            nameKey="name"
                          >
                            {pieData.map((_: any, idx: number) => (
                              <Cell key={idx} fill={OWNERSHIP_COLORS[idx % OWNERSHIP_COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip
                            formatter={(value: number) => `${value.toFixed(2)}%`}
                            contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px' }}
                          />
                          <Legend />
                        </RechartsPie>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>

                <Card className="lg:col-span-3">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">Ownership Table</CardTitle>
                    <CardDescription>
                      {ownershipView !== 'fully_diluted' && viewLoading ? 'Loading...' : 'Click column headers to sort'}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      {ownershipView === 'by_class' && viewData?.classes ? (
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Security Class</TableHead>
                              <TableHead>Series</TableHead>
                              <TableHead className="text-right">Total Shares</TableHead>
                              <TableHead className="text-right">% of Total</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {viewData.classes.map((c: any, i: number) => (
                              <TableRow key={i} data-testid={`row-class-${i}`}>
                                <TableCell className="font-medium capitalize">{c.share_class}</TableCell>
                                <TableCell className="text-muted-foreground">{c.series || '—'}</TableCell>
                                <TableCell className="text-right">{c.total_shares.toLocaleString()}</TableCell>
                                <TableCell className="text-right font-semibold">{c.percent.toFixed(2)}%</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      ) : ownershipView === 'as_converted' && viewData?.as_converted ? (
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Name</TableHead>
                              <TableHead className="text-right">Common</TableHead>
                              <TableHead className="text-right">Preferred → Common</TableHead>
                              <TableHead className="text-right">Total Converted</TableHead>
                              <TableHead className="text-right">%</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {viewData.as_converted.map((v: any) => (
                              <TableRow key={v.shareholder_id} data-testid={`row-converted-${v.shareholder_id}`}>
                                <TableCell className="font-medium">{v.name}</TableCell>
                                <TableCell className="text-right">{(v.original_common || 0).toLocaleString()}</TableCell>
                                <TableCell className="text-right">{(v.original_preferred || 0).toLocaleString()}</TableCell>
                                <TableCell className="text-right">{v.converted_shares.toLocaleString()}</TableCell>
                                <TableCell className="text-right font-semibold">{v.percent.toFixed(2)}%</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      ) : ownershipView === 'as_exercised' && viewData?.as_exercised ? (
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Name</TableHead>
                              <TableHead className="text-right">Equity Shares</TableHead>
                              <TableHead className="text-right">Exercisable Options</TableHead>
                              <TableHead className="text-right">Total</TableHead>
                              <TableHead className="text-right">%</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {viewData.as_exercised.map((v: any) => (
                              <TableRow key={v.shareholder_id} data-testid={`row-exercised-${v.shareholder_id}`}>
                                <TableCell className="font-medium">{v.name}</TableCell>
                                <TableCell className="text-right">{v.equity_shares.toLocaleString()}</TableCell>
                                <TableCell className="text-right">{v.exercisable_options.toLocaleString()}</TableCell>
                                <TableCell className="text-right">{v.total_shares.toLocaleString()}</TableCell>
                                <TableCell className="text-right font-semibold">{v.percent.toFixed(2)}%</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      ) : (
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead className="cursor-pointer" onClick={() => handleSort('name')} data-testid="sort-name">
                                Name {sortColumn === 'name' && (sortDir === 'asc' ? <ChevronUp className="inline h-3 w-3" /> : <ChevronDown className="inline h-3 w-3" />)}
                              </TableHead>
                              <TableHead>Type</TableHead>
                              <TableHead>Share Class</TableHead>
                              <TableHead className="text-right cursor-pointer" onClick={() => handleSort('total_fully_diluted')} data-testid="sort-shares">
                                Shares {sortColumn === 'total_fully_diluted' && (sortDir === 'asc' ? <ChevronUp className="inline h-3 w-3" /> : <ChevronDown className="inline h-3 w-3" />)}
                              </TableHead>
                              <TableHead className="text-right cursor-pointer" onClick={() => handleSort('ownership_percent')} data-testid="sort-ownership">
                                % Ownership {sortColumn === 'ownership_percent' && (sortDir === 'asc' ? <ChevronUp className="inline h-3 w-3" /> : <ChevronDown className="inline h-3 w-3" />)}
                              </TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {sortedOwnership.map((o: OwnershipEntry) => (
                              <TableRow key={o.shareholder_id} data-testid={`row-ownership-${o.shareholder_id}`}>
                                <TableCell className="font-medium">{o.name}</TableCell>
                                <TableCell><TypeBadge type={o.type} /></TableCell>
                                <TableCell className="text-muted-foreground">
                                  {o.common_shares > 0 && o.preferred_shares > 0 ? 'Mixed' :
                                    o.preferred_shares > 0 ? 'Preferred' : 'Common'}
                                </TableCell>
                                <TableCell className="text-right">{o.total_fully_diluted.toLocaleString()}</TableCell>
                                <TableCell className="text-right font-semibold">{o.ownership_percent.toFixed(2)}%</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </>
          )}
        </TabsContent>

        {/* ─── Stakeholders Tab ──────────────────────────────── */}
        <TabsContent value="stakeholders" className="space-y-4">
          <div className="flex flex-wrap justify-between items-center gap-2">
            <h2 className="text-lg font-semibold">Stakeholders</h2>
            <Button onClick={() => setShowShareholderDialog(true)} data-testid="button-add-shareholder">
              <Plus className="h-4 w-4 mr-2" />
              Add Stakeholder
            </Button>
          </div>

          {shareholdersLoading ? (
            <div className="space-y-3">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}</div>
          ) : shareholders.length === 0 ? (
            <EmptyStateCard
              icon={Users}
              title="No Stakeholders"
              description="Add founders, employees, investors, and advisors to build your cap table."
              action={{ label: "Add Stakeholder", onClick: () => setShowShareholderDialog(true), icon: Plus }}
            />
          ) : (
            <Card>
              <CardContent className="pt-4">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Email</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead className="text-right">Common</TableHead>
                        <TableHead className="text-right">Preferred</TableHead>
                        <TableHead className="text-right">Options</TableHead>
                        <TableHead className="text-right">Total %</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {shareholders.map((sh: ShareholderData) => {
                        const ownershipEntry = summary?.ownership?.find((o: OwnershipEntry) => o.shareholder_id === sh.id);
                        const isExpanded = expandedShareholder === sh.id;
                        return (
                          <>
                            <TableRow
                              key={sh.id}
                              data-testid={`row-stakeholder-${sh.id}`}
                              className="cursor-pointer"
                              onClick={() => setExpandedShareholder(isExpanded ? null : sh.id)}
                            >
                              <TableCell className="font-medium">{sh.name}</TableCell>
                              <TableCell className="text-muted-foreground">{sh.email || '--'}</TableCell>
                              <TableCell><TypeBadge type={sh.type} /></TableCell>
                              <TableCell className="text-right">{(ownershipEntry?.common_shares || 0).toLocaleString()}</TableCell>
                              <TableCell className="text-right">{(ownershipEntry?.preferred_shares || 0).toLocaleString()}</TableCell>
                              <TableCell className="text-right">{sh.total_options_granted.toLocaleString()}</TableCell>
                              <TableCell className="text-right font-semibold">
                                {ownershipEntry ? `${ownershipEntry.ownership_percent.toFixed(2)}%` : '0.00%'}
                              </TableCell>
                              <TableCell>
                                <Button
                                  size="icon"
                                  variant="ghost"
                                  onClick={(e) => { e.stopPropagation(); setExpandedShareholder(isExpanded ? null : sh.id); }}
                                  data-testid={`button-expand-${sh.id}`}
                                >
                                  {isExpanded ? <ChevronUp /> : <ChevronDown />}
                                </Button>
                              </TableCell>
                            </TableRow>
                            {isExpanded && (
                              <TableRow key={`${sh.id}-detail`}>
                                <TableCell colSpan={8} className="bg-muted/30">
                                  <div className="p-4 space-y-3">
                                    <p className="text-sm font-medium">Holdings Breakdown</p>
                                    <div className="grid gap-4 md:grid-cols-3">
                                      <div>
                                        <p className="text-xs text-muted-foreground">Common Shares</p>
                                        <p className="font-semibold">{(ownershipEntry?.common_shares || 0).toLocaleString()}</p>
                                      </div>
                                      <div>
                                        <p className="text-xs text-muted-foreground">Preferred Shares</p>
                                        <p className="font-semibold">{(ownershipEntry?.preferred_shares || 0).toLocaleString()}</p>
                                      </div>
                                      <div>
                                        <p className="text-xs text-muted-foreground">Vested Options</p>
                                        <p className="font-semibold">{(ownershipEntry?.options_vested || 0).toLocaleString()}</p>
                                      </div>
                                      <div>
                                        <p className="text-xs text-muted-foreground">Options Granted</p>
                                        <p className="font-semibold">{sh.total_options_granted.toLocaleString()}</p>
                                      </div>
                                      <div>
                                        <p className="text-xs text-muted-foreground">Options Exercised</p>
                                        <p className="font-semibold">{(ownershipEntry?.options_exercised || 0).toLocaleString()}</p>
                                      </div>
                                      <div>
                                        <p className="text-xs text-muted-foreground">Fully Diluted Total</p>
                                        <p className="font-semibold">{(ownershipEntry?.total_fully_diluted || 0).toLocaleString()}</p>
                                      </div>
                                    </div>
                                  </div>
                                </TableCell>
                              </TableRow>
                            )}
                          </>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ─── Securities Tab ────────────────────────────────── */}
        <TabsContent value="securities" className="space-y-6">
          <div className="flex flex-wrap justify-between items-center gap-2">
            <h2 className="text-lg font-semibold">Securities</h2>
            <div className="flex gap-2 flex-wrap">
              <Button variant="outline" onClick={() => setShowIssueDialog(true)} data-testid="button-issue-securities">
                <Plus className="h-4 w-4 mr-2" />
                Issue Securities
              </Button>
              <Button variant="outline" onClick={() => setShowGrantDialog(true)} data-testid="button-new-grant">
                <Award className="h-4 w-4 mr-2" />
                Grant Options
              </Button>
              <Button variant="outline" onClick={() => setShowConvertibleDialog(true)} data-testid="button-add-convertible">
                <Briefcase className="h-4 w-4 mr-2" />
                Add SAFE/Note
              </Button>
            </div>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Layers className="h-4 w-4 text-emerald-500" />
                  Equity Holdings
                </CardTitle>
                <CardDescription>Common and preferred stock issued to stakeholders</CardDescription>
              </CardHeader>
              <CardContent>
                {holdings.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-4 text-center">No equity holdings yet. Issue securities to get started.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Holder</TableHead>
                          <TableHead>Class</TableHead>
                          <TableHead>Series</TableHead>
                          <TableHead className="text-right">Shares</TableHead>
                          <TableHead className="text-right">Price/Share</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {holdings.map((h: any) => (
                          <TableRow key={h.id} data-testid={`row-holding-${h.id}`}>
                            <TableCell className="font-medium">{h.shareholder_name || h.shareholder_id?.slice(0, 8)}</TableCell>
                            <TableCell>
                              <Badge variant="outline" className={h.share_class === 'preferred' ? 'bg-violet-500/15 text-violet-600 dark:text-violet-400' : 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'}>
                                {h.share_class}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-muted-foreground">{h.series || '--'}</TableCell>
                            <TableCell className="text-right">{h.shares?.toLocaleString()}</TableCell>
                            <TableCell className="text-right">{h.price_per_share ? formatCurrency(h.price_per_share) : '--'}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Award className="h-4 w-4 text-blue-500" />
                  Option Grants
                </CardTitle>
                <CardDescription>Stock options with vesting schedules</CardDescription>
              </CardHeader>
              <CardContent>
                {grantsLoading ? (
                  <div className="space-y-3">{[...Array(2)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
                ) : grants.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-4 text-center">No option grants yet.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Recipient</TableHead>
                          <TableHead>Type</TableHead>
                          <TableHead>Grant Date</TableHead>
                          <TableHead className="text-right">Granted</TableHead>
                          <TableHead className="text-right">Vested</TableHead>
                          <TableHead className="text-right">Exercisable</TableHead>
                          <TableHead className="text-right">Strike Price</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {grants.map((g: GrantData) => (
                          <TableRow key={g.id} data-testid={`row-grant-${g.id}`}>
                            <TableCell className="font-medium">{g.shareholder_name}</TableCell>
                            <TableCell><Badge variant="outline">{g.grant_type.toUpperCase()}</Badge></TableCell>
                            <TableCell className="text-muted-foreground">{g.grant_date || '--'}</TableCell>
                            <TableCell className="text-right">{g.shares_granted.toLocaleString()}</TableCell>
                            <TableCell className="text-right">{g.shares_vested.toLocaleString()}</TableCell>
                            <TableCell className="text-right">{g.shares_exercisable.toLocaleString()}</TableCell>
                            <TableCell className="text-right">{formatCurrency(g.exercise_price)}</TableCell>
                            <TableCell><StatusBadge status={g.status} /></TableCell>
                            <TableCell>
                              <div className="flex gap-1">
                                {g.status === 'active' && g.shares_exercisable > 0 && (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => { setSelectedGrantId(g.id); setShowExerciseDialog(true); }}
                                    data-testid={`button-exercise-${g.id}`}
                                  >
                                    Exercise
                                  </Button>
                                )}
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Briefcase className="h-4 w-4 text-amber-500" />
                  Convertible Securities
                </CardTitle>
                <CardDescription>SAFEs, Convertible Notes, and Warrants</CardDescription>
              </CardHeader>
              <CardContent>
                {convertiblesLoading ? (
                  <div className="space-y-3">{[...Array(2)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
                ) : convertibles.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-4 text-center">No convertible securities. Add SAFEs, Notes, or Warrants.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Holder</TableHead>
                          <TableHead>Type</TableHead>
                          <TableHead className="text-right">Principal</TableHead>
                          <TableHead className="text-right">Val. Cap</TableHead>
                          <TableHead className="text-right">Discount</TableHead>
                          <TableHead className="text-right">Interest</TableHead>
                          <TableHead>Maturity</TableHead>
                          <TableHead>Status</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {convertibles.map((c: ConvertibleData) => (
                          <TableRow key={c.id} data-testid={`row-convertible-${c.id}`}>
                            <TableCell className="font-medium">{c.holder}</TableCell>
                            <TableCell>
                              <Badge variant="outline" className="bg-amber-500/15 text-amber-600 dark:text-amber-400">
                                {c.type.toUpperCase()}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right">{formatCurrency(c.principal)}</TableCell>
                            <TableCell className="text-right">{c.valuation_cap ? formatCurrency(c.valuation_cap) : '--'}</TableCell>
                            <TableCell className="text-right">{c.discount_rate ? `${c.discount_rate}%` : '--'}</TableCell>
                            <TableCell className="text-right">{c.interest_rate ? `${c.interest_rate}%` : '--'}</TableCell>
                            <TableCell className="text-muted-foreground">{c.maturity_date || '--'}</TableCell>
                            <TableCell><StatusBadge status={c.conversion_status} /></TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {grants.length > 0 && (
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardContent className="pt-4 pb-4">
                  <p className="text-sm text-muted-foreground">Total Granted</p>
                  <p className="text-xl font-bold">{formatNumber(grants.reduce((s: number, g: GrantData) => s + g.shares_granted, 0))}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-4 pb-4">
                  <p className="text-sm text-muted-foreground">Total Vested</p>
                  <p className="text-xl font-bold">{formatNumber(grants.reduce((s: number, g: GrantData) => s + g.shares_vested, 0))}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-4 pb-4">
                  <p className="text-sm text-muted-foreground">Total Exercised</p>
                  <p className="text-xl font-bold">{formatNumber(grants.reduce((s: number, g: GrantData) => s + g.shares_exercised, 0))}</p>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        {/* ─── Transactions Tab ──────────────────────────────── */}
        <TabsContent value="transactions" className="space-y-4">
          <div className="flex flex-wrap justify-between items-center gap-2">
            <h2 className="text-lg font-semibold">Transaction History</h2>
            <div className="flex gap-2 flex-wrap">
              <Select value={txTypeFilter} onValueChange={setTxTypeFilter}>
                <SelectTrigger className="w-[160px]" data-testid="select-tx-filter">
                  <SelectValue placeholder="Filter by type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="issuance">Issuance</SelectItem>
                  <SelectItem value="transfer">Transfer</SelectItem>
                  <SelectItem value="exercise">Exercise</SelectItem>
                  <SelectItem value="cancellation">Cancellation</SelectItem>
                  <SelectItem value="conversion">Conversion</SelectItem>
                  <SelectItem value="repurchase">Repurchase</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" onClick={() => setShowTransferDialog(true)} data-testid="button-record-transfer">
                <ArrowRightLeft className="h-4 w-4 mr-2" />
                Record Transfer
              </Button>
            </div>
          </div>

          {transactionsLoading ? (
            <div className="space-y-3">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}</div>
          ) : filteredTransactions.length === 0 ? (
            <EmptyStateCard
              icon={ArrowRightLeft}
              title="No Transactions"
              description="Transaction history will appear here as equity is issued, transferred, or exercised."
            />
          ) : (
            <Card>
              <CardContent className="pt-4">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>From</TableHead>
                        <TableHead>To</TableHead>
                        <TableHead className="text-right">Shares</TableHead>
                        <TableHead className="text-right">Price/Share</TableHead>
                        <TableHead className="text-right">Total Value</TableHead>
                        <TableHead>Notes</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredTransactions.map((tx: TransactionData) => (
                        <TableRow key={tx.id} data-testid={`row-tx-${tx.id}`}>
                          <TableCell className="text-muted-foreground whitespace-nowrap">
                            {tx.effective_date || tx.created_at?.split('T')[0] || '--'}
                          </TableCell>
                          <TableCell><TxTypeBadge type={tx.transaction_type} /></TableCell>
                          <TableCell>{tx.from_shareholder_name || '--'}</TableCell>
                          <TableCell>{tx.to_shareholder_name || '--'}</TableCell>
                          <TableCell className="text-right">{tx.shares.toLocaleString()}</TableCell>
                          <TableCell className="text-right">{tx.price_per_share ? formatCurrency(tx.price_per_share) : '--'}</TableCell>
                          <TableCell className="text-right">{tx.total_value ? formatCurrency(tx.total_value) : '--'}</TableCell>
                          <TableCell className="text-muted-foreground text-xs max-w-[200px] truncate">{tx.notes || '--'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ─── Scenarios Tab ─────────────────────────────────── */}
        <TabsContent value="scenarios" className="space-y-6">
          <div className="flex flex-wrap justify-between items-center gap-2">
            <h2 className="text-lg font-semibold">Scenario Modeling</h2>
            <div className="flex gap-2 flex-wrap">
              <Button variant="outline" onClick={() => setShowWaterfallDialog(true)} data-testid="button-exit-waterfall">
                <BarChart3 className="h-4 w-4 mr-2" />
                Exit Waterfall
              </Button>
              <Button onClick={() => setShowScenarioDialog(true)} data-testid="button-new-scenario">
                <Plus className="h-4 w-4 mr-2" />
                New Scenario
              </Button>
            </div>
          </div>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Calculator className="h-4 w-4 text-emerald-500" />
                Dilution Calculator
              </CardTitle>
              <CardDescription>Quick inline dilution model</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!summary || summary.fully_diluted_shares === 0 ? (
                <div className="text-center py-6">
                  <AlertTriangle className="h-8 w-8 mx-auto text-amber-500 mb-3" />
                  <p className="text-muted-foreground">Issue equity first to model dilution scenarios</p>
                </div>
              ) : (
                <>
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="space-y-2">
                      <Label>Pre-Money Valuation ($)</Label>
                      <Input
                        type="number"
                        placeholder="10000000"
                        value={scenarioFormData.pre_money}
                        onChange={(e) => setScenarioFormData({ ...scenarioFormData, pre_money: e.target.value })}
                        data-testid="input-dilution-pre-money"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Raise Amount ($)</Label>
                      <Input
                        type="number"
                        placeholder="3000000"
                        value={scenarioFormData.raise_amount}
                        onChange={(e) => setScenarioFormData({ ...scenarioFormData, raise_amount: e.target.value })}
                        data-testid="input-dilution-raise"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Option Pool Refresh (%)</Label>
                      <Input
                        type="number"
                        placeholder="10"
                        value={scenarioFormData.option_pool_refresh}
                        onChange={(e) => setScenarioFormData({ ...scenarioFormData, option_pool_refresh: e.target.value })}
                        data-testid="input-dilution-pool"
                      />
                    </div>
                  </div>
                  <Button
                    onClick={() => createScenarioMutation.mutate({
                      name: `Quick Model - ${new Date().toLocaleDateString()}`,
                      scenario_type: 'new_round',
                      inputs_json: {
                        pre_money: parseFloat(scenarioFormData.pre_money) || 0,
                        raise_amount: parseFloat(scenarioFormData.raise_amount) || 0,
                        option_pool_refresh_percent: parseFloat(scenarioFormData.option_pool_refresh) || 0,
                      }
                    })}
                    disabled={createScenarioMutation.isPending || !scenarioFormData.pre_money || !scenarioFormData.raise_amount}
                    data-testid="button-run-dilution"
                  >
                    <TrendingUp className="h-4 w-4 mr-2" />
                    {createScenarioMutation.isPending ? 'Modeling...' : 'Run Dilution Model'}
                  </Button>
                </>
              )}
            </CardContent>
          </Card>

          {lastScenarioResult && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-emerald-500" />
                  Scenario Results
                </CardTitle>
                <CardDescription>Latest dilution model output</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 grid-cols-2 md:grid-cols-4">
                  {lastScenarioResult.post_money != null && (
                    <div>
                      <p className="text-xs text-muted-foreground">Post-Money Valuation</p>
                      <p className="font-semibold">{formatCurrency(lastScenarioResult.post_money)}</p>
                    </div>
                  )}
                  {lastScenarioResult.price_per_share != null && (
                    <div>
                      <p className="text-xs text-muted-foreground">Price Per Share</p>
                      <p className="font-semibold">{formatCurrency(lastScenarioResult.price_per_share)}</p>
                    </div>
                  )}
                  {lastScenarioResult.new_investor_shares != null && (
                    <div>
                      <p className="text-xs text-muted-foreground">New Shares Issued</p>
                      <p className="font-semibold">{Math.round(lastScenarioResult.new_investor_shares).toLocaleString()}</p>
                    </div>
                  )}
                  {lastScenarioResult.new_investor_percent != null && (
                    <div>
                      <p className="text-xs text-muted-foreground">Investor Ownership</p>
                      <p className="font-semibold">{lastScenarioResult.new_investor_percent.toFixed(2)}%</p>
                    </div>
                  )}
                  {lastScenarioResult.current_fully_diluted != null && (
                    <div>
                      <p className="text-xs text-muted-foreground">Current FD Shares</p>
                      <p className="font-semibold">{lastScenarioResult.current_fully_diluted.toLocaleString()}</p>
                    </div>
                  )}
                  {lastScenarioResult.new_fully_diluted != null && (
                    <div>
                      <p className="text-xs text-muted-foreground">Post-Round FD Shares</p>
                      <p className="font-semibold">{lastScenarioResult.new_fully_diluted.toLocaleString()}</p>
                    </div>
                  )}
                  {lastScenarioResult.option_pool_new_shares != null && lastScenarioResult.option_pool_new_shares > 0 && (
                    <div>
                      <p className="text-xs text-muted-foreground">New Option Pool Shares</p>
                      <p className="font-semibold">{lastScenarioResult.option_pool_new_shares.toLocaleString()}</p>
                    </div>
                  )}
                </div>
                <Button variant="ghost" size="sm" className="mt-3" onClick={() => setLastScenarioResult(null)}>
                  Dismiss
                </Button>
              </CardContent>
            </Card>
          )}

          {waterfallResult && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Exit Waterfall Results</CardTitle>
                <CardDescription>Payout distribution at {formatCurrency(parseFloat(waterfallExitValue))} exit</CardDescription>
              </CardHeader>
              <CardContent>
                {waterfallResult.payouts && waterfallResult.payouts.length > 0 ? (
                  <div className="space-y-4">
                    <div className="h-[250px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={waterfallResult.payouts}>
                          <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                          <XAxis dataKey="name" className="text-xs" />
                          <YAxis tickFormatter={(v: number) => `$${(v / 1e6).toFixed(1)}M`} className="text-xs" />
                          <Tooltip formatter={(v: number) => formatCurrency(v)} contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px' }} />
                          <Bar dataKey="payout" fill="#10b981" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Class / Holder</TableHead>
                            <TableHead className="text-right">Payout</TableHead>
                            <TableHead className="text-right">% of Exit</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {waterfallResult.payouts.map((p: any, i: number) => (
                            <TableRow key={i}>
                              <TableCell className="font-medium">{p.name || p.class_name || `Class ${i + 1}`}</TableCell>
                              <TableCell className="text-right">{formatCurrency(p.payout || p.amount || 0)}</TableCell>
                              <TableCell className="text-right">{((p.payout || p.amount || 0) / parseFloat(waterfallExitValue) * 100).toFixed(2)}%</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground py-4 text-center">No waterfall data available.</p>
                )}
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Saved Scenarios</CardTitle>
              <CardDescription>Previously modeled scenarios</CardDescription>
            </CardHeader>
            <CardContent>
              {scenariosLoading ? (
                <div className="space-y-3">{[...Array(2)].map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}</div>
              ) : scenarios.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">No saved scenarios. Create a scenario to model ownership changes.</p>
              ) : (
                <div className="space-y-3">
                  {scenarios.map((sc: ScenarioData) => (
                    <div
                      key={sc.id}
                      className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-md border"
                      data-testid={`card-scenario-${sc.id}`}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="font-medium">{sc.name}</p>
                          <ScenarioTypeBadge type={sc.scenario_type} />
                        </div>
                        {sc.description && <p className="text-sm text-muted-foreground mt-1">{sc.description}</p>}
                        <p className="text-xs text-muted-foreground mt-1">Created {new Date(sc.created_at).toLocaleDateString()}</p>
                      </div>
                      <div className="flex gap-2">
                        {sc.results_json && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setLastScenarioResult(sc.results_json)}
                            data-testid={`button-view-scenario-${sc.id}`}
                          >
                            View Results
                          </Button>
                        )}
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => deleteScenarioMutation.mutate(sc.id)}
                          data-testid={`button-delete-scenario-${sc.id}`}
                        >
                          <Trash2 />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ─── Reports Tab ───────────────────────────────────── */}
        <TabsContent value="reports" className="space-y-6">
          <div className="flex flex-wrap justify-between items-center gap-2">
            <h2 className="text-lg font-semibold">Reports & Compliance</h2>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Shield className="h-4 w-4 text-amber-500" />
                  409A Summary
                </CardTitle>
              </CardHeader>
              <CardContent>
                {summary409aData ? (
                  <div className="space-y-3">
                    <div className="grid gap-3 grid-cols-2">
                      <div>
                        <p className="text-xs text-muted-foreground">FMV per Share</p>
                        <p className="font-semibold">{summary409aData.price_per_share ? formatCurrency(summary409aData.price_per_share) : '--'}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Total FMV</p>
                        <p className="font-semibold">{summary409aData.fair_market_value ? formatCurrency(summary409aData.fair_market_value) : '--'}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Methodology</p>
                        <p className="font-semibold capitalize">{summary409aData.methodology || '--'}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Valuation Date</p>
                        <p className="font-semibold">{summary409aData.valuation_date || '--'}</p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <p className="text-sm text-muted-foreground">No 409A valuation on file</p>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Download className="h-4 w-4 text-blue-500" />
                  Export Cap Table
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <Button variant="outline" className="w-full justify-start" onClick={handleExportCSV} data-testid="button-export-csv">
                    <FileText className="h-4 w-4 mr-2" />
                    Export as CSV
                  </Button>
                  <Button variant="outline" className="w-full justify-start" onClick={() => window.print()} data-testid="button-export-pdf">
                    <FileText className="h-4 w-4 mr-2" />
                    Export as PDF (Print)
                  </Button>
                  <Button variant="outline" className="w-full justify-start" onClick={handleExportJSON} data-testid="button-export-json">
                    <FileText className="h-4 w-4 mr-2" />
                    Export as JSON (OCF)
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <ScrollText className="h-4 w-4 text-violet-500" />
                Audit Log
              </CardTitle>
              <CardDescription>Full history of all cap table changes</CardDescription>
            </CardHeader>
            <CardContent>
              {auditLogLoading ? (
                <div className="space-y-3">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
              ) : auditLog.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">No audit log entries yet. Changes will be tracked automatically.</p>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Timestamp</TableHead>
                        <TableHead>Action</TableHead>
                        <TableHead>Entity Type</TableHead>
                        <TableHead>Entity ID</TableHead>
                        <TableHead>User</TableHead>
                        <TableHead>Changes</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {auditLog.map((entry: AuditLogData) => (
                        <TableRow key={entry.id} data-testid={`row-audit-${entry.id}`}>
                          <TableCell className="text-muted-foreground whitespace-nowrap">
                            {new Date(entry.timestamp).toLocaleString()}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">{entry.action}</Badge>
                          </TableCell>
                          <TableCell className="capitalize">{entry.entity_type}</TableCell>
                          <TableCell className="text-muted-foreground font-mono text-xs">{entry.entity_id?.slice(0, 8)}...</TableCell>
                          <TableCell className="text-muted-foreground">{entry.user_id || 'System'}</TableCell>
                          <TableCell className="text-xs max-w-[200px] truncate text-muted-foreground">
                            {entry.changes_json ? JSON.stringify(entry.changes_json).slice(0, 60) : '--'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>

          {valuations.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">409A Valuation History</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {valuations.map((v: any) => (
                    <div key={v.id} className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-md border" data-testid={`card-valuation-${v.id}`}>
                      <div>
                        <p className="font-semibold">FMV: {formatCurrency(v.price_per_share)}/share</p>
                        <p className="text-sm text-muted-foreground">
                          Total: {formatCurrency(v.fair_market_value)} | {v.methodology || 'N/A'} method
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          Date: {v.valuation_date} {v.expiration_date ? `| Expires: ${v.expiration_date}` : ''}
                        </p>
                      </div>
                      <StatusBadge status={v.status || 'active'} />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* ─── Dialogs ─────────────────────────────────────────── */}

      <Dialog open={showShareholderDialog} onOpenChange={setShowShareholderDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Stakeholder</DialogTitle>
            <DialogDescription>Add a founder, employee, investor, or advisor.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Name</Label>
              <Input
                value={newShareholder.name}
                onChange={(e) => setNewShareholder({ ...newShareholder, name: e.target.value })}
                placeholder="Jane Smith"
                data-testid="input-shareholder-name"
              />
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input
                value={newShareholder.email}
                onChange={(e) => setNewShareholder({ ...newShareholder, email: e.target.value })}
                placeholder="jane@company.com"
                data-testid="input-shareholder-email"
              />
            </div>
            <div className="space-y-2">
              <Label>Type</Label>
              <Select value={newShareholder.type} onValueChange={(v) => setNewShareholder({ ...newShareholder, type: v })}>
                <SelectTrigger data-testid="select-shareholder-type"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {SHAREHOLDER_TYPES.map(t => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-4 grid-cols-2">
              <div className="space-y-2">
                <Label>Tax ID (optional)</Label>
                <Input
                  value={newShareholder.tax_id}
                  onChange={(e) => setNewShareholder({ ...newShareholder, tax_id: e.target.value })}
                  placeholder="XX-XXXXXXX"
                  data-testid="input-shareholder-tax-id"
                />
              </div>
              <div className="space-y-2">
                <Label>Address (optional)</Label>
                <Input
                  value={newShareholder.address}
                  onChange={(e) => setNewShareholder({ ...newShareholder, address: e.target.value })}
                  placeholder="123 Main St"
                  data-testid="input-shareholder-address"
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowShareholderDialog(false)}>Cancel</Button>
            <Button
              onClick={() => createShareholderMutation.mutate(newShareholder)}
              disabled={createShareholderMutation.isPending || !newShareholder.name}
              data-testid="button-save-shareholder"
            >
              Add
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showIssueDialog} onOpenChange={setShowIssueDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Issue Securities</DialogTitle>
            <DialogDescription>Issue shares to a stakeholder. This creates a new equity holding and records the transaction.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Shareholder</Label>
              <Select value={issueData.shareholder_id} onValueChange={(v) => setIssueData({ ...issueData, shareholder_id: v })}>
                <SelectTrigger data-testid="select-issue-shareholder"><SelectValue placeholder="Select shareholder" /></SelectTrigger>
                <SelectContent>
                  {shareholders.map(sh => (
                    <SelectItem key={sh.id} value={sh.id}>{sh.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-4 grid-cols-2">
              <div className="space-y-2">
                <Label>Share Class</Label>
                <Select value={issueData.share_class} onValueChange={(v) => setIssueData({ ...issueData, share_class: v })}>
                  <SelectTrigger data-testid="select-share-class"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="common">Common</SelectItem>
                    <SelectItem value="preferred">Preferred</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {issueData.share_class === 'preferred' && (
                <div className="space-y-2">
                  <Label>Series</Label>
                  <Input
                    value={issueData.series}
                    onChange={(e) => setIssueData({ ...issueData, series: e.target.value })}
                    placeholder="Series A"
                    data-testid="input-series"
                  />
                </div>
              )}
            </div>
            <div className="grid gap-4 grid-cols-2">
              <div className="space-y-2">
                <Label>Number of Shares</Label>
                <Input
                  type="number"
                  value={issueData.shares}
                  onChange={(e) => setIssueData({ ...issueData, shares: e.target.value })}
                  placeholder="1000000"
                  data-testid="input-issue-shares"
                />
              </div>
              <div className="space-y-2">
                <Label>Price per Share ($)</Label>
                <Input
                  type="number"
                  value={issueData.price_per_share}
                  onChange={(e) => setIssueData({ ...issueData, price_per_share: e.target.value })}
                  placeholder="0.001"
                  data-testid="input-issue-price"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Notes</Label>
              <Input
                value={issueData.notes}
                onChange={(e) => setIssueData({ ...issueData, notes: e.target.value })}
                placeholder="Founder shares at incorporation"
                data-testid="input-issue-notes"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowIssueDialog(false)}>Cancel</Button>
            <Button
              onClick={() => issueEquityMutation.mutate({
                shareholder_id: issueData.shareholder_id,
                share_class: issueData.share_class,
                series: issueData.series || null,
                shares: parseFloat(issueData.shares) || 0,
                price_per_share: issueData.price_per_share ? parseFloat(issueData.price_per_share) : null,
                notes: issueData.notes || null,
              })}
              disabled={issueEquityMutation.isPending || !issueData.shareholder_id || !issueData.shares}
              data-testid="button-save-issue"
            >
              Issue Shares
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showGrantDialog} onOpenChange={setShowGrantDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Create Option Grant</DialogTitle>
            <DialogDescription>Grant stock options with a vesting schedule.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Recipient</Label>
              <Select value={grantData.shareholder_id} onValueChange={(v) => setGrantData({ ...grantData, shareholder_id: v })}>
                <SelectTrigger data-testid="select-grant-recipient"><SelectValue placeholder="Select recipient" /></SelectTrigger>
                <SelectContent>
                  {shareholders.map(sh => (
                    <SelectItem key={sh.id} value={sh.id}>{sh.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-4 grid-cols-2">
              <div className="space-y-2">
                <Label>Grant Type</Label>
                <Select value={grantData.grant_type} onValueChange={(v) => setGrantData({ ...grantData, grant_type: v })}>
                  <SelectTrigger data-testid="select-grant-type"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {GRANT_TYPES.map(t => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Vesting Schedule</Label>
                <Select value={grantData.vesting_type} onValueChange={(v) => setGrantData({ ...grantData, vesting_type: v })}>
                  <SelectTrigger data-testid="select-vesting-type"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {VESTING_TYPES.map(t => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid gap-4 grid-cols-2">
              <div className="space-y-2">
                <Label>Shares to Grant</Label>
                <Input
                  type="number"
                  value={grantData.shares_granted}
                  onChange={(e) => setGrantData({ ...grantData, shares_granted: e.target.value })}
                  placeholder="50000"
                  data-testid="input-grant-shares"
                />
              </div>
              <div className="space-y-2">
                <Label>Exercise Price ($)</Label>
                <Input
                  type="number"
                  value={grantData.exercise_price}
                  onChange={(e) => setGrantData({ ...grantData, exercise_price: e.target.value })}
                  placeholder="0.10"
                  data-testid="input-grant-price"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Grant Date</Label>
              <Input
                type="date"
                value={grantData.grant_date}
                onChange={(e) => setGrantData({ ...grantData, grant_date: e.target.value })}
                data-testid="input-grant-date"
              />
            </div>
            {grantData.vesting_type === 'custom' && (
              <div className="grid gap-4 grid-cols-2">
                <div className="space-y-2">
                  <Label>Cliff (months)</Label>
                  <Input
                    type="number"
                    value={grantData.cliff_months}
                    onChange={(e) => setGrantData({ ...grantData, cliff_months: e.target.value })}
                    data-testid="input-cliff-months"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Total Vesting (months)</Label>
                  <Input
                    type="number"
                    value={grantData.vesting_months}
                    onChange={(e) => setGrantData({ ...grantData, vesting_months: e.target.value })}
                    data-testid="input-vesting-months"
                  />
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowGrantDialog(false)}>Cancel</Button>
            <Button
              onClick={() => createGrantMutation.mutate({
                shareholder_id: grantData.shareholder_id,
                grant_type: grantData.grant_type,
                shares_granted: parseFloat(grantData.shares_granted) || 0,
                exercise_price: parseFloat(grantData.exercise_price) || 0,
                vesting_type: grantData.vesting_type,
                cliff_months: grantData.vesting_type === 'monthly_no_cliff' ? 0 : parseInt(grantData.cliff_months) || 12,
                vesting_months: parseInt(grantData.vesting_months) || 48,
                grant_date: grantData.grant_date || null,
              })}
              disabled={createGrantMutation.isPending || !grantData.shareholder_id || !grantData.shares_granted}
              data-testid="button-save-grant"
            >
              Create Grant
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showExerciseDialog} onOpenChange={setShowExerciseDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Exercise Options</DialogTitle>
            <DialogDescription>Convert vested options into shares.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Shares to Exercise</Label>
              <Input
                type="number"
                value={exerciseData.shares_to_exercise}
                onChange={(e) => setExerciseData({ ...exerciseData, shares_to_exercise: e.target.value })}
                placeholder="Enter number of shares"
                data-testid="input-exercise-shares"
              />
            </div>
            <div className="space-y-2">
              <Label>Notes</Label>
              <Input
                value={exerciseData.notes}
                onChange={(e) => setExerciseData({ ...exerciseData, notes: e.target.value })}
                placeholder="Optional notes"
                data-testid="input-exercise-notes"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setShowExerciseDialog(false); setSelectedGrantId(null); }}>Cancel</Button>
            <Button
              onClick={() => exerciseMutation.mutate({
                shares_to_exercise: parseFloat(exerciseData.shares_to_exercise) || 0,
                notes: exerciseData.notes || null,
              })}
              disabled={exerciseMutation.isPending || !exerciseData.shares_to_exercise}
              data-testid="button-confirm-exercise"
            >
              Exercise
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showTransferDialog} onOpenChange={setShowTransferDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Record Transfer</DialogTitle>
            <DialogDescription>Transfer shares between stakeholders.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>From Shareholder</Label>
              <Select value={transferData.from_shareholder_id} onValueChange={(v) => setTransferData({ ...transferData, from_shareholder_id: v, holding_id: '' })}>
                <SelectTrigger data-testid="select-transfer-from"><SelectValue placeholder="Select sender" /></SelectTrigger>
                <SelectContent>
                  {shareholders.filter(sh => sh.total_shares > 0).map(sh => (
                    <SelectItem key={sh.id} value={sh.id}>{sh.name} ({sh.total_shares.toLocaleString()} shares)</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {transferData.from_shareholder_id && (
              <div className="space-y-2">
                <Label>Holding</Label>
                <Select value={transferData.holding_id} onValueChange={(v) => setTransferData({ ...transferData, holding_id: v })}>
                  <SelectTrigger data-testid="select-transfer-holding"><SelectValue placeholder="Select holding" /></SelectTrigger>
                  <SelectContent>
                    {holdings.filter((h: any) => h.shareholder_id === transferData.from_shareholder_id).map((h: any) => (
                      <SelectItem key={h.id} value={h.id}>
                        {h.share_class} {h.series ? `(${h.series})` : ''} — {h.shares.toLocaleString()} shares
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <div className="space-y-2">
              <Label>To Shareholder</Label>
              <Select value={transferData.to_shareholder_id} onValueChange={(v) => setTransferData({ ...transferData, to_shareholder_id: v })}>
                <SelectTrigger data-testid="select-transfer-to"><SelectValue placeholder="Select recipient" /></SelectTrigger>
                <SelectContent>
                  {shareholders.filter(sh => sh.id !== transferData.from_shareholder_id).map(sh => (
                    <SelectItem key={sh.id} value={sh.id}>{sh.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-4 grid-cols-2">
              <div className="space-y-2">
                <Label>Shares to Transfer</Label>
                <Input
                  type="number"
                  value={transferData.shares}
                  onChange={(e) => setTransferData({ ...transferData, shares: e.target.value })}
                  placeholder="Number of shares"
                  data-testid="input-transfer-shares"
                />
              </div>
              <div className="space-y-2">
                <Label>Price per Share ($)</Label>
                <Input
                  type="number"
                  value={transferData.price_per_share}
                  onChange={(e) => setTransferData({ ...transferData, price_per_share: e.target.value })}
                  placeholder="Optional"
                  data-testid="input-transfer-price"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Notes</Label>
              <Input
                value={transferData.notes}
                onChange={(e) => setTransferData({ ...transferData, notes: e.target.value })}
                placeholder="Transfer notes"
                data-testid="input-transfer-notes"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowTransferDialog(false)}>Cancel</Button>
            <Button
              onClick={() => transferMutation.mutate({
                from_shareholder_id: transferData.from_shareholder_id,
                to_shareholder_id: transferData.to_shareholder_id,
                holding_id: transferData.holding_id,
                shares: parseFloat(transferData.shares) || 0,
                price_per_share: transferData.price_per_share ? parseFloat(transferData.price_per_share) : null,
                notes: transferData.notes || null,
              })}
              disabled={transferMutation.isPending || !transferData.from_shareholder_id || !transferData.to_shareholder_id || !transferData.holding_id || !transferData.shares}
              data-testid="button-confirm-transfer"
            >
              Transfer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showConvertibleDialog} onOpenChange={setShowConvertibleDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Add Convertible Security</DialogTitle>
            <DialogDescription>Record a SAFE, Convertible Note, or Warrant.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid gap-4 grid-cols-2">
              <div className="space-y-2">
                <Label>Type</Label>
                <Select value={convertibleData.type} onValueChange={(v) => setConvertibleData({ ...convertibleData, type: v })}>
                  <SelectTrigger data-testid="select-convertible-type"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="safe">SAFE</SelectItem>
                    <SelectItem value="convertible_note">Convertible Note</SelectItem>
                    <SelectItem value="warrant">Warrant</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Holder Name</Label>
                <Input
                  value={convertibleData.holder}
                  onChange={(e) => setConvertibleData({ ...convertibleData, holder: e.target.value })}
                  placeholder="Investor name"
                  data-testid="input-convertible-holder"
                />
              </div>
            </div>
            <div className="grid gap-4 grid-cols-2">
              <div className="space-y-2">
                <Label>Principal ($)</Label>
                <Input
                  type="number"
                  value={convertibleData.principal}
                  onChange={(e) => setConvertibleData({ ...convertibleData, principal: e.target.value })}
                  placeholder="500000"
                  data-testid="input-convertible-principal"
                />
              </div>
              <div className="space-y-2">
                <Label>Valuation Cap ($)</Label>
                <Input
                  type="number"
                  value={convertibleData.valuation_cap}
                  onChange={(e) => setConvertibleData({ ...convertibleData, valuation_cap: e.target.value })}
                  placeholder="10000000"
                  data-testid="input-convertible-cap"
                />
              </div>
            </div>
            <div className="grid gap-4 grid-cols-2">
              <div className="space-y-2">
                <Label>Discount Rate (%)</Label>
                <Input
                  type="number"
                  value={convertibleData.discount_rate}
                  onChange={(e) => setConvertibleData({ ...convertibleData, discount_rate: e.target.value })}
                  placeholder="20"
                  data-testid="input-convertible-discount"
                />
              </div>
              {(convertibleData.type === 'convertible_note') && (
                <div className="space-y-2">
                  <Label>Interest Rate (%)</Label>
                  <Input
                    type="number"
                    value={convertibleData.interest_rate}
                    onChange={(e) => setConvertibleData({ ...convertibleData, interest_rate: e.target.value })}
                    placeholder="5"
                    data-testid="input-convertible-interest"
                  />
                </div>
              )}
            </div>
            {(convertibleData.type === 'convertible_note' || convertibleData.type === 'warrant') && (
              <div className="space-y-2">
                <Label>Maturity Date</Label>
                <Input
                  type="date"
                  value={convertibleData.maturity_date}
                  onChange={(e) => setConvertibleData({ ...convertibleData, maturity_date: e.target.value })}
                  data-testid="input-convertible-maturity"
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowConvertibleDialog(false)}>Cancel</Button>
            <Button
              onClick={() => createConvertibleMutation.mutate({
                type: convertibleData.type,
                holder: convertibleData.holder,
                principal: parseFloat(convertibleData.principal) || 0,
                valuation_cap: convertibleData.valuation_cap ? parseFloat(convertibleData.valuation_cap) : null,
                discount_rate: convertibleData.discount_rate ? parseFloat(convertibleData.discount_rate) : null,
                interest_rate: convertibleData.interest_rate ? parseFloat(convertibleData.interest_rate) : null,
                maturity_date: convertibleData.maturity_date || null,
              })}
              disabled={createConvertibleMutation.isPending || !convertibleData.holder || !convertibleData.principal}
              data-testid="button-save-convertible"
            >
              Add Security
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showScenarioDialog} onOpenChange={setShowScenarioDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>New Scenario</DialogTitle>
            <DialogDescription>Model how changes would affect ownership.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Scenario Name</Label>
              <Input
                value={scenarioFormData.name}
                onChange={(e) => setScenarioFormData({ ...scenarioFormData, name: e.target.value })}
                placeholder="Series A Round"
                data-testid="input-scenario-name"
              />
            </div>
            <div className="space-y-2">
              <Label>Type</Label>
              <Select value={scenarioFormData.scenario_type} onValueChange={(v) => setScenarioFormData({ ...scenarioFormData, scenario_type: v })}>
                <SelectTrigger data-testid="select-scenario-type"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {SCENARIO_TYPES.map(t => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input
                value={scenarioFormData.description}
                onChange={(e) => setScenarioFormData({ ...scenarioFormData, description: e.target.value })}
                placeholder="Model the impact of..."
                data-testid="input-scenario-description"
              />
            </div>
            {scenarioFormData.scenario_type === 'new_round' && (
              <>
                <div className="grid gap-4 grid-cols-2">
                  <div className="space-y-2">
                    <Label>Pre-Money ($)</Label>
                    <Input
                      type="number"
                      value={scenarioFormData.pre_money}
                      onChange={(e) => setScenarioFormData({ ...scenarioFormData, pre_money: e.target.value })}
                      placeholder="10000000"
                      data-testid="input-scenario-pre-money"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Raise Amount ($)</Label>
                    <Input
                      type="number"
                      value={scenarioFormData.raise_amount}
                      onChange={(e) => setScenarioFormData({ ...scenarioFormData, raise_amount: e.target.value })}
                      placeholder="3000000"
                      data-testid="input-scenario-raise"
                    />
                  </div>
                </div>
                <div className="grid gap-4 grid-cols-2">
                  <div className="space-y-2">
                    <Label>Option Pool Refresh (%)</Label>
                    <Input
                      type="number"
                      value={scenarioFormData.option_pool_refresh}
                      onChange={(e) => setScenarioFormData({ ...scenarioFormData, option_pool_refresh: e.target.value })}
                      placeholder="10"
                      data-testid="input-scenario-pool"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Investor Name</Label>
                    <Input
                      value={scenarioFormData.investor_name}
                      onChange={(e) => setScenarioFormData({ ...scenarioFormData, investor_name: e.target.value })}
                      placeholder="Acme Ventures"
                      data-testid="input-scenario-investor"
                    />
                  </div>
                </div>
              </>
            )}
            {scenarioFormData.scenario_type === 'exit_waterfall' && (
              <div className="space-y-2">
                <Label>Exit Value ($)</Label>
                <Input
                  type="number"
                  value={scenarioFormData.exit_value}
                  onChange={(e) => setScenarioFormData({ ...scenarioFormData, exit_value: e.target.value })}
                  placeholder="100000000"
                  data-testid="input-scenario-exit-value"
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowScenarioDialog(false)}>Cancel</Button>
            <Button
              onClick={() => {
                const inputs: any = {};
                if (scenarioFormData.scenario_type === 'new_round') {
                  inputs.pre_money = parseFloat(scenarioFormData.pre_money) || 0;
                  inputs.raise_amount = parseFloat(scenarioFormData.raise_amount) || 0;
                  inputs.option_pool_refresh_percent = parseFloat(scenarioFormData.option_pool_refresh) || 0;
                  inputs.investor_name = scenarioFormData.investor_name || null;
                } else if (scenarioFormData.scenario_type === 'exit_waterfall') {
                  inputs.exit_value = parseFloat(scenarioFormData.exit_value) || 0;
                }
                createScenarioMutation.mutate({
                  name: scenarioFormData.name,
                  description: scenarioFormData.description || null,
                  scenario_type: scenarioFormData.scenario_type,
                  inputs_json: inputs,
                });
              }}
              disabled={createScenarioMutation.isPending || !scenarioFormData.name}
              data-testid="button-save-scenario"
            >
              Create Scenario
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showWaterfallDialog} onOpenChange={setShowWaterfallDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Exit Waterfall Analysis</DialogTitle>
            <DialogDescription>Model how exit proceeds would be distributed based on liquidation preferences.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Exit Value ($)</Label>
              <Input
                type="number"
                value={waterfallExitValue}
                onChange={(e) => setWaterfallExitValue(e.target.value)}
                placeholder="100000000"
                data-testid="input-waterfall-exit"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowWaterfallDialog(false)}>Cancel</Button>
            <Button
              onClick={() => {
                waterfallMutation.mutate({ exit_value: parseFloat(waterfallExitValue) || 0 });
                setShowWaterfallDialog(false);
              }}
              disabled={waterfallMutation.isPending || !waterfallExitValue}
              data-testid="button-run-waterfall"
            >
              <BarChart3 className="h-4 w-4 mr-2" />
              Run Waterfall
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
