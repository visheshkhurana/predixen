import { formatCurrencyFull, formatCurrencyAbbrev } from '@/lib/utils';
import {
  BOARD_STAGES, groupByStage, pipelineSummary, currentRound, relativeActivity, stageLabel,
  type BoardEntry, type BoardStage,
} from '@/lib/fundraisingPipeline';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSEO } from "@/lib/seo";
import { FadeIn, StaggerContainer, StaggerItem } from "@/components/motion/animated-container";
import { FloatingOrbsBackground } from "@/components/motion/floating-orbs-background";
import { PageTransition } from "@/components/motion/page-transition-wrapper";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useToast } from '@/hooks/use-toast';
import { useFounderStore } from '@/store/founderStore';
import { getErrorMessage } from '@/lib/errors';
import { CrossPageIntelligence } from '@/components/CrossPageIntelligence';
import { apiRequest } from '@/lib/queryClient';
import {
  Plus, DollarSign, TrendingUp, PieChart,
  Calculator, Play, Building2, Target, Mail,
  Clock, BarChart3, CheckCircle2, AlertCircle, Pause, Send,
  Kanban, Database, Search, MapPin, Star,
  GripVertical, LayoutGrid, List,
  Calendar, ChevronRight
} from 'lucide-react';
import { EmptyStateCard } from '@/components/ui/empty-state';
import { trackEvent } from '@/lib/posthog';
import { ReadinessScore } from '@/components/fundraising/ReadinessScore';
import { RecommendationsList } from '@/components/fundraising/RecommendationsList';
import { RaiseWindow } from '@/components/fundraising/RaiseWindow';
import investorDatabaseRaw from '@/data/investor-database.json';

interface CapTable {
  id: string;
  name: string;
  as_of_date: string | null;
  currency: string;
  cap_table: {
    common: Array<{ holder: string; shares: number; percent: number }>;
    preferred: Array<{ series: string; holder: string; shares: number; percent: number; liquidation_pref: string }>;
    options: { pool_percent: number; allocated_percent: number };
    notes: Array<{ holder: string; principal: number; conversion_cap: number | null; discount: number }>;
    fully_diluted_shares: number;
  };
}

interface FundraisingRound {
  id: string;
  name: string;
  target_raise: number | null;
  pre_money: number | null;
  post_money: number | null;
  instrument: string;
  option_pool_refresh_percent: number | null;
  status: string;
}

interface PipelineInvestor {
  id: string;
  firm: string;
  partner: string;
  checkSize: string;
  lastActivity: string;
  sentiment: 'green' | 'yellow' | 'red';
  warmIntro: boolean;
  stage: string;
}

interface InvestorDBEntry {
  id: number;
  name: string;
  type: string;
  originalType: string;
  address: string;
  phone: string;
  email: string;
  website: string;
  dealSize: string;
  notableInvestments: string;
  stages: string[];
  countries: string;
  yearFounded: number | null;
  aum: string;
  region: string;
  fitScore: number;
  initials: string;
  color: string;
}

const STATUS_COLORS: Record<string, string> = {
  planned: 'bg-yellow-500/20 text-yellow-600',
  active: 'bg-blue-500/20 text-blue-600',
  closed: 'bg-green-500/20 text-green-600',
};

const INVESTOR_DB: InvestorDBEntry[] = investorDatabaseRaw as InvestorDBEntry[];

const INVESTOR_REGIONS = ['All Regions', 'USA', 'India', 'Korea', 'Japan', 'Global'] as const;
const INVESTOR_TYPES = [
  { value: 'all', label: 'All' },
  { value: 'VC', label: 'VC' },
  { value: 'PE', label: 'PE' },
  { value: 'CVC', label: 'CVC' },
  { value: 'Family Office', label: 'Family Office' },
  { value: 'Angels', label: 'Angels' },
  { value: 'Accelerator', label: 'Accelerators' },
] as const;
const INVESTOR_STAGES = ['All Stages', 'Pre-Seed', 'Seed', 'Series A', 'Series B', 'Series C', 'Growth', 'Late Stage'] as const;
const INVESTORS_PER_PAGE = 30;

function getFitScoreColor(score: number): string {
  if (score >= 80) return 'text-emerald-500';
  if (score >= 60) return 'text-yellow-500';
  return 'text-red-500';
}

function getFitScoreBarColor(score: number): string {
  if (score >= 80) return 'bg-emerald-500';
  if (score >= 60) return 'bg-yellow-500';
  return 'bg-red-500';
}

const STAGE_COLORS: Record<BoardStage, string> = {
  sourced: 'border-t-slate-400',
  contacted: 'border-t-blue-400',
  meeting: 'border-t-cyan-400',
  partner_meeting: 'border-t-indigo-400',
  dd: 'border-t-purple-400',
  term_sheet: 'border-t-amber-400',
  committed: 'border-t-emerald-400',
  closed: 'border-t-green-500',
  passed: 'border-t-red-400',
};

function pipelineKey(companyId: number | undefined) {
  return ['/api/companies', companyId, 'fundraising', 'pipeline-board'];
}

function usePipelineBoard(companyId: number | undefined) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const key = pipelineKey(companyId);
  const query = useQuery<{ entries: BoardEntry[] }>({
    queryKey: key,
    queryFn: async () => (await apiRequest('GET', `/api/companies/${companyId}/fundraising/pipeline`)).json(),
    enabled: !!companyId,
  });
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: key });
    queryClient.invalidateQueries({ queryKey: ['/api/companies', companyId, 'fundraising/rounds'] });
  };
  const onError = (error: unknown) =>
    toast({ title: 'Could not save', description: getErrorMessage(error), variant: 'destructive' });

  const add = useMutation({
    mutationFn: async (body: { firm: string; partner?: string; check_size?: string; stage?: BoardStage; warm_intro?: boolean }) =>
      (await apiRequest('POST', `/api/companies/${companyId}/fundraising/pipeline`, body)).json(),
    onSuccess: (entry: BoardEntry) => {
      refresh();
      toast({ title: 'Added to pipeline', description: `${entry.firm} added to ${stageLabel(entry.stage)}` });
    },
    onError,
  });
  const move = useMutation({
    mutationFn: async ({ id, stage }: { id: string; stage: BoardStage }) =>
      (await apiRequest('PATCH', `/api/companies/${companyId}/fundraising/pipeline-board/${id}`, { stage })).json(),
    onMutate: async ({ id, stage }) => {
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData<{ entries: BoardEntry[] }>(key);
      if (previous) {
        queryClient.setQueryData(key, { ...previous, entries: previous.entries.map(e => (e.id === id ? { ...e, stage } : e)) });
      }
      return { previous };
    },
    onError: (error, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(key, context.previous);
      onError(error);
    },
    onSettled: refresh,
  });
  const remove = useMutation({
    mutationFn: async (id: string) => (await apiRequest('DELETE', `/api/companies/${companyId}/fundraising/pipeline-board/${id}`)).json(),
    onSuccess: refresh,
    onError,
  });
  return { entries: query.data?.entries ?? [], isLoading: query.isLoading, add, move, remove };
}

function DashboardBanner({ entries, rounds, currency, isLoading }: {
  entries: BoardEntry[];
  rounds: any[];
  currency?: string;
  isLoading: boolean;
}) {
  const summary = pipelineSummary(entries);
  const round = currentRound(rounds);
  if (isLoading) {
    return <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">{[0, 1, 2].map(i => <Skeleton key={i} className="h-24" />)}</div>;
  }
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3" data-testid="dashboard-banner">
      <Card className="border-border/50" data-testid="banner-card-raised">
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Current Round</span>
            <DollarSign className="h-4 w-4 text-emerald-500" />
          </div>
          {round ? (
            <>
              <div className="text-base font-semibold truncate" data-testid="text-round-name">{round.name}</div>
              <div className="text-sm text-muted-foreground" data-testid="text-amount-raised">
                {round.target_raise ? `Target ${formatCurrencyAbbrev(round.target_raise, currency)}` : 'No target set yet'}
                {' · '}{summary.committed} committed
              </div>
            </>
          ) : (
            <div className="text-sm text-muted-foreground" data-testid="text-amount-raised">
              No round yet. Add one in the Rounds tab, or add an investor below to start.
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/50" data-testid="banner-card-pipeline">
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Pipeline</span>
            <Kanban className="h-4 w-4 text-blue-500" />
          </div>
          {summary.total === 0 ? (
            <div className="text-sm text-muted-foreground" data-testid="text-pipeline-funnel">No investors tracked yet</div>
          ) : (
            <>
              <div className="flex items-center gap-1 text-sm flex-wrap" data-testid="text-pipeline-funnel">
                {summary.funnel.map((step, i) => (
                  <span key={step.label} className="flex items-center gap-1">
                    {i > 0 && <ChevronRight className="h-3 w-3 text-muted-foreground" />}
                    <span className={i === summary.funnel.length - 1 ? 'font-bold text-emerald-500' : 'font-semibold'}>{step.count}</span>
                  </span>
                ))}
              </div>
              <div className="flex gap-1.5 mt-2 text-[10px] text-muted-foreground flex-wrap">
                {summary.funnel.map((step, i) => (
                  <span key={step.label}>{i > 0 && '· '}{step.label}</span>
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/50" data-testid="banner-card-warm">
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Investors</span>
            <Star className="h-4 w-4 text-amber-500" />
          </div>
          <div className="flex items-baseline gap-3 text-sm">
            <span><span className="text-xl font-bold">{summary.active}</span> <span className="text-muted-foreground">active</span></span>
            <span><span className="font-semibold">{summary.warmIntros}</span> <span className="text-muted-foreground">warm intros</span></span>
            <span><span className="font-semibold">{summary.passed}</span> <span className="text-muted-foreground">passed</span></span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function PipelineCard({ investor, onDragStart, onRemove }: {
  investor: BoardEntry;
  onDragStart: (investorId: string) => void;
  onRemove: (investorId: string) => void;
}) {
  return (
    <Card
      className="mb-2 cursor-grab active:cursor-grabbing hover:border-primary/40 transition-colors group"
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData('text/plain', investor.id);
        e.dataTransfer.effectAllowed = 'move';
        onDragStart(investor.id);
      }}
      data-testid={`pipeline-card-${investor.id}`}
    >
      <CardContent className="p-3">
        <div className="flex items-start gap-2">
          <GripVertical className="h-4 w-4 text-muted-foreground/40 mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 mb-1">
              <span className="font-medium text-sm truncate" data-testid={`text-pipeline-firm-${investor.id}`}>
                {investor.firm}
              </span>
            </div>
            {investor.partner && <p className="text-xs text-muted-foreground truncate">{investor.partner}</p>}
            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
              {investor.check_size && <Badge variant="outline" className="text-[10px] px-1.5 py-0">{investor.check_size}</Badge>}
              {investor.warm_intro && (
                <Badge className="text-[10px] px-1.5 py-0 bg-amber-500/15 text-amber-600 border-transparent">
                  <Star className="h-2.5 w-2.5 mr-0.5" />Warm
                </Badge>
              )}
            </div>
            <p className="text-[10px] text-muted-foreground mt-1.5">{relativeActivity(investor.last_activity_at)}</p>
          </div>
          <button
            type="button"
            className="text-[10px] text-muted-foreground opacity-0 group-hover:opacity-100 focus:opacity-100 hover:text-destructive"
            onClick={() => onRemove(investor.id)}
            aria-label={`Remove ${investor.firm}`}
            data-testid={`button-remove-pipeline-${investor.id}`}
          >
            Remove
          </button>
        </div>
      </CardContent>
    </Card>
  );
}

function PipelineTab({ board }: { board: ReturnType<typeof usePipelineBoard> }) {
  const [viewMode, setViewMode] = useState<'board' | 'table'>('board');
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<BoardStage | null>(null);
  const grouped = groupByStage(board.entries);

  const handleDrop = (target: BoardStage) => {
    const investor = board.entries.find(e => e.id === draggingId);
    setDraggingId(null);
    setDragOverColumn(null);
    if (!investor || investor.stage === target) return;
    board.move.mutate({ id: investor.id, stage: target });
  };

  const headerBar = (isBoardActive: boolean) => (
    <div className="flex items-center justify-between flex-wrap gap-2">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-semibold">Pipeline</h2>
        <Badge variant="outline">{board.entries.length} investors</Badge>
      </div>
      <div className="flex items-center gap-2">
        <Button variant={isBoardActive ? 'default' : 'outline'} size="sm" onClick={() => setViewMode('board')} data-testid="button-board-view">
          <LayoutGrid className="h-4 w-4 mr-1" /> Board
        </Button>
        <Button variant={!isBoardActive ? 'default' : 'outline'} size="sm" onClick={() => setViewMode('table')} data-testid="button-table-view">
          <List className="h-4 w-4 mr-1" /> Table
        </Button>
        <Button size="sm" onClick={() => setShowAddDialog(true)} data-testid="button-add-investor-pipeline">
          <Plus className="h-4 w-4 mr-1" /> Add Investor
        </Button>
      </div>
    </div>
  );

  const dialog = (
    <AddInvestorDialog
      open={showAddDialog}
      onClose={() => setShowAddDialog(false)}
      onAdd={(body) => board.add.mutate(body, { onSuccess: () => setShowAddDialog(false) })}
      saving={board.add.isPending}
    />
  );

  if (board.isLoading) {
    return <div className="space-y-4">{headerBar(viewMode === 'board')}<Skeleton className="h-64 w-full" /></div>;
  }

  if (board.entries.length === 0) {
    return (
      <div className="space-y-4">
        {headerBar(viewMode === 'board')}
        <EmptyStateCard
          icon={Kanban}
          title="No investors in your pipeline yet"
          description="Add the funds and angels you're talking to, then drag them across stages as conversations move. You can also add investors from the Investor Database tab."
          action={{ label: 'Add your first investor', onClick: () => setShowAddDialog(true), icon: Plus }}
        />
        {dialog}
      </div>
    );
  }

  if (viewMode === 'table') {
    return (
      <div className="space-y-4">
        {headerBar(false)}
        <Card>
          <div className="mobile-table-scroll">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Firm</TableHead>
                  <TableHead>Partner</TableHead>
                  <TableHead>Stage</TableHead>
                  <TableHead>Check Size</TableHead>
                  <TableHead>Warm intro</TableHead>
                  <TableHead>Last Activity</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {board.entries.map(inv => (
                  <TableRow key={inv.id} data-testid={`table-row-${inv.id}`}>
                    <TableCell className="font-medium">{inv.firm}</TableCell>
                    <TableCell className="text-muted-foreground">{inv.partner || '—'}</TableCell>
                    <TableCell><Badge variant="outline" className="text-xs">{stageLabel(inv.stage)}</Badge></TableCell>
                    <TableCell>{inv.check_size || '—'}</TableCell>
                    <TableCell>{inv.warm_intro ? 'Yes' : 'No'}</TableCell>
                    <TableCell className="text-muted-foreground text-sm">{relativeActivity(inv.last_activity_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
        {dialog}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {headerBar(true)}
      <div className="overflow-x-auto pb-4 -mx-4 px-4" data-testid="pipeline-kanban">
        <div className="flex gap-3" style={{ minWidth: `${BOARD_STAGES.length * 240}px` }}>
          {BOARD_STAGES.map(({ key, label }) => (
            <div
              key={key}
              className={`flex-1 min-w-[220px] max-w-[280px] rounded-lg border border-border/50 border-t-2 ${STAGE_COLORS[key]} p-3 transition-colors ${
                dragOverColumn === key ? 'bg-primary/10 border-primary/40' : 'bg-muted/30'
              }`}
              onDragOver={(e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                setDragOverColumn(key);
              }}
              onDragLeave={() => setDragOverColumn(null)}
              onDrop={(e) => {
                e.preventDefault();
                handleDrop(key);
              }}
              data-testid={`pipeline-column-${label.toLowerCase().replace(/\s/g, '-')}`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</span>
                <Badge variant="outline" className="text-[10px] h-5 px-1.5">{grouped[key].length}</Badge>
              </div>
              <div className="space-y-0 min-h-[120px]">
                {grouped[key].map(investor => (
                  <PipelineCard key={investor.id} investor={investor} onDragStart={setDraggingId} onRemove={(id) => board.remove.mutate(id)} />
                ))}
                {grouped[key].length === 0 && (
                  <div className="flex items-center justify-center h-[100px] border border-dashed border-border/50 rounded-lg">
                    <span className="text-xs text-muted-foreground">Drop here</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
      {dialog}
    </div>
  );
}

function AddInvestorDialog({ open, onClose, onAdd, saving }: {
  open: boolean;
  onClose: () => void;
  onAdd: (body: { firm: string; partner: string; check_size: string; stage: BoardStage; warm_intro: boolean }) => void;
  saving: boolean;
}) {
  const { toast } = useToast();
  const blank = { firm: '', partner: '', check_size: '', stage: 'sourced' as BoardStage, warm_intro: false };
  const [form, setForm] = useState(blank);

  const handleAdd = () => {
    if (!form.firm.trim()) {
      toast({ title: 'Firm name is required', variant: 'destructive' });
      return;
    }
    onAdd(form);
    setForm(blank);
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Investor to Pipeline</DialogTitle>
          <DialogDescription>Track a fund or angel you're talking to. Only your team can see this.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="fundraising-firm-name">Firm or angel name</Label>
            <Input id="fundraising-firm-name" value={form.firm} onChange={e => setForm({ ...form, firm: e.target.value })} data-testid="input-add-firm" />
          </div>
          <div className="grid gap-4 grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="fundraising-key-partner">Contact person</Label>
              <Input id="fundraising-key-partner" value={form.partner} onChange={e => setForm({ ...form, partner: e.target.value })} data-testid="input-add-partner" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="fundraising-check-size">Check Size</Label>
              <Input id="fundraising-check-size" value={form.check_size} onChange={e => setForm({ ...form, check_size: e.target.value })} placeholder="e.g. ₹2–5Cr" data-testid="input-add-check-size" />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Pipeline Stage</Label>
            <Select value={form.stage} onValueChange={v => setForm({ ...form, stage: v as BoardStage })}>
              <SelectTrigger data-testid="select-add-stage">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {BOARD_STAGES.map(s => (
                  <SelectItem key={s.key} value={s.key}>{s.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.warm_intro} onChange={e => setForm({ ...form, warm_intro: e.target.checked })} data-testid="checkbox-add-warm" />
            I have a warm intro
          </label>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleAdd} disabled={saving} data-testid="button-save-add-investor">{saving ? 'Adding…' : 'Add to Pipeline'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function InvestorDatabaseTab({ onAdd }: { onAdd: (body: { firm: string; stage: BoardStage }) => void }) {
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [regionFilter, setRegionFilter] = useState<string>('All Regions');
  const [stageFilter, setStageFilter] = useState<string>('All Stages');
  const [page, setPage] = useState(1);
  const { toast } = useToast();

  const filtered = INVESTOR_DB.filter(inv => {
    const q = search.toLowerCase();
    const matchesSearch = !search ||
      inv.name.toLowerCase().includes(q) ||
      inv.originalType.toLowerCase().includes(q) ||
      inv.countries.toLowerCase().includes(q) ||
      inv.notableInvestments.toLowerCase().includes(q) ||
      inv.region.toLowerCase().includes(q);
    const matchesType = typeFilter === 'all' || inv.type === typeFilter;
    const matchesRegion = regionFilter === 'All Regions' || inv.region === regionFilter;
    const matchesStage = stageFilter === 'All Stages' ||
      inv.stages.some(s => s.toLowerCase().includes(stageFilter.toLowerCase()));
    return matchesSearch && matchesType && matchesRegion && matchesStage;
  });

  const paginated = filtered.slice(0, page * INVESTORS_PER_PAGE);
  const hasMore = paginated.length < filtered.length;

  const resetFilters = () => {
    setSearch('');
    setTypeFilter('all');
    setRegionFilter('All Regions');
    setStageFilter('All Stages');
    setPage(1);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">Investor Database</h2>
          <Badge variant="outline" data-testid="text-investor-count">{filtered.length} investors</Badge>
        </div>
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search firms, portfolios, regions..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
            className="pl-9"
            data-testid="input-search-investors"
          />
        </div>
      </div>

      <div className="flex gap-2 flex-wrap" data-testid="investor-category-filters">
        {INVESTOR_TYPES.map(cat => (
          <Button
            key={cat.value}
            variant={typeFilter === cat.value ? 'default' : 'outline'}
            size="sm"
            onClick={() => { setTypeFilter(cat.value); setPage(1); }}
            data-testid={`filter-category-${cat.value}`}
          >
            {cat.label}
          </Button>
        ))}
      </div>

      <div className="flex gap-2 flex-wrap items-center">
        <Select value={regionFilter} onValueChange={(v) => { setRegionFilter(v); setPage(1); }}>
          <SelectTrigger className="w-[160px] h-8 text-xs" data-testid="filter-region">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {INVESTOR_REGIONS.map(r => (
              <SelectItem key={r} value={r}>{r}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={stageFilter} onValueChange={(v) => { setStageFilter(v); setPage(1); }}>
          <SelectTrigger className="w-[160px] h-8 text-xs" data-testid="filter-stage">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {INVESTOR_STAGES.map(s => (
              <SelectItem key={s} value={s}>{s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {(typeFilter !== 'all' || regionFilter !== 'All Regions' || stageFilter !== 'All Stages' || search) && (
          <Button variant="ghost" size="sm" onClick={resetFilters} className="text-xs h-8" data-testid="button-clear-filters">
            Clear filters
          </Button>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {paginated.map(inv => (
          <Card key={inv.id} className="hover:border-primary/30 transition-colors" data-testid={`investor-card-${inv.id}`}>
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <div className={`h-10 w-10 rounded-lg ${inv.color} flex items-center justify-center shrink-0`}>
                  <span className="text-white font-bold text-sm">{inv.initials}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-sm truncate" data-testid={`text-investor-firm-${inv.id}`}>{inv.name}</h3>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">{inv.type}</Badge>
                    <span className="text-[10px] text-muted-foreground">{inv.region}</span>
                  </div>
                </div>
                <div className="text-right shrink-0" data-testid={`fit-score-${inv.id}`}>
                  <span className={`text-lg font-bold ${getFitScoreColor(inv.fitScore)}`}>{inv.fitScore}</span>
                  <p className="text-[10px] text-muted-foreground">Fit Score</p>
                </div>
              </div>

              <div className="mt-3">
                <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                  <div className={`h-full rounded-full transition-all ${getFitScoreBarColor(inv.fitScore)}`} style={{ width: `${inv.fitScore}%` }} />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-3 text-xs">
                {inv.aum && (
                  <div className="flex items-center gap-1 text-muted-foreground">
                    <DollarSign className="h-3 w-3" />
                    <span className="truncate">AUM {inv.aum}</span>
                  </div>
                )}
                <div className="flex items-center gap-1 text-muted-foreground">
                  <MapPin className="h-3 w-3" />
                  <span className="truncate">{inv.countries || inv.region}</span>
                </div>
                {inv.dealSize && (
                  <div className="col-span-2 flex items-center gap-1 text-muted-foreground">
                    <Target className="h-3 w-3" />
                    <span className="truncate">{inv.dealSize}</span>
                  </div>
                )}
              </div>

              {inv.stages.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {inv.stages.slice(0, 4).map(stage => (
                    <Badge key={stage} variant="outline" className="text-[10px] px-1.5 py-0">{stage}</Badge>
                  ))}
                  {inv.stages.length > 4 && (
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0">+{inv.stages.length - 4}</Badge>
                  )}
                </div>
              )}

              {inv.notableInvestments && (
                <p className="text-[10px] text-muted-foreground mt-2 line-clamp-1" title={inv.notableInvestments}>
                  Portfolio: {inv.notableInvestments}
                </p>
              )}

              <div className="flex gap-2 mt-3">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() => onAdd({ firm: inv.name, stage: 'sourced' })}
                  data-testid={`button-add-to-pipeline-${inv.id}`}
                >
                  <Plus className="h-3.5 w-3.5 mr-1" /> Add to Pipeline
                </Button>
                {inv.website && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="px-2"
                    onClick={() => window.open(inv.website, '_blank')}
                    data-testid={`button-website-${inv.id}`}
                  >
                    <ChevronRight className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
        {filtered.length === 0 && (
          <div className="col-span-full text-center py-12 text-muted-foreground">
            <Database className="h-10 w-10 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No investors match your filters</p>
            <Button variant="ghost" size="sm" onClick={resetFilters} className="mt-2 text-primary underline-offset-4 hover:underline" data-testid="button-reset-filters">Reset all filters</Button>
          </div>
        )}
      </div>

      {hasMore && (
        <div className="flex justify-center pt-2">
          <Button
            variant="outline"
            onClick={() => setPage(p => p + 1)}
            data-testid="button-load-more-investors"
          >
            Show More ({filtered.length - paginated.length} remaining)
          </Button>
        </div>
      )}

      {!hasMore && filtered.length > INVESTORS_PER_PAGE && (
        <p className="text-center text-xs text-muted-foreground pt-2">
          Showing all {filtered.length} investors
        </p>
      )}
    </div>
  );
}

const OUTREACH_PLAYBOOKS = [
  { id: 'cold-outreach', title: 'Cold outreach', steps: 'Personalised first email → follow-up after 4 days → traction update → close the loop' },
  { id: 'warm-intro', title: 'Warm intro request', steps: 'Write a 3-line forwardable blurb → send to your connector → nudge after 5 days' },
  { id: 'post-meeting', title: 'After a meeting', steps: 'Thank-you within an hour → data room or deck in 3 days → check in after a week' },
  { id: 'investor-update', title: 'Monthly investor update', steps: 'Revenue, burn, runway, wins, asks — same format every month' },
  { id: 'reengagement', title: 'Re-engage investors who passed', steps: 'Share a milestone they cared about → ask if timing is better now' },
];

function OutreachTab() {
  return (
    <div className="space-y-4" data-testid="tab-content-outreach">
      <div>
        <h2 className="text-lg font-semibold">Outreach playbooks</h2>
        <p className="text-sm text-muted-foreground">
          Proven sequences to follow by hand. FounderConsole doesn't send investor emails for you yet, so there are no open or reply rates here.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {OUTREACH_PLAYBOOKS.map(p => (
          <Card key={p.id} data-testid={`card-playbook-${p.id}`}>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">{p.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-start gap-2 text-sm text-muted-foreground">
                <Clock className="h-4 w-4 mt-0.5 shrink-0" /><span>{p.steps}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

export default function FundraisingPage() {
  useSEO({
    title: "Fundraising Intelligence — Startup Fundraising Tools | FounderConsole",
    description: "Pipeline CRM, investor database, outreach tracking, and fundraising readiness scoring. Manage your entire fundraising process from first contact to close.",
    path: "/fundraising",
    robots: "noindex, nofollow",
  });
  const { currentCompany: selectedCompany } = useFounderStore();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState('pipeline');
  const [showCapTableDialog, setShowCapTableDialog] = useState(false);
  const [showRoundDialog, setShowRoundDialog] = useState(false);

  const [newCapTableName, setNewCapTableName] = useState('Current Cap Table');
  const [newRound, setNewRound] = useState({
    name: '',
    target_raise: '',
    pre_money: '',
    instrument: 'equity',
    option_pool_refresh_percent: ''
  });

  const [simulationConfig, setSimulationConfig] = useState({
    cap_table_id: '',
    pre_money: '',
    raise: '',
    option_pool_refresh: ''
  });

  const { data: capTablesData, isLoading: capTablesLoading } = useQuery({
    queryKey: ['/api/companies', selectedCompany?.id, 'cap-tables'],
    queryFn: async () => {
      const res = await apiRequest('GET', `/api/companies/${selectedCompany?.id}/cap-tables`);
      return res.json();
    },
    enabled: !!selectedCompany?.id,
  });

  const { data: roundsData, isLoading: roundsLoading } = useQuery({
    queryKey: ['/api/companies', selectedCompany?.id, 'fundraising/rounds'],
    queryFn: async () => {
      const res = await apiRequest('GET', `/api/companies/${selectedCompany?.id}/fundraising/rounds`);
      return res.json();
    },
    enabled: !!selectedCompany?.id,
  });

  const { data: readinessData, isLoading: readinessLoading } = useQuery<any>({
    queryKey: ['/api/companies', selectedCompany?.id, 'fundraising', 'readiness'],
    enabled: !!selectedCompany?.id,
  });

  const createCapTableMutation = useMutation({
    mutationFn: async (data: { name: string }) => {
      const res = await apiRequest('POST', `/api/companies/${selectedCompany?.id}/cap-tables`, data);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/companies', selectedCompany?.id, 'cap-tables'] });
      toast({ title: 'Cap Table Created', description: 'Your cap table has been created.' });
      setShowCapTableDialog(false);
      setNewCapTableName('Current Cap Table');
    },
    onError: (error: unknown) => {
      toast({ title: 'Error', description: getErrorMessage(error, 'Failed to create cap table'), variant: 'destructive' });
    }
  });

  const createRoundMutation = useMutation({
    mutationFn: async (data: any) => {
      const res = await apiRequest('POST', `/api/companies/${selectedCompany?.id}/fundraising/rounds`, data);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/companies', selectedCompany?.id, 'fundraising/rounds'] });
      toast({ title: 'Round Created', description: 'Your fundraising round has been created.' });
      setShowRoundDialog(false);
      setNewRound({ name: '', target_raise: '', pre_money: '', instrument: 'equity', option_pool_refresh_percent: '' });
    },
    onError: (error: unknown) => {
      toast({ title: 'Error', description: getErrorMessage(error, 'Failed to create round'), variant: 'destructive' });
    }
  });

  const simulateMutation = useMutation({
    mutationFn: async (data: any) => {
      const res = await apiRequest('POST', `/api/companies/${selectedCompany?.id}/fundraising/simulate`, data);
      return res.json();
    },
    onSuccess: (data: any) => {
      toast({ title: 'Simulation Complete', description: 'View your dilution analysis below.' });
      setSimulationResults(data);
    },
    onError: (error: unknown) => {
      toast({ title: 'Error', description: getErrorMessage(error, 'Simulation failed'), variant: 'destructive' });
    }
  });

  const [simulationResults, setSimulationResults] = useState<any>(null);

  const capTables = capTablesData?.cap_tables || [];
  const rounds = roundsData?.rounds || [];
  const board = usePipelineBoard(selectedCompany?.id);

  if (!selectedCompany) {
    return (
      <div className="p-6 flex items-center justify-center h-[60vh]">
        <Card className="max-w-md">
          <CardContent className="pt-6 text-center">
            <Building2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Company Selected</h3>
            <p className="text-muted-foreground">Please select a company to manage fundraising.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const handleCreateRound = () => {
    trackEvent('fundraising_round_created', {});
    createRoundMutation.mutate({
      name: newRound.name,
      target_raise: newRound.target_raise ? parseFloat(newRound.target_raise) : null,
      pre_money: newRound.pre_money ? parseFloat(newRound.pre_money) : null,
      instrument: newRound.instrument,
      option_pool_refresh_percent: newRound.option_pool_refresh_percent
        ? parseFloat(newRound.option_pool_refresh_percent)
        : null,
    });
  };

  const handleSimulate = () => {
    trackEvent('fundraising_simulated', {});
    if (!simulationConfig.cap_table_id) {
      toast({ title: 'Error', description: 'Please select a cap table', variant: 'destructive' });
      return;
    }
    simulateMutation.mutate({
      cap_table_id: simulationConfig.cap_table_id,
      rounds: [{
        instrument: 'equity',
        raise: parseFloat(simulationConfig.raise) || 0,
        pre_money: parseFloat(simulationConfig.pre_money) || 0,
        option_pool_refresh_percent: parseFloat(simulationConfig.option_pool_refresh) || 0,
      }]
    });
  };

  return (
    <PageTransition pageKey="fundraising" className="relative">
      <FloatingOrbsBackground />
    <div className="p-4 md:p-6 space-y-5">
      <CrossPageIntelligence context="fundraising" className="mb-2" testId="fundraising-intelligence" />
      <FadeIn>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <DollarSign className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold" data-testid="text-fundraising-title">Fundraising CRM</h1>
            <p className="text-muted-foreground text-sm">Pipeline, investor database, cap table management & readiness</p>
          </div>
        </div>
      </div>
      </FadeIn>

      <DashboardBanner entries={board.entries} rounds={rounds} currency={selectedCompany?.currency} isLoading={board.isLoading || roundsLoading} />

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="flex-wrap h-auto gap-1" data-testid="fundraising-tabs">
          <TabsTrigger value="pipeline" data-testid="tab-pipeline">
            <Kanban className="h-4 w-4 mr-2" />Pipeline
          </TabsTrigger>
          <TabsTrigger value="investor-db" data-testid="tab-investor-db">
            <Database className="h-4 w-4 mr-2" />Investor Database
          </TabsTrigger>
          <TabsTrigger value="outreach" data-testid="tab-outreach">
            <Mail className="h-4 w-4 mr-2" />Outreach
          </TabsTrigger>
          <TabsTrigger value="cap-table" data-testid="tab-cap-table">
            <PieChart className="h-4 w-4 mr-2" />Cap Table
          </TabsTrigger>
          <TabsTrigger value="rounds" data-testid="tab-rounds">
            <TrendingUp className="h-4 w-4 mr-2" />Rounds
          </TabsTrigger>
          <TabsTrigger value="readiness" data-testid="tab-readiness">
            <Target className="h-4 w-4 mr-2" />Readiness
          </TabsTrigger>
        </TabsList>

        <TabsContent value="pipeline" className="space-y-4" data-testid="tab-content-pipeline">
          <PipelineTab board={board} />
        </TabsContent>

        <TabsContent value="investor-db" className="space-y-4" data-testid="tab-content-investor-db">
          <InvestorDatabaseTab onAdd={(body) => board.add.mutate(body)} />
        </TabsContent>

        <TabsContent value="outreach" className="space-y-4">
          <OutreachTab />
        </TabsContent>

        <TabsContent value="cap-table" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold">Cap Tables</h2>
            <Button onClick={() => setShowCapTableDialog(true)} data-testid="button-create-cap-table">
              <Plus className="h-4 w-4 mr-2" />New Cap Table
            </Button>
          </div>
          {capTablesLoading ? (
            <div className="space-y-3">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-32 w-full" />)}</div>
          ) : capTables.length === 0 ? (
            <EmptyStateCard
              icon={PieChart}
              title="No Cap Tables Yet"
              description="Create your first cap table to track ownership, manage equity, and simulate dilution scenarios."
              action={{ label: "Create Cap Table", onClick: () => setShowCapTableDialog(true), icon: Plus }}
            />
          ) : (
            <StaggerContainer className="space-y-4">
              {capTables.map((ct: CapTable) => (
                <StaggerItem key={ct.id}>
                <Card data-testid={`card-cap-table-${ct.id}`}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle>{ct.name}</CardTitle>
                      <Badge variant="outline">{ct.currency}</Badge>
                    </div>
                    <CardDescription>{ct.as_of_date ? `As of ${ct.as_of_date}` : 'No date specified'}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="mobile-table-scroll">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Holder</TableHead>
                            <TableHead>Type</TableHead>
                            <TableHead className="text-right">Shares</TableHead>
                            <TableHead className="text-right">Ownership %</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {ct.cap_table.common.map((holder, idx) => (
                            <TableRow key={`common-${idx}`}>
                              <TableCell>{holder.holder}</TableCell>
                              <TableCell><Badge variant="outline">Common</Badge></TableCell>
                              <TableCell className="text-right">{holder.shares.toLocaleString()}</TableCell>
                              <TableCell className="text-right">{holder.percent.toFixed(2)}%</TableCell>
                            </TableRow>
                          ))}
                          {ct.cap_table.preferred.map((holder, idx) => (
                            <TableRow key={`preferred-${idx}`}>
                              <TableCell>{holder.holder}</TableCell>
                              <TableCell><Badge>{holder.series}</Badge></TableCell>
                              <TableCell className="text-right">{holder.shares.toLocaleString()}</TableCell>
                              <TableCell className="text-right">{holder.percent.toFixed(2)}%</TableCell>
                            </TableRow>
                          ))}
                          {ct.cap_table.options.pool_percent > 0 && (
                            <TableRow>
                              <TableCell>Option Pool</TableCell>
                              <TableCell><Badge variant="outline">Options</Badge></TableCell>
                              <TableCell className="text-right">{(ct.cap_table.fully_diluted_shares * ct.cap_table.options.pool_percent / 100).toLocaleString()}</TableCell>
                              <TableCell className="text-right">{ct.cap_table.options.pool_percent.toFixed(2)}%</TableCell>
                            </TableRow>
                          )}
                        </TableBody>
                      </Table>
                    </div>
                    <div className="mt-4 text-sm text-muted-foreground">Fully Diluted Shares: {ct.cap_table.fully_diluted_shares.toLocaleString()}</div>
                  </CardContent>
                </Card>
                </StaggerItem>
              ))}
            </StaggerContainer>
          )}
        </TabsContent>

        <TabsContent value="rounds" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold">Fundraising Rounds</h2>
            <Button onClick={() => setShowRoundDialog(true)} data-testid="button-create-round">
              <Plus className="h-4 w-4 mr-2" />New Round
            </Button>
          </div>
          {roundsLoading ? (
            <div className="space-y-3">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-24 w-full" />)}</div>
          ) : rounds.length === 0 ? (
            <EmptyStateCard
              icon={TrendingUp}
              title="No Fundraising Rounds"
              description="Plan your next fundraising round, model different scenarios, and understand dilution impact."
              action={{ label: "Create Round", onClick: () => setShowRoundDialog(true), icon: Plus }}
            />
          ) : (
            <StaggerContainer className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {rounds.map((round: FundraisingRound) => (
                <StaggerItem key={round.id}>
                <Card className="hover-elevate cursor-pointer" data-testid={`card-round-${round.id}`}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">{round.name}</CardTitle>
                      <Badge className={STATUS_COLORS[round.status]}>{round.status}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Target Raise</span>
                        <span className="font-medium">{formatCurrencyFull(round.target_raise || 0)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Pre-Money</span>
                        <span className="font-medium">{formatCurrencyFull(round.pre_money || 0)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Instrument</span>
                        <Badge variant="outline">{round.instrument.toUpperCase()}</Badge>
                      </div>
                      {round.option_pool_refresh_percent && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Pool Refresh</span>
                          <span className="font-medium">{round.option_pool_refresh_percent}%</span>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
                </StaggerItem>
              ))}
            </StaggerContainer>
          )}

          <Card className="mt-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calculator className="h-5 w-5" />Dilution Simulator
              </CardTitle>
              <CardDescription>Model the impact of a fundraising round on ownership</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Cap Table</Label>
                  <Select value={simulationConfig.cap_table_id} onValueChange={(v) => setSimulationConfig({ ...simulationConfig, cap_table_id: v })}>
                    <SelectTrigger data-testid="select-cap-table"><SelectValue placeholder="Select cap table" /></SelectTrigger>
                    <SelectContent>
                      {capTables.map((ct: CapTable) => (
                        <SelectItem key={ct.id} value={ct.id}>{ct.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="fundraising-pre-money-valuation">Pre-Money Valuation</Label>
                  <Input id="fundraising-pre-money-valuation" type="number" placeholder="25000000" value={simulationConfig.pre_money} onChange={(e) => setSimulationConfig({ ...simulationConfig, pre_money: e.target.value })} data-testid="input-pre-money" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="fundraising-raise-amount">Raise Amount</Label>
                  <Input id="fundraising-raise-amount" type="number" placeholder="5000000" value={simulationConfig.raise} onChange={(e) => setSimulationConfig({ ...simulationConfig, raise: e.target.value })} data-testid="input-raise" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="fundraising-option-pool-refresh">Option Pool Refresh (%)</Label>
                  <Input id="fundraising-option-pool-refresh" type="number" placeholder="10" value={simulationConfig.option_pool_refresh} onChange={(e) => setSimulationConfig({ ...simulationConfig, option_pool_refresh: e.target.value })} data-testid="input-pool-refresh" />
                </div>
              </div>
              <Button onClick={handleSimulate} disabled={simulateMutation.isPending} data-testid="button-simulate">
                <Play className="h-4 w-4 mr-2" />{simulateMutation.isPending ? 'Simulating...' : 'Run Simulation'}
              </Button>
              {simulationResults && simulationResults.scenarios?.[0] && (
                <Card className="mt-4 bg-muted/50">
                  <CardHeader><CardTitle className="text-base">Simulation Results</CardTitle></CardHeader>
                  <CardContent>
                    <div className="grid gap-4 md:grid-cols-3">
                      <div>
                        <p className="text-sm text-muted-foreground">Founder Dilution</p>
                        <p className="text-2xl font-bold text-amber-500">{simulationResults.scenarios[0].founder_dilution_percent?.toFixed(1)}%</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">New Investor Ownership</p>
                        <p className="text-2xl font-bold text-blue-500">{simulationResults.scenarios[0].new_investor_ownership_percent?.toFixed(1)}%</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Post-Money Valuation</p>
                        <p className="text-2xl font-bold text-green-500">{formatCurrencyFull(simulationResults.scenarios[0].post_money || 0)}</p>
                      </div>
                    </div>
                    {simulationResults.scenarios[0].warnings?.length > 0 && (
                      <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                        <p className="text-sm font-medium text-amber-500">Warnings</p>
                        {simulationResults.scenarios[0].warnings.map((w: string, i: number) => (
                          <p key={i} className="text-sm text-amber-400">{w}</p>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="readiness" className="space-y-6" data-testid="tab-content-readiness">
          {readinessLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-48 w-full" />
              <Skeleton className="h-64 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          ) : readinessData ? (
            <div className="space-y-6">
              <ReadinessScore data={{
                overall: readinessData.overall ?? 0,
                breakdown: readinessData.breakdown ?? { runway: 0, growth: 0, unit_economics: 0, market_timing: 60, narrative_quality: 0 },
                status: readinessData.status ?? 'not-ready',
              }} />
              <RecommendationsList recommendations={readinessData.recommendations ?? []} />
              {readinessData.raiseWindow && selectedCompany && (
                <RaiseWindow raiseWindow={readinessData.raiseWindow} companyId={selectedCompany.id} />
              )}
            </div>
          ) : (
            <Card>
              <CardContent className="pt-6 text-center text-muted-foreground">
                <Target className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                <h3 className="text-lg font-semibold mb-2">Readiness Score Unavailable</h3>
                <p>Upload financial data and run a Truth Scan to generate your fundraising readiness score.</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      <Dialog open={showCapTableDialog} onOpenChange={setShowCapTableDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Cap Table</DialogTitle>
            <DialogDescription>Create a new cap table for your company.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="fundraising-name">Name</Label>
              <Input id="fundraising-name" value={newCapTableName} onChange={(e) => setNewCapTableName(e.target.value)} placeholder="Current Cap Table" data-testid="input-cap-table-name" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCapTableDialog(false)}>Cancel</Button>
            <Button onClick={() => createCapTableMutation.mutate({ name: newCapTableName })} disabled={createCapTableMutation.isPending} data-testid="button-save-cap-table">Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showRoundDialog} onOpenChange={setShowRoundDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Fundraising Round</DialogTitle>
            <DialogDescription>Set up a new fundraising round.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="fundraising-round-name">Round Name</Label>
              <Input id="fundraising-round-name" value={newRound.name} onChange={(e) => setNewRound({ ...newRound, name: e.target.value })} placeholder="Series A" data-testid="input-round-name" />
            </div>
            <div className="grid gap-4 grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="fundraising-target-raise">Target Raise ($)</Label>
                <Input id="fundraising-target-raise" type="number" value={newRound.target_raise} onChange={(e) => setNewRound({ ...newRound, target_raise: e.target.value })} placeholder="5000000" data-testid="input-round-raise" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="fundraising-pre-money-valuation-2">Pre-Money Valuation ($)</Label>
                <Input id="fundraising-pre-money-valuation-2" type="number" value={newRound.pre_money} onChange={(e) => setNewRound({ ...newRound, pre_money: e.target.value })} placeholder="25000000" data-testid="input-round-pre-money" />
              </div>
            </div>
            <div className="grid gap-4 grid-cols-2">
              <div className="space-y-2">
                <Label>Instrument</Label>
                <Select value={newRound.instrument} onValueChange={(v) => setNewRound({ ...newRound, instrument: v })}>
                  <SelectTrigger data-testid="select-instrument"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="equity">Equity</SelectItem>
                    <SelectItem value="safe">SAFE</SelectItem>
                    <SelectItem value="note">Convertible Note</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="fundraising-option-pool-refresh-2">Option Pool Refresh (%)</Label>
                <Input id="fundraising-option-pool-refresh-2" type="number" value={newRound.option_pool_refresh_percent} onChange={(e) => setNewRound({ ...newRound, option_pool_refresh_percent: e.target.value })} placeholder="10" data-testid="input-round-pool" />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRoundDialog(false)}>Cancel</Button>
            <Button onClick={handleCreateRound} disabled={createRoundMutation.isPending || !newRound.name} data-testid="button-save-round">Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
    </PageTransition>
  );
}
