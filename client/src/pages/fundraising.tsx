import { useState } from 'react';
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
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { useFounderStore } from '@/store/founderStore';
import { CrossPageIntelligence } from '@/components/CrossPageIntelligence';
import { apiRequest } from '@/lib/queryClient';
import { 
  Plus, DollarSign, Users, TrendingUp, PieChart, 
  Calculator, Play, FileText, Building2, Percent
} from 'lucide-react';
import { EmptyStateCard } from '@/components/ui/empty-state';

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

const STATUS_COLORS: Record<string, string> = {
  planned: 'bg-yellow-500/20 text-yellow-600',
  active: 'bg-blue-500/20 text-blue-600',
  closed: 'bg-green-500/20 text-green-600',
};

export default function FundraisingPage() {
  const { currentCompany: selectedCompany } = useFounderStore();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  
  const [activeTab, setActiveTab] = useState('cap-table');
  const [showCapTableDialog, setShowCapTableDialog] = useState(false);
  const [showRoundDialog, setShowRoundDialog] = useState(false);
  const [showSimulateDialog, setShowSimulateDialog] = useState(false);
  
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
    onError: (error: Error) => {
      toast({ title: 'Error', description: error.message, variant: 'destructive' });
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
    onError: (error: Error) => {
      toast({ title: 'Error', description: error.message, variant: 'destructive' });
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
    onError: (error: Error) => {
      toast({ title: 'Error', description: error.message, variant: 'destructive' });
    }
  });

  const [simulationResults, setSimulationResults] = useState<any>(null);

  const capTables = capTablesData?.cap_tables || [];
  const rounds = roundsData?.rounds || [];

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
    <div className="p-6 space-y-6">
      <CrossPageIntelligence context="fundraising" className="mb-2" testId="fundraising-intelligence" />
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <DollarSign className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold" data-testid="text-fundraising-title">Fundraising</h1>
            <p className="text-muted-foreground text-sm">Manage cap tables, rounds, and model dilution</p>
          </div>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="cap-table" data-testid="tab-cap-table">
            <PieChart className="h-4 w-4 mr-2" />
            Cap Table
          </TabsTrigger>
          <TabsTrigger value="rounds" data-testid="tab-rounds">
            <TrendingUp className="h-4 w-4 mr-2" />
            Rounds
          </TabsTrigger>
          <TabsTrigger value="simulate" data-testid="tab-simulate">
            <Calculator className="h-4 w-4 mr-2" />
            Simulate
          </TabsTrigger>
        </TabsList>

        <TabsContent value="cap-table" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold">Cap Tables</h2>
            <Button onClick={() => setShowCapTableDialog(true)} data-testid="button-create-cap-table">
              <Plus className="h-4 w-4 mr-2" />
              New Cap Table
            </Button>
          </div>

          {capTablesLoading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-32 w-full" />)}
            </div>
          ) : capTables.length === 0 ? (
            <EmptyStateCard
              icon={PieChart}
              title="No Cap Tables Yet"
              description="Create your first cap table to track ownership, manage equity, and simulate dilution scenarios."
              action={{
                label: "Create Cap Table",
                onClick: () => setShowCapTableDialog(true),
                icon: Plus,
              }}
            />
          ) : (
            <div className="space-y-4">
              {capTables.map((ct: CapTable) => (
                <Card key={ct.id} data-testid={`card-cap-table-${ct.id}`}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle>{ct.name}</CardTitle>
                      <Badge variant="outline">{ct.currency}</Badge>
                    </div>
                    <CardDescription>
                      {ct.as_of_date ? `As of ${ct.as_of_date}` : 'No date specified'}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
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
                    <div className="mt-4 text-sm text-muted-foreground">
                      Fully Diluted Shares: {ct.cap_table.fully_diluted_shares.toLocaleString()}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="rounds" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold">Fundraising Rounds</h2>
            <Button onClick={() => setShowRoundDialog(true)} data-testid="button-create-round">
              <Plus className="h-4 w-4 mr-2" />
              New Round
            </Button>
          </div>

          {roundsLoading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-24 w-full" />)}
            </div>
          ) : rounds.length === 0 ? (
            <EmptyStateCard
              icon={TrendingUp}
              title="No Fundraising Rounds"
              description="Plan your next fundraising round, model different scenarios, and understand dilution impact."
              action={{
                label: "Create Round",
                onClick: () => setShowRoundDialog(true),
                icon: Plus,
              }}
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {rounds.map((round: FundraisingRound) => (
                <Card key={round.id} className="hover-elevate cursor-pointer" data-testid={`card-round-${round.id}`}>
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
                        <span className="font-medium">${(round.target_raise || 0).toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Pre-Money</span>
                        <span className="font-medium">${(round.pre_money || 0).toLocaleString()}</span>
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
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="simulate" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calculator className="h-5 w-5" />
                Dilution Simulator
              </CardTitle>
              <CardDescription>Model the impact of a fundraising round on ownership</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Cap Table</Label>
                  <Select 
                    value={simulationConfig.cap_table_id} 
                    onValueChange={(v) => setSimulationConfig({ ...simulationConfig, cap_table_id: v })}
                  >
                    <SelectTrigger data-testid="select-cap-table">
                      <SelectValue placeholder="Select cap table" />
                    </SelectTrigger>
                    <SelectContent>
                      {capTables.map((ct: CapTable) => (
                        <SelectItem key={ct.id} value={ct.id}>{ct.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="space-y-2">
                  <Label>Pre-Money Valuation</Label>
                  <Input 
                    type="number" 
                    placeholder="25000000"
                    value={simulationConfig.pre_money}
                    onChange={(e) => setSimulationConfig({ ...simulationConfig, pre_money: e.target.value })}
                    data-testid="input-pre-money"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label>Raise Amount</Label>
                  <Input 
                    type="number" 
                    placeholder="5000000"
                    value={simulationConfig.raise}
                    onChange={(e) => setSimulationConfig({ ...simulationConfig, raise: e.target.value })}
                    data-testid="input-raise"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label>Option Pool Refresh (%)</Label>
                  <Input 
                    type="number" 
                    placeholder="10"
                    value={simulationConfig.option_pool_refresh}
                    onChange={(e) => setSimulationConfig({ ...simulationConfig, option_pool_refresh: e.target.value })}
                    data-testid="input-pool-refresh"
                  />
                </div>
              </div>

              <Button 
                onClick={handleSimulate} 
                disabled={simulateMutation.isPending}
                data-testid="button-simulate"
              >
                <Play className="h-4 w-4 mr-2" />
                {simulateMutation.isPending ? 'Simulating...' : 'Run Simulation'}
              </Button>

              {simulationResults && simulationResults.scenarios?.[0] && (
                <Card className="mt-4 bg-muted/50">
                  <CardHeader>
                    <CardTitle className="text-base">Simulation Results</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4 md:grid-cols-3">
                      <div>
                        <p className="text-sm text-muted-foreground">Founder Dilution</p>
                        <p className="text-2xl font-bold text-amber-500">
                          {simulationResults.scenarios[0].founder_dilution_percent?.toFixed(1)}%
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">New Investor Ownership</p>
                        <p className="text-2xl font-bold text-blue-500">
                          {simulationResults.scenarios[0].new_investor_ownership_percent?.toFixed(1)}%
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Post-Money Valuation</p>
                        <p className="text-2xl font-bold text-green-500">
                          ${(simulationResults.scenarios[0].post_money || 0).toLocaleString()}
                        </p>
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
      </Tabs>

      <Dialog open={showCapTableDialog} onOpenChange={setShowCapTableDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Cap Table</DialogTitle>
            <DialogDescription>Create a new cap table for your company.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Name</Label>
              <Input 
                value={newCapTableName}
                onChange={(e) => setNewCapTableName(e.target.value)}
                placeholder="Current Cap Table"
                data-testid="input-cap-table-name"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCapTableDialog(false)}>Cancel</Button>
            <Button 
              onClick={() => createCapTableMutation.mutate({ name: newCapTableName })}
              disabled={createCapTableMutation.isPending}
              data-testid="button-save-cap-table"
            >
              Create
            </Button>
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
              <Label>Round Name</Label>
              <Input 
                value={newRound.name}
                onChange={(e) => setNewRound({ ...newRound, name: e.target.value })}
                placeholder="Series A"
                data-testid="input-round-name"
              />
            </div>
            <div className="grid gap-4 grid-cols-2">
              <div className="space-y-2">
                <Label>Target Raise ($)</Label>
                <Input 
                  type="number"
                  value={newRound.target_raise}
                  onChange={(e) => setNewRound({ ...newRound, target_raise: e.target.value })}
                  placeholder="5000000"
                  data-testid="input-round-raise"
                />
              </div>
              <div className="space-y-2">
                <Label>Pre-Money Valuation ($)</Label>
                <Input 
                  type="number"
                  value={newRound.pre_money}
                  onChange={(e) => setNewRound({ ...newRound, pre_money: e.target.value })}
                  placeholder="25000000"
                  data-testid="input-round-pre-money"
                />
              </div>
            </div>
            <div className="grid gap-4 grid-cols-2">
              <div className="space-y-2">
                <Label>Instrument</Label>
                <Select 
                  value={newRound.instrument} 
                  onValueChange={(v) => setNewRound({ ...newRound, instrument: v })}
                >
                  <SelectTrigger data-testid="select-instrument">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="equity">Equity</SelectItem>
                    <SelectItem value="safe">SAFE</SelectItem>
                    <SelectItem value="note">Convertible Note</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Option Pool Refresh (%)</Label>
                <Input 
                  type="number"
                  value={newRound.option_pool_refresh_percent}
                  onChange={(e) => setNewRound({ ...newRound, option_pool_refresh_percent: e.target.value })}
                  placeholder="10"
                  data-testid="input-round-pool"
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRoundDialog(false)}>Cancel</Button>
            <Button 
              onClick={handleCreateRound}
              disabled={createRoundMutation.isPending || !newRound.name}
              data-testid="button-save-round"
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
