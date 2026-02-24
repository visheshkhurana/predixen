import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { useToast } from '@/hooks/use-toast';
import { useFounderStore } from '@/store/founderStore';
import { apiRequest } from '@/lib/queryClient';
import { 
  FileText, CheckSquare, HelpCircle, BarChart3, 
  Play, Building2, RefreshCw, Copy, Download
} from 'lucide-react';

interface FundraisingRound {
  id: string;
  name: string;
  target_raise: number | null;
  status: string;
}

interface ChecklistItem {
  item: string;
  required: boolean;
  completed: boolean;
}

interface FAQItem {
  question: string;
  suggested_answer: string;
}

interface InvestorRoomData {
  round_id: string;
  round_name: string;
  mode: string;
  investor_memo_markdown: string;
  data_room_checklist: Record<string, ChecklistItem[]>;
  kpi_snapshot: Record<string, any>;
  investor_faq: FAQItem[];
}

interface FundraisingRoundsResponse {
  rounds: FundraisingRound[];
}

export default function InvestorRoomPage() {
  const { currentCompany: selectedCompany } = useFounderStore();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  
  const [activeTab, setActiveTab] = useState('memo');
  const [selectedRoundId, setSelectedRoundId] = useState<string>('');
  const [selectedMode, setSelectedMode] = useState<string>('vc');
  const [investorRoomData, setInvestorRoomData] = useState<InvestorRoomData | null>(null);
  const [checklistState, setChecklistState] = useState<Record<string, Record<string, boolean>>>({});

  const { data: roundsData, isLoading: roundsLoading } = useQuery<FundraisingRoundsResponse>({
    queryKey: ['/api/companies', selectedCompany?.id, 'fundraising/rounds'],
    queryFn: async () => {
      const res = await apiRequest("GET", `/api/companies/${selectedCompany?.id}/fundraising/rounds`);
      return res.json() as Promise<FundraisingRoundsResponse>;
    },
    enabled: !!selectedCompany?.id,
  });

  const generateMutation = useMutation({
    mutationFn: async (data: { round_id: string; mode: string }) => {
      const res = await apiRequest("POST", `/api/companies/${selectedCompany?.id}/investor-room/generate`, data);
      return res.json() as Promise<InvestorRoomData>;
    },
    onSuccess: (data: InvestorRoomData) => {
      setInvestorRoomData(data);
      toast({ title: 'Investor Room Generated', description: 'Your investor materials are ready.' });
      
      const initialState: Record<string, Record<string, boolean>> = {};
      Object.entries(data.data_room_checklist || {}).forEach(([category, items]) => {
        initialState[category] = {};
        (items as ChecklistItem[]).forEach((item) => {
          initialState[category][item.item] = item.completed;
        });
      });
      setChecklistState(initialState);
    },
    onError: (error: Error) => {
      toast({ title: 'Error', description: error.message, variant: 'destructive' });
    }
  });

  const rounds = roundsData?.rounds || [];

  if (!selectedCompany) {
    return (
      <div className="p-6 flex items-center justify-center h-[60vh]">
        <Card className="max-w-md">
          <CardContent className="pt-6 text-center">
            <Building2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Company Selected</h3>
            <p className="text-muted-foreground">Please select a company to access the investor room.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const handleGenerate = () => {
    if (!selectedRoundId) {
      toast({ title: 'Error', description: 'Please select a round', variant: 'destructive' });
      return;
    }
    generateMutation.mutate({ round_id: selectedRoundId, mode: selectedMode });
  };

  const toggleChecklistItem = (category: string, item: string) => {
    setChecklistState((prev) => ({
      ...prev,
      [category]: {
        ...prev[category],
        [item]: !prev[category]?.[item],
      },
    }));
  };

  const copyMemoToClipboard = () => {
    if (investorRoomData?.investor_memo_markdown) {
      navigator.clipboard.writeText(investorRoomData.investor_memo_markdown);
      toast({ title: 'Copied', description: 'Memo copied to clipboard.' });
    }
  };

  const getCategoryCompletionPercent = (category: string): number => {
    const items = investorRoomData?.data_room_checklist?.[category] || [];
    if (items.length === 0) return 0;
    const completed = items.filter((item: ChecklistItem) => checklistState[category]?.[item.item]).length;
    return Math.round((completed / items.length) * 100);
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <FileText className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold" data-testid="text-investor-room-title">Investor Room</h1>
            <p className="text-muted-foreground text-sm">Generate investor materials and manage due diligence</p>
          </div>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Generate Investor Materials</CardTitle>
          <CardDescription>Select a round and investor type to generate materials</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4 items-end">
            <div className="space-y-2 min-w-[200px]">
              <label className="text-sm font-medium">Fundraising Round</label>
              <Select value={selectedRoundId} onValueChange={setSelectedRoundId}>
                <SelectTrigger data-testid="select-round">
                  <SelectValue placeholder="Select round" />
                </SelectTrigger>
                <SelectContent>
                  {roundsLoading ? (
                    <SelectItem value="loading" disabled>Loading...</SelectItem>
                  ) : rounds.length === 0 ? (
                    <SelectItem value="none" disabled>No rounds available</SelectItem>
                  ) : (
                    rounds.map((round: FundraisingRound) => (
                      <SelectItem key={round.id} value={round.id}>
                        {round.name} {round.target_raise ? `($${(round.target_raise/1000000).toFixed(1)}M)` : ''}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2 min-w-[200px]">
              <label className="text-sm font-medium">Investor Type</label>
              <Select value={selectedMode} onValueChange={setSelectedMode}>
                <SelectTrigger data-testid="select-mode">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="vc">Venture Capital</SelectItem>
                  <SelectItem value="growth_pe">Growth PE</SelectItem>
                  <SelectItem value="strategic">Strategic</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button 
              onClick={handleGenerate}
              disabled={generateMutation.isPending || !selectedRoundId}
              data-testid="button-generate"
            >
              {generateMutation.isPending ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              Generate Materials
            </Button>
          </div>
        </CardContent>
      </Card>

      {investorRoomData && (
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList>
            <TabsTrigger value="memo" data-testid="tab-memo">
              <FileText className="h-4 w-4 mr-2" />
              Investor Memo
            </TabsTrigger>
            <TabsTrigger value="checklist" data-testid="tab-checklist">
              <CheckSquare className="h-4 w-4 mr-2" />
              Data Room Checklist
            </TabsTrigger>
            <TabsTrigger value="kpi" data-testid="tab-kpi">
              <BarChart3 className="h-4 w-4 mr-2" />
              KPI Snapshot
            </TabsTrigger>
            <TabsTrigger value="faq" data-testid="tab-faq">
              <HelpCircle className="h-4 w-4 mr-2" />
              Investor FAQ
            </TabsTrigger>
          </TabsList>

          <TabsContent value="memo">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Investor Memo</CardTitle>
                  <Button variant="outline" size="sm" onClick={copyMemoToClipboard}>
                    <Copy className="h-4 w-4 mr-2" />
                    Copy
                  </Button>
                </div>
                <CardDescription>Markdown-formatted investor memo ready for sharing</CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[500px] w-full rounded-md border p-4">
                  <pre className="whitespace-pre-wrap font-mono text-sm">
                    {investorRoomData.investor_memo_markdown}
                  </pre>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="checklist">
            <Card>
              <CardHeader>
                <CardTitle>Data Room Checklist</CardTitle>
                <CardDescription>Track your due diligence document preparation</CardDescription>
              </CardHeader>
              <CardContent>
                <Accordion type="multiple" className="w-full">
                  {Object.entries(investorRoomData.data_room_checklist || {}).map(([category, items]) => (
                    <AccordionItem key={category} value={category}>
                      <AccordionTrigger className="hover:no-underline">
                        <div className="flex items-center justify-between w-full pr-4">
                          <span className="capitalize">{category.replace('_', ' ')}</span>
                          <Badge variant="outline">
                            {getCategoryCompletionPercent(category)}% Complete
                          </Badge>
                        </div>
                      </AccordionTrigger>
                      <AccordionContent>
                        <div className="space-y-2 pl-2">
                          {(items as ChecklistItem[]).map((item, idx) => (
                            <div 
                              key={idx} 
                              className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50"
                            >
                              <Checkbox 
                                checked={checklistState[category]?.[item.item] || false}
                                onCheckedChange={() => toggleChecklistItem(category, item.item)}
                                data-testid={`checkbox-${category}-${idx}`}
                              />
                              <span className={checklistState[category]?.[item.item] ? 'line-through text-muted-foreground' : ''}>
                                {item.item}
                              </span>
                              {item.required && (
                                <Badge variant="destructive" className="text-xs">Required</Badge>
                              )}
                            </div>
                          ))}
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  ))}
                </Accordion>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="kpi">
            <Card>
              <CardHeader>
                <CardTitle>KPI Snapshot</CardTitle>
                <CardDescription>Key metrics for investor presentations</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-3">
                  <Card>
                    <CardContent className="pt-4">
                      <p className="text-sm text-muted-foreground">MRR</p>
                      <p className="text-2xl font-bold">
                        ${(investorRoomData.kpi_snapshot?.mrr || 0).toLocaleString()}
                      </p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <p className="text-sm text-muted-foreground">ARR</p>
                      <p className="text-2xl font-bold">
                        ${(investorRoomData.kpi_snapshot?.arr || 0).toLocaleString()}
                      </p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <p className="text-sm text-muted-foreground">Runway</p>
                      <p className="text-2xl font-bold">
                        {investorRoomData.kpi_snapshot?.runway_months 
                          ? `${investorRoomData.kpi_snapshot.runway_months} months`
                          : 'N/A'}
                      </p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <p className="text-sm text-muted-foreground">Gross Margin</p>
                      <p className="text-2xl font-bold">
                        {investorRoomData.kpi_snapshot?.gross_margin 
                          ? `${investorRoomData.kpi_snapshot.gross_margin.toFixed(1)}%`
                          : 'N/A'}
                      </p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <p className="text-sm text-muted-foreground">Customers</p>
                      <p className="text-2xl font-bold">
                        {investorRoomData.kpi_snapshot?.customers || 'N/A'}
                      </p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <p className="text-sm text-muted-foreground">LTV/CAC</p>
                      <p className="text-2xl font-bold">
                        {investorRoomData.kpi_snapshot?.ltv_cac_ratio 
                          ? `${investorRoomData.kpi_snapshot.ltv_cac_ratio.toFixed(1)}x`
                          : 'N/A'}
                      </p>
                    </CardContent>
                  </Card>
                </div>
                {investorRoomData.kpi_snapshot?.as_of && (
                  <p className="text-sm text-muted-foreground mt-4">
                    As of {new Date(investorRoomData.kpi_snapshot.as_of).toLocaleDateString()}
                  </p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="faq">
            <Card>
              <CardHeader>
                <CardTitle>Investor FAQ</CardTitle>
                <CardDescription>Common investor questions with suggested answers</CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[500px]">
                  <div className="space-y-4">
                    {investorRoomData.investor_faq?.map((faq, idx) => (
                      <Card key={idx} className="bg-muted/30" data-testid={`card-faq-${idx}`}>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-base flex items-center gap-2">
                            <HelpCircle className="h-4 w-4 text-primary" />
                            {faq.question}
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <p className="text-sm text-muted-foreground">{faq.suggested_answer}</p>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}

      {!investorRoomData && !generateMutation.isPending && (
        <Card>
          <CardContent className="py-12 text-center">
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Materials Generated</h3>
            <p className="text-muted-foreground">
              Select a fundraising round and click "Generate Materials" to create your investor room.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
