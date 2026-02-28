import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/hooks/use-toast';
import { useFounderStore } from '@/store/founderStore';
import { getErrorMessage } from '@/lib/errors';
import { apiRequest } from '@/lib/queryClient';
import {
  Plus, PieChart, Users, TrendingUp, FileText, Building2,
  ArrowRightLeft, Award, Clock, AlertTriangle, DollarSign,
  Calculator, ChevronDown, ChevronUp, MoreHorizontal, Shield,
  X, Check
} from 'lucide-react';
import { EmptyStateCard } from '@/components/ui/empty-state';
import {
  PieChart as RechartsPie, Pie, Cell, ResponsiveContainer, Tooltip, Legend
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

const OWNERSHIP_COLORS = [
  '#6366f1', '#8b5cf6', '#a855f7', '#d946ef',
  '#ec4899', '#f43f5e', '#f97316', '#eab308',
  '#22c55e', '#14b8a6', '#06b6d4', '#3b82f6',
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
    founder: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    employee: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    investor: 'bg-green-500/20 text-green-400 border-green-500/30',
    advisor: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    board_member: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    contractor: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  };
  return (
    <Badge variant="outline" className={colors[type] || colors.contractor}>
      {type.replace('_', ' ')}
    </Badge>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: 'bg-green-500/20 text-green-400',
    exercised: 'bg-blue-500/20 text-blue-400',
    cancelled: 'bg-red-500/20 text-red-400',
    expired: 'bg-gray-500/20 text-gray-400',
    draft: 'bg-yellow-500/20 text-yellow-400',
  };
  return <Badge className={colors[status] || colors.draft}>{status}</Badge>;
}

function TxTypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    issuance: 'bg-green-500/20 text-green-400',
    transfer: 'bg-blue-500/20 text-blue-400',
    exercise: 'bg-purple-500/20 text-purple-400',
    cancellation: 'bg-red-500/20 text-red-400',
    conversion: 'bg-amber-500/20 text-amber-400',
    repurchase: 'bg-gray-500/20 text-gray-400',
  };
  return <Badge className={colors[type] || 'bg-gray-500/20 text-gray-400'}>{type}</Badge>;
}

export default function CapTablePage() {
  const { currentCompany } = useFounderStore();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const companyId = currentCompany?.id;

  const [activeTab, setActiveTab] = useState('overview');
  const [showShareholderDialog, setShowShareholderDialog] = useState(false);
  const [showIssueDialog, setShowIssueDialog] = useState(false);
  const [showGrantDialog, setShowGrantDialog] = useState(false);
  const [showTransferDialog, setShowTransferDialog] = useState(false);
  const [showExerciseDialog, setShowExerciseDialog] = useState(false);
  const [showValuationDialog, setShowValuationDialog] = useState(false);
  const [showDilutionDialog, setShowDilutionDialog] = useState(false);
  const [selectedGrantId, setSelectedGrantId] = useState<string | null>(null);

  const [newShareholder, setNewShareholder] = useState({ name: '', email: '', type: 'founder' });
  const [issueData, setIssueData] = useState({
    shareholder_id: '', share_class: 'common', series: '', shares: '', price_per_share: '', notes: ''
  });
  const [grantData, setGrantData] = useState({
    shareholder_id: '', grant_type: 'iso', shares_granted: '', exercise_price: '',
    vesting_type: '4y_1y_cliff', cliff_months: '12', vesting_months: '48', notes: ''
  });
  const [transferData, setTransferData] = useState({
    from_shareholder_id: '', to_shareholder_id: '', holding_id: '', shares: '', notes: ''
  });
  const [exerciseData, setExerciseData] = useState({ shares_to_exercise: '', notes: '' });
  const [valuationData, setValuationData] = useState({
    valuation_date: '', fair_market_value: '', price_per_share: '',
    methodology: 'income', provider: '', notes: ''
  });
  const [dilutionData, setDilutionData] = useState({
    pre_money: '', raise_amount: '', option_pool_refresh_percent: ''
  });
  const [dilutionResult, setDilutionResult] = useState<any>(null);

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

  const shareholders: ShareholderData[] = shareholdersData?.shareholders || [];
  const grants: GrantData[] = grantsData?.grants || [];
  const transactions: TransactionData[] = transactionsData?.transactions || [];
  const holdings = holdingsData?.holdings || [];
  const valuations = valuationsData?.valuations || [];
  const summary = summaryData;

  const pieData = useMemo(() => {
    if (!summary?.ownership?.length) return [];
    return summary.ownership.map((o: OwnershipEntry) => ({
      name: o.name,
      value: o.ownership_percent,
      shares: o.total_fully_diluted,
    }));
  }, [summary]);

  const createShareholderMutation = useMutation({
    mutationFn: async (data: any) => {
      const res = await apiRequest('POST', `/api/companies/${companyId}/cap-table/shareholders`, data);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/companies', companyId, 'cap-table'] });
      toast({ title: 'Shareholder Added' });
      setShowShareholderDialog(false);
      setNewShareholder({ name: '', email: '', type: 'founder' });
    },
    onError: (e: unknown) => toast({ title: 'Error', description: getErrorMessage(e), variant: 'destructive' }),
  });

  const issueEquityMutation = useMutation({
    mutationFn: async (data: any) => {
      const res = await apiRequest('POST', `/api/companies/${companyId}/cap-table/issue`, data);
      return res.json();
    },
    onSuccess: () => {
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
      setGrantData({ shareholder_id: '', grant_type: 'iso', shares_granted: '', exercise_price: '', vesting_type: '4y_1y_cliff', cliff_months: '12', vesting_months: '48', notes: '' });
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
      setTransferData({ from_shareholder_id: '', to_shareholder_id: '', holding_id: '', shares: '', notes: '' });
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

  const valuationMutation = useMutation({
    mutationFn: async (data: any) => {
      const res = await apiRequest('POST', `/api/companies/${companyId}/cap-table/valuations`, data);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/companies', companyId, 'cap-table'] });
      toast({ title: '409A Valuation Recorded' });
      setShowValuationDialog(false);
      setValuationData({ valuation_date: '', fair_market_value: '', price_per_share: '', methodology: 'income', provider: '', notes: '' });
    },
    onError: (e: unknown) => toast({ title: 'Error', description: getErrorMessage(e), variant: 'destructive' }),
  });

  const dilutionMutation = useMutation({
    mutationFn: async (data: any) => {
      const res = await apiRequest('POST', `/api/companies/${companyId}/cap-table/model-dilution`, data);
      return res.json();
    },
    onSuccess: (data: any) => {
      setDilutionResult(data);
      toast({ title: 'Dilution Model Complete' });
    },
    onError: (e: unknown) => toast({ title: 'Error', description: getErrorMessage(e), variant: 'destructive' }),
  });

  if (!currentCompany) {
    return (
      <div className="p-6 flex items-center justify-center h-[60vh]">
        <Card className="max-w-md">
          <CardContent className="pt-6 text-center">
            <Building2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Company Selected</h3>
            <p className="text-muted-foreground">Select a company to manage your cap table.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <PieChart className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold" data-testid="text-cap-table-title">Cap Table</h1>
            <p className="text-muted-foreground text-sm">Manage equity, shareholders, option grants, and model dilution</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowShareholderDialog(true)} data-testid="button-add-shareholder">
            <Users className="h-4 w-4 mr-2" />
            Add Shareholder
          </Button>
          <Button onClick={() => setShowIssueDialog(true)} data-testid="button-issue-equity">
            <Plus className="h-4 w-4 mr-2" />
            Issue Equity
          </Button>
        </div>
      </div>

      {summaryLoading ? (
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
      ) : summary && summary.fully_diluted_shares > 0 ? (
        <div className="grid gap-4 md:grid-cols-4">
          <Card data-testid="stat-fully-diluted">
            <CardContent className="pt-4 pb-4">
              <p className="text-sm text-muted-foreground">Fully Diluted Shares</p>
              <p className="text-2xl font-bold">{formatNumber(summary.fully_diluted_shares)}</p>
              <p className="text-xs text-muted-foreground mt-1">{summary.total_shares_issued.toLocaleString()} issued</p>
            </CardContent>
          </Card>
          <Card data-testid="stat-shareholders">
            <CardContent className="pt-4 pb-4">
              <p className="text-sm text-muted-foreground">Shareholders</p>
              <p className="text-2xl font-bold">{shareholders.length}</p>
              <p className="text-xs text-muted-foreground mt-1">{summary.ownership.length} with equity</p>
            </CardContent>
          </Card>
          <Card data-testid="stat-options">
            <CardContent className="pt-4 pb-4">
              <p className="text-sm text-muted-foreground">Options Outstanding</p>
              <p className="text-2xl font-bold">{formatNumber(summary.total_options_granted - summary.total_options_exercised)}</p>
              <p className="text-xs text-muted-foreground mt-1">{formatNumber(summary.total_options_vested)} vested</p>
            </CardContent>
          </Card>
          <Card data-testid="stat-409a">
            <CardContent className="pt-4 pb-4">
              <p className="text-sm text-muted-foreground">409A FMV</p>
              {summary.latest_409a ? (
                <>
                  <p className="text-2xl font-bold">{formatCurrency(summary.latest_409a.price_per_share)}/sh</p>
                  <p className="text-xs text-muted-foreground mt-1">As of {summary.latest_409a.valuation_date}</p>
                </>
              ) : (
                <>
                  <p className="text-2xl font-bold text-muted-foreground">--</p>
                  <p className="text-xs text-amber-400 mt-1">No 409A on file</p>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      ) : null}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview" data-testid="tab-overview">
            <PieChart className="h-4 w-4 mr-2" />
            Ownership
          </TabsTrigger>
          <TabsTrigger value="shareholders" data-testid="tab-shareholders">
            <Users className="h-4 w-4 mr-2" />
            Shareholders
          </TabsTrigger>
          <TabsTrigger value="grants" data-testid="tab-grants">
            <Award className="h-4 w-4 mr-2" />
            Option Grants
          </TabsTrigger>
          <TabsTrigger value="transactions" data-testid="tab-transactions">
            <FileText className="h-4 w-4 mr-2" />
            Transactions
          </TabsTrigger>
          <TabsTrigger value="dilution" data-testid="tab-dilution">
            <Calculator className="h-4 w-4 mr-2" />
            Dilution Model
          </TabsTrigger>
          <TabsTrigger value="valuations" data-testid="tab-valuations">
            <Shield className="h-4 w-4 mr-2" />
            409A
          </TabsTrigger>
        </TabsList>

        {/* ─── Ownership Overview Tab ────────────────────── */}
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
            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Ownership Breakdown</CardTitle>
                  <CardDescription>Fully diluted ownership by shareholder</CardDescription>
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
                          outerRadius={120}
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
                          contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }}
                        />
                        <Legend />
                      </RechartsPie>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Cap Table</CardTitle>
                  <CardDescription>All shareholders sorted by ownership</CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Shareholder</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead className="text-right">Shares</TableHead>
                        <TableHead className="text-right">Ownership %</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {summary.ownership.map((o: OwnershipEntry) => (
                        <TableRow key={o.shareholder_id} data-testid={`row-ownership-${o.shareholder_id}`}>
                          <TableCell className="font-medium">{o.name}</TableCell>
                          <TableCell><TypeBadge type={o.type} /></TableCell>
                          <TableCell className="text-right">{o.total_fully_diluted.toLocaleString()}</TableCell>
                          <TableCell className="text-right font-semibold">{o.ownership_percent.toFixed(2)}%</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        {/* ─── Shareholders Tab ──────────────────────────── */}
        <TabsContent value="shareholders" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold">Shareholders</h2>
            <Button onClick={() => setShowShareholderDialog(true)} data-testid="button-add-shareholder-tab">
              <Plus className="h-4 w-4 mr-2" />
              Add Shareholder
            </Button>
          </div>

          {shareholdersLoading ? (
            <div className="space-y-3">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}</div>
          ) : shareholders.length === 0 ? (
            <EmptyStateCard
              icon={Users}
              title="No Shareholders"
              description="Add founders, employees, investors, and advisors to build your cap table."
              action={{ label: "Add Shareholder", onClick: () => setShowShareholderDialog(true), icon: Plus }}
            />
          ) : (
            <Card>
              <CardContent className="pt-4">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead className="text-right">Shares Held</TableHead>
                      <TableHead className="text-right">Options Granted</TableHead>
                      <TableHead className="text-right">Options Vested</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {shareholders.map((sh: ShareholderData) => (
                      <TableRow key={sh.id} data-testid={`row-shareholder-${sh.id}`}>
                        <TableCell className="font-medium">{sh.name}</TableCell>
                        <TableCell><TypeBadge type={sh.type} /></TableCell>
                        <TableCell className="text-muted-foreground">{sh.email || '--'}</TableCell>
                        <TableCell className="text-right">{sh.total_shares.toLocaleString()}</TableCell>
                        <TableCell className="text-right">{sh.total_options_granted.toLocaleString()}</TableCell>
                        <TableCell className="text-right">{sh.total_options_vested.toLocaleString()}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ─── Option Grants Tab ─────────────────────────── */}
        <TabsContent value="grants" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold">Option Grants</h2>
            <Button onClick={() => setShowGrantDialog(true)} data-testid="button-new-grant">
              <Plus className="h-4 w-4 mr-2" />
              New Grant
            </Button>
          </div>

          {grantsLoading ? (
            <div className="space-y-3">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-20 w-full" />)}</div>
          ) : grants.length === 0 ? (
            <EmptyStateCard
              icon={Award}
              title="No Option Grants"
              description="Create option grants for employees and advisors with customizable vesting schedules."
              action={{ label: "Create Grant", onClick: () => setShowGrantDialog(true), icon: Plus }}
            />
          ) : (
            <Card>
              <CardContent className="pt-4">
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
                      <TableHead></TableHead>
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
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}

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

        {/* ─── Transactions Tab ──────────────────────────── */}
        <TabsContent value="transactions" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold">Transaction History</h2>
            <Button variant="outline" onClick={() => setShowTransferDialog(true)} data-testid="button-transfer">
              <ArrowRightLeft className="h-4 w-4 mr-2" />
              Transfer Shares
            </Button>
          </div>

          {transactionsLoading ? (
            <div className="space-y-3">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}</div>
          ) : transactions.length === 0 ? (
            <EmptyStateCard
              icon={FileText}
              title="No Transactions"
              description="Transaction history will appear here as equity is issued, transferred, or exercised."
            />
          ) : (
            <Card>
              <CardContent className="pt-4">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>From</TableHead>
                      <TableHead>To</TableHead>
                      <TableHead>Class</TableHead>
                      <TableHead className="text-right">Shares</TableHead>
                      <TableHead className="text-right">Price/Share</TableHead>
                      <TableHead className="text-right">Total Value</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {transactions.map((tx: TransactionData) => (
                      <TableRow key={tx.id} data-testid={`row-tx-${tx.id}`}>
                        <TableCell className="text-muted-foreground">
                          {tx.effective_date || tx.created_at?.split('T')[0] || '--'}
                        </TableCell>
                        <TableCell><TxTypeBadge type={tx.transaction_type} /></TableCell>
                        <TableCell>{tx.from_shareholder_name || '--'}</TableCell>
                        <TableCell>{tx.to_shareholder_name || '--'}</TableCell>
                        <TableCell><Badge variant="outline">{tx.share_class || '--'}</Badge></TableCell>
                        <TableCell className="text-right">{tx.shares.toLocaleString()}</TableCell>
                        <TableCell className="text-right">{tx.price_per_share ? formatCurrency(tx.price_per_share) : '--'}</TableCell>
                        <TableCell className="text-right">{tx.total_value ? formatCurrency(tx.total_value) : '--'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ─── Dilution Modeling Tab ──────────────────────── */}
        <TabsContent value="dilution" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calculator className="h-5 w-5" />
                Dilution Scenario Modeling
              </CardTitle>
              <CardDescription>Model how a new fundraising round would impact ownership</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!summary || summary.fully_diluted_shares === 0 ? (
                <div className="text-center py-8">
                  <AlertTriangle className="h-8 w-8 mx-auto text-amber-400 mb-3" />
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
                        value={dilutionData.pre_money}
                        onChange={(e) => setDilutionData({ ...dilutionData, pre_money: e.target.value })}
                        data-testid="input-dilution-pre-money"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Raise Amount ($)</Label>
                      <Input
                        type="number"
                        placeholder="3000000"
                        value={dilutionData.raise_amount}
                        onChange={(e) => setDilutionData({ ...dilutionData, raise_amount: e.target.value })}
                        data-testid="input-dilution-raise"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Option Pool Refresh (%)</Label>
                      <Input
                        type="number"
                        placeholder="10"
                        value={dilutionData.option_pool_refresh_percent}
                        onChange={(e) => setDilutionData({ ...dilutionData, option_pool_refresh_percent: e.target.value })}
                        data-testid="input-dilution-pool"
                      />
                    </div>
                  </div>
                  <Button
                    onClick={() => dilutionMutation.mutate({
                      pre_money: parseFloat(dilutionData.pre_money) || 0,
                      raise_amount: parseFloat(dilutionData.raise_amount) || 0,
                      option_pool_refresh_percent: parseFloat(dilutionData.option_pool_refresh_percent) || 0,
                    })}
                    disabled={dilutionMutation.isPending}
                    data-testid="button-run-dilution"
                  >
                    <TrendingUp className="h-4 w-4 mr-2" />
                    {dilutionMutation.isPending ? 'Modeling...' : 'Run Dilution Model'}
                  </Button>

                  {dilutionResult && (
                    <div className="mt-6 space-y-4">
                      <div className="grid gap-4 md:grid-cols-4">
                        <Card className="bg-muted/50">
                          <CardContent className="pt-4 pb-4">
                            <p className="text-xs text-muted-foreground">Post-Money</p>
                            <p className="text-lg font-bold text-green-400">{formatCurrency(dilutionResult.post_money)}</p>
                          </CardContent>
                        </Card>
                        <Card className="bg-muted/50">
                          <CardContent className="pt-4 pb-4">
                            <p className="text-xs text-muted-foreground">Price/Share</p>
                            <p className="text-lg font-bold">{formatCurrency(dilutionResult.price_per_share)}</p>
                          </CardContent>
                        </Card>
                        <Card className="bg-muted/50">
                          <CardContent className="pt-4 pb-4">
                            <p className="text-xs text-muted-foreground">New Investor %</p>
                            <p className="text-lg font-bold text-blue-400">{dilutionResult.new_investor_percent}%</p>
                          </CardContent>
                        </Card>
                        <Card className="bg-muted/50">
                          <CardContent className="pt-4 pb-4">
                            <p className="text-xs text-muted-foreground">New Fully Diluted</p>
                            <p className="text-lg font-bold">{formatNumber(dilutionResult.new_fully_diluted)}</p>
                          </CardContent>
                        </Card>
                      </div>

                      {dilutionResult.after_ownership?.length > 0 && (
                        <Card className="bg-muted/50">
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm">Ownership Impact</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead>Shareholder</TableHead>
                                  <TableHead className="text-right">Before %</TableHead>
                                  <TableHead className="text-right">After %</TableHead>
                                  <TableHead className="text-right">Dilution</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {dilutionResult.after_ownership.map((row: any, i: number) => {
                                  const before = dilutionResult.before_ownership?.[i];
                                  return (
                                    <TableRow key={row.shareholder_id}>
                                      <TableCell className="font-medium">{row.shareholder_id.slice(0, 8)}...</TableCell>
                                      <TableCell className="text-right">{before?.percent?.toFixed(2)}%</TableCell>
                                      <TableCell className="text-right">{row.percent?.toFixed(2)}%</TableCell>
                                      <TableCell className="text-right text-red-400">-{row.dilution?.toFixed(2)}%</TableCell>
                                    </TableRow>
                                  );
                                })}
                              </TableBody>
                            </Table>
                          </CardContent>
                        </Card>
                      )}
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ─── 409A Valuations Tab ───────────────────────── */}
        <TabsContent value="valuations" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold">409A Valuations</h2>
            <Button onClick={() => setShowValuationDialog(true)} data-testid="button-add-valuation">
              <Plus className="h-4 w-4 mr-2" />
              Record Valuation
            </Button>
          </div>

          {valuations.length === 0 ? (
            <EmptyStateCard
              icon={Shield}
              title="No 409A Valuations"
              description="Record your 409A valuations to ensure compliance for option pricing. Required before issuing stock options to employees."
              action={{ label: "Record Valuation", onClick: () => setShowValuationDialog(true), icon: Plus }}
            />
          ) : (
            <div className="space-y-4">
              {valuations.map((v: any) => (
                <Card key={v.id} data-testid={`card-valuation-${v.id}`}>
                  <CardContent className="pt-4 pb-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-semibold">FMV: {formatCurrency(v.price_per_share)}/share</p>
                        <p className="text-sm text-muted-foreground">
                          Total: {formatCurrency(v.fair_market_value)} | {v.methodology || 'N/A'} method
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          Valuation Date: {v.valuation_date} {v.expiration_date ? `| Expires: ${v.expiration_date}` : ''}
                        </p>
                      </div>
                      <Badge className={v.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}>
                        {v.status}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* ─── Dialogs ─────────────────────────────────────── */}

      {/* Add Shareholder Dialog */}
      <Dialog open={showShareholderDialog} onOpenChange={setShowShareholderDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Shareholder</DialogTitle>
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

      {/* Issue Equity Dialog */}
      <Dialog open={showIssueDialog} onOpenChange={setShowIssueDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Issue Equity</DialogTitle>
            <DialogDescription>Issue shares to a shareholder. This creates a new equity holding and records the transaction.</DialogDescription>
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

      {/* Option Grant Dialog */}
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
              })}
              disabled={createGrantMutation.isPending || !grantData.shareholder_id || !grantData.shares_granted}
              data-testid="button-save-grant"
            >
              Create Grant
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Exercise Options Dialog */}
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

      {/* Transfer Shares Dialog */}
      <Dialog open={showTransferDialog} onOpenChange={setShowTransferDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Transfer Shares</DialogTitle>
            <DialogDescription>Transfer shares between shareholders.</DialogDescription>
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
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowTransferDialog(false)}>Cancel</Button>
            <Button
              onClick={() => transferMutation.mutate({
                from_shareholder_id: transferData.from_shareholder_id,
                to_shareholder_id: transferData.to_shareholder_id,
                holding_id: transferData.holding_id,
                shares: parseFloat(transferData.shares) || 0,
              })}
              disabled={transferMutation.isPending || !transferData.from_shareholder_id || !transferData.to_shareholder_id || !transferData.holding_id || !transferData.shares}
              data-testid="button-confirm-transfer"
            >
              Transfer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 409A Valuation Dialog */}
      <Dialog open={showValuationDialog} onOpenChange={setShowValuationDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Record 409A Valuation</DialogTitle>
            <DialogDescription>Record your latest 409A valuation for compliance and option pricing.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid gap-4 grid-cols-2">
              <div className="space-y-2">
                <Label>Valuation Date</Label>
                <Input
                  type="date"
                  value={valuationData.valuation_date}
                  onChange={(e) => setValuationData({ ...valuationData, valuation_date: e.target.value })}
                  data-testid="input-valuation-date"
                />
              </div>
              <div className="space-y-2">
                <Label>Methodology</Label>
                <Select value={valuationData.methodology} onValueChange={(v) => setValuationData({ ...valuationData, methodology: v })}>
                  <SelectTrigger data-testid="select-methodology"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="income">Income Approach</SelectItem>
                    <SelectItem value="market">Market Approach</SelectItem>
                    <SelectItem value="asset">Asset-Based</SelectItem>
                    <SelectItem value="backsolve">OPM Backsolve</SelectItem>
                    <SelectItem value="hybrid">Hybrid</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid gap-4 grid-cols-2">
              <div className="space-y-2">
                <Label>Fair Market Value ($)</Label>
                <Input
                  type="number"
                  value={valuationData.fair_market_value}
                  onChange={(e) => setValuationData({ ...valuationData, fair_market_value: e.target.value })}
                  placeholder="5000000"
                  data-testid="input-fmv"
                />
              </div>
              <div className="space-y-2">
                <Label>Price per Share ($)</Label>
                <Input
                  type="number"
                  value={valuationData.price_per_share}
                  onChange={(e) => setValuationData({ ...valuationData, price_per_share: e.target.value })}
                  placeholder="0.50"
                  data-testid="input-fmv-pps"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Provider</Label>
              <Input
                value={valuationData.provider}
                onChange={(e) => setValuationData({ ...valuationData, provider: e.target.value })}
                placeholder="Carta, Eqvista, etc."
                data-testid="input-valuation-provider"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowValuationDialog(false)}>Cancel</Button>
            <Button
              onClick={() => valuationMutation.mutate({
                valuation_date: valuationData.valuation_date,
                fair_market_value: parseFloat(valuationData.fair_market_value) || 0,
                price_per_share: parseFloat(valuationData.price_per_share) || 0,
                methodology: valuationData.methodology,
                provider: valuationData.provider || null,
              })}
              disabled={valuationMutation.isPending || !valuationData.valuation_date || !valuationData.fair_market_value}
              data-testid="button-save-valuation"
            >
              Save Valuation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
