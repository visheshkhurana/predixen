import { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { FeedbackButton } from '@/components/FeedbackButton';
import { 
  Send, 
  Sparkles, 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Play, 
  Database, 
  BarChart3, 
  Target,
  Bot,
  User,
  ChevronDown,
  AlertTriangle,
  Lightbulb,
  Users,
  Building2,
  HelpCircle,
  Zap,
  Eye,
  FileText,
  Shield,
  Link2,
  Activity
} from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useTruthScan, useSimulation, useScenarios } from '@/api/hooks';
import { apiRequest } from '@/lib/queryClient';
import { useToast } from '@/hooks/use-toast';

type DataSource = 'truth_scan' | 'simulation' | 'scenario' | 'benchmark' | 'cfo_agent' | 'market_agent' | 'strategy_agent';

interface CopilotApiResponse {
  executive_summary: string[];
  company_snapshot: string[];
  financials?: {
    metrics?: Record<string, any>;
    extracted?: Record<string, any>;
    health_score?: number;
  };
  market_and_customers?: {
    icp?: any;
    competitors?: any[];
    benchmarks?: Record<string, any>;
    this_month_targets?: Array<{
      company_name: string;
      industry: string;
      why_now: string;
      outreach_channel: string;
      talking_points: string[];
      priority: string;
    }>;
  };
  strategy_options?: Array<{
    title: string;
    description: string;
    impact: string;
    risk_level: string;
    timeline: string;
  }>;
  recommendations?: Array<{
    action: string;
    priority: string;
    rationale: string;
    expected_impact: string;
  }>;
  assumptions: string[];
  risks: string[];
  next_questions: string[];
  confidence: string;
  ckb_updated: boolean;
  decision_created?: {
    id: string;
    title: string;
    status: string;
  };
  challenge?: {
    mode: string;
    challenges: Array<{
      recommendation: string;
      counterarguments: string[];
      stress_test: Record<string, string>;
      alternative_perspectives: string[];
    }>;
    summary: string;
  };
  investor_analysis?: {
    investor_type: string;
    evaluation_criteria: Record<string, any>;
    company_fit_analysis: {
      strengths: string[];
      gaps: string[];
      score: string;
    };
    recommendation_alignment: Array<{
      action: string;
      investor_perspective: string;
      concerns: string;
    }>;
  };
  citations?: Array<{
    source_id: string;
    label: string;
    kind?: string;
    page?: number;
    url?: string;
    snippet?: string;
  }>;
  highlighted_claims?: Array<{
    text: string;
    source_ids: string[];
    confidence: string;
  }>;
  data_health?: {
    score: number;
    grade: string;
    issues: Array<{
      severity: string;
      code: string;
      message: string;
      suggested_fix: string;
    }>;
  };
  pii_findings?: Array<{
    type: string;
    count: number;
    examples: string[];
    confidence: string;
  }>;
  pii_mode?: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  metrics?: string[];
  dataSources?: DataSource[];
  suggestion?: { label: string; action: string };
  timestamp?: Date;
  structuredResponse?: CopilotApiResponse;
}

const DATA_SOURCE_CONFIG: Record<DataSource, { label: string; icon: typeof Database; className: string }> = {
  truth_scan: { 
    label: 'Truth Scan', 
    icon: Database, 
    className: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' 
  },
  simulation: { 
    label: 'Simulation', 
    icon: BarChart3, 
    className: 'bg-blue-500/20 text-blue-400 border-blue-500/30' 
  },
  scenario: { 
    label: 'Scenario', 
    icon: Target, 
    className: 'bg-purple-500/20 text-purple-400 border-purple-500/30' 
  },
  benchmark: { 
    label: 'Benchmark', 
    icon: TrendingUp, 
    className: 'bg-amber-500/20 text-amber-400 border-amber-500/30' 
  },
  cfo_agent: { 
    label: 'CFO Agent', 
    icon: DollarSign, 
    className: 'bg-green-500/20 text-green-400 border-green-500/30' 
  },
  market_agent: { 
    label: 'Market Agent', 
    icon: Users, 
    className: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' 
  },
  strategy_agent: { 
    label: 'Strategy Agent', 
    icon: Building2, 
    className: 'bg-orange-500/20 text-orange-400 border-orange-500/30' 
  },
};

const SUGGESTED_PROMPTS = [
  { label: 'How can I extend my runway by 6 months?', icon: TrendingUp },
  { label: "What's the riskiest assumption in my financials?", icon: TrendingDown },
  { label: 'What if my fundraise slips by 3 months?', icon: DollarSign },
  { label: 'Who are my top competitors and how do I differentiate?', icon: Users },
  { label: 'What strategic options should I consider for growth?', icon: Lightbulb },
];

function StructuredResponseDisplay({ response, messageIndex, showSources }: { response: CopilotApiResponse; messageIndex: number; showSources?: boolean }) {
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({});
  
  const toggleSection = (section: string) => {
    setOpenSections(prev => ({ ...prev, [section]: !prev[section] }));
  };
  
  return (
    <div className="mt-4 space-y-3">
      {showSources && response.citations && response.citations.length > 0 && (
        <Collapsible open={openSections['citations']} onOpenChange={() => toggleSection('citations')}>
          <CollapsibleTrigger className="flex items-center gap-2 w-full text-left text-sm font-medium hover:text-primary transition-colors" data-testid={`trigger-citations-${messageIndex}`}>
            <ChevronDown className={`h-4 w-4 transition-transform ${openSections['citations'] ? 'rotate-180' : ''}`} />
            <Link2 className="h-4 w-4 text-blue-400" />
            Sources ({response.citations.length})
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 pl-6 space-y-2">
            {response.citations.map((citation, i) => (
              <div key={i} className="p-2 rounded bg-blue-500/5 border border-blue-500/20">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">
                    {citation.kind === 'pdf' ? 'PDF' : citation.kind === 'web' ? 'Web' : 'Analysis'}
                  </Badge>
                  <span className="text-sm font-medium">{citation.label}</span>
                </div>
                {citation.snippet && (
                  <p className="text-xs text-muted-foreground mt-1 italic">"{citation.snippet}"</p>
                )}
                {citation.page && (
                  <p className="text-xs text-muted-foreground mt-1">Page {citation.page}</p>
                )}
                {citation.url && (
                  <a href={citation.url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-400 hover:underline mt-1 block">
                    View source
                  </a>
                )}
              </div>
            ))}
          </CollapsibleContent>
        </Collapsible>
      )}
      {response.company_snapshot && response.company_snapshot.length > 0 && (
        <Collapsible open={openSections['snapshot']} onOpenChange={() => toggleSection('snapshot')}>
          <CollapsibleTrigger className="flex items-center gap-2 w-full text-left text-sm font-medium hover:text-primary transition-colors" data-testid={`trigger-snapshot-${messageIndex}`}>
            <ChevronDown className={`h-4 w-4 transition-transform ${openSections['snapshot'] ? 'rotate-180' : ''}`} />
            <Building2 className="h-4 w-4" />
            Company Snapshot
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 pl-6 space-y-1">
            {response.company_snapshot.map((item, i) => (
              <p key={i} className="text-xs text-muted-foreground">{item}</p>
            ))}
          </CollapsibleContent>
        </Collapsible>
      )}
      
      {response.strategy_options && response.strategy_options.length > 0 && (
        <Collapsible open={openSections['strategy']} onOpenChange={() => toggleSection('strategy')}>
          <CollapsibleTrigger className="flex items-center gap-2 w-full text-left text-sm font-medium hover:text-primary transition-colors" data-testid={`trigger-strategy-${messageIndex}`}>
            <ChevronDown className={`h-4 w-4 transition-transform ${openSections['strategy'] ? 'rotate-180' : ''}`} />
            <Lightbulb className="h-4 w-4" />
            Strategic Options ({response.strategy_options.length})
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 pl-6 space-y-2">
            {response.strategy_options.map((option, i) => (
              <div key={i} className="p-2 rounded bg-card/50 border border-border/30">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{option.title}</span>
                  <Badge variant="outline" className={option.risk_level === 'Low' ? 'text-green-400' : option.risk_level === 'High' ? 'text-red-400' : 'text-yellow-400'}>
                    {option.risk_level} Risk
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-1">{option.description}</p>
                <div className="flex gap-4 mt-2 text-xs">
                  <span>Impact: {option.impact}</span>
                  <span>Timeline: {option.timeline}</span>
                </div>
              </div>
            ))}
          </CollapsibleContent>
        </Collapsible>
      )}
      
      {response.recommendations && response.recommendations.length > 0 && (
        <Collapsible open={openSections['recommendations']} onOpenChange={() => toggleSection('recommendations')}>
          <CollapsibleTrigger className="flex items-center gap-2 w-full text-left text-sm font-medium hover:text-primary transition-colors" data-testid={`trigger-recommendations-${messageIndex}`}>
            <ChevronDown className={`h-4 w-4 transition-transform ${openSections['recommendations'] ? 'rotate-180' : ''}`} />
            <Target className="h-4 w-4" />
            Recommendations ({response.recommendations.length})
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 pl-6 space-y-2">
            {response.recommendations.map((rec, i) => (
              <div key={i} className="p-2 rounded bg-card/50 border border-border/30">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{rec.action}</span>
                  <Badge variant="outline" className={rec.priority === 'High' ? 'text-red-400' : rec.priority === 'Low' ? 'text-green-400' : 'text-yellow-400'}>
                    {rec.priority} Priority
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-1">{rec.rationale}</p>
                <p className="text-xs text-primary mt-1">Expected: {rec.expected_impact}</p>
              </div>
            ))}
          </CollapsibleContent>
        </Collapsible>
      )}
      
      {response.risks && response.risks.length > 0 && (
        <Collapsible open={openSections['risks']} onOpenChange={() => toggleSection('risks')}>
          <CollapsibleTrigger className="flex items-center gap-2 w-full text-left text-sm font-medium hover:text-primary transition-colors" data-testid={`trigger-risks-${messageIndex}`}>
            <ChevronDown className={`h-4 w-4 transition-transform ${openSections['risks'] ? 'rotate-180' : ''}`} />
            <AlertTriangle className="h-4 w-4 text-amber-400" />
            Risks & Considerations ({response.risks.length})
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 pl-6">
            <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
              {response.risks.map((risk, i) => (
                <li key={i}>{risk}</li>
              ))}
            </ul>
          </CollapsibleContent>
        </Collapsible>
      )}
      
      {response.next_questions && response.next_questions.length > 0 && (
        <div className="pt-2 border-t border-border/30">
          <p className="text-xs text-muted-foreground mb-2 flex items-center gap-1">
            <HelpCircle className="h-3 w-3" />
            Suggested follow-ups:
          </p>
          <div className="flex flex-wrap gap-1">
            {response.next_questions.slice(0, 3).map((q, i) => (
              <Badge key={i} variant="outline" className="text-xs cursor-pointer hover:bg-primary/10">
                {q}
              </Badge>
            ))}
          </div>
        </div>
      )}
      
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Badge variant="outline" className={response.confidence === 'High' ? 'text-green-400 border-green-500/30' : response.confidence === 'Low' ? 'text-red-400 border-red-500/30' : 'text-yellow-400 border-yellow-500/30'}>
          {response.confidence} Confidence
        </Badge>
        {response.ckb_updated && (
          <Badge variant="outline" className="text-blue-400 border-blue-500/30">
            Knowledge Base Updated
          </Badge>
        )}
      </div>
    </div>
  );
}

export default function CopilotPage() {
  const { currentCompany, token } = useFounderStore();
  const { toast } = useToast();
  const { data: truthScan, isLoading: truthLoading } = useTruthScan(currentCompany?.id || null);
  const { data: scenarios } = useScenarios(currentCompany?.id || null);
  const latestScenario = scenarios?.[0];
  const { data: simulation } = useSimulation(latestScenario?.id || null);
  
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: "I'm your AI financial advisor powered by a multi-agent system. I can analyze your financials (CFO Agent), research your market (Market Agent), and develop strategy (Strategy Agent). What would you like to explore?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [useApiMode, setUseApiMode] = useState(true);
  
  const [mode, setMode] = useState<'advisor' | 'analyst' | 'pitch'>('advisor');
  const [challengeMode, setChallengeMode] = useState(false);
  const [investorLens, setInvestorLens] = useState<string | null>(null);
  const [createDecision, setCreateDecision] = useState(false);
  const [showSources, setShowSources] = useState(false);
  const [piiMode, setPiiMode] = useState<'off' | 'standard' | 'strict'>('standard');
  const [latestDataHealth, setLatestDataHealth] = useState<CopilotApiResponse['data_health'] | null>(null);
  const [latestPiiFindings, setLatestPiiFindings] = useState<any[] | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  
  const confidence = truthScan?.data_confidence_score || 0;
  const qualityOfGrowth = truthScan?.quality_of_growth_index || 0;
  const metrics = truthScan?.metrics || {};

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);
  
  const sendMessage = async (messageText: string) => {
    if (!messageText.trim() || isTyping || !currentCompany) return;
    
    const userMessage: Message = { 
      role: 'user', 
      content: messageText,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);
    
    if (useApiMode && token) {
      try {
        const response = await apiRequest<CopilotApiResponse>(
          'POST',
          `/companies/${currentCompany.id}/chat`,
          { 
            message: messageText,
            mode,
            challenge_mode: challengeMode,
            investor_lens: investorLens,
            create_decision: createDecision,
            show_sources: showSources,
            privacy: { pii_mode: piiMode }
          }
        );
        
        const dataSources: DataSource[] = [];
        if (response.financials) dataSources.push('cfo_agent');
        if (response.market_and_customers) dataSources.push('market_agent');
        if (response.strategy_options) dataSources.push('strategy_agent');
        
        const summary = Array.isArray(response.executive_summary) 
          ? response.executive_summary.join('\n\n')
          : 'Response received but could not be parsed.';
        
        const assistantMessage: Message = {
          role: 'assistant',
          content: summary || 'No summary available.',
          dataSources,
          timestamp: new Date(),
          structuredResponse: response,
        };
        setMessages((prev) => [...prev, assistantMessage]);
        
        if (response.data_health) {
          setLatestDataHealth(response.data_health);
        }
        
        if (response.pii_findings) {
          setLatestPiiFindings(response.pii_findings);
        }
      } catch (error: any) {
        console.error('Copilot API error:', error);
        toast({
          title: 'Error',
          description: 'Failed to get response from Copilot. Using fallback mode.',
          variant: 'destructive',
        });
        const fallbackResponse = generateResponse(messageText, metrics, confidence);
        setMessages((prev) => [...prev, fallbackResponse]);
      }
    } else {
      setTimeout(() => {
        const response = generateResponse(messageText, metrics, confidence);
        setMessages((prev) => [...prev, response]);
      }, 1500);
    }
    setIsTyping(false);
  };

  const handleSend = () => {
    sendMessage(input);
  };
  
  const generateResponse = (query: string, metrics: any, confidence: number): Message => {
    const lowerQuery = query.toLowerCase();
    
    if (lowerQuery.includes('runway') || lowerQuery.includes('extend')) {
      return {
        role: 'assistant',
        content: `Based on your current metrics, your runway is ${metrics.runway_months?.value?.toFixed(1) || 16.5} months (P50). To extend by 6 months, I recommend:\n\n1. **Reduce burn by 15%** - This alone could add 3-4 months\n2. **Implement 10% price increase** - With your strong NRR of ${metrics.net_revenue_retention?.value || 108}%, churn risk is minimal\n3. **Defer non-critical hires** - Push Q2 hires to Q3\n\nWould you like me to run a simulation with these changes?`,
        metrics: ['runway_months', 'net_burn', 'net_revenue_retention'],
        dataSources: ['truth_scan', 'simulation'],
        suggestion: { label: 'Run burn cut scenario', action: 'burn_cut_15' },
        timestamp: new Date(),
      };
    }
    
    if (lowerQuery.includes('risk') || lowerQuery.includes('assumption')) {
      return {
        role: 'assistant',
        content: `Your riskiest assumption is **revenue concentration**. Your top 5 customers represent ${metrics.concentration_top5?.value || 32}% of revenue.\n\nIf you lose your largest customer, runway drops from ${metrics.runway_months?.value?.toFixed(1) || 16.5} to approximately 11 months.\n\nRecommendation: Prioritize customer diversification and increase logo count before your next fundraise.`,
        metrics: ['concentration_top5', 'customer_count', 'runway_months'],
        dataSources: ['truth_scan', 'benchmark'],
        timestamp: new Date(),
      };
    }
    
    if (lowerQuery.includes('fundraise') || lowerQuery.includes('slip')) {
      return {
        role: 'assistant',
        content: `If your fundraise slips 3 months:\n\n• Current runway: ${metrics.runway_months?.value?.toFixed(1) || 16.5} months\n• Survival probability at 18m: ${simulation?.survival?.['18m'] || 65}%\n• Post-slip survival: ~52%\n\nMitigation options:\n1. Secure a bridge round now ($500K-750K)\n2. Implement immediate burn reduction (15-20%)\n3. Accelerate revenue with pricing optimization\n\nThe confidence in these projections is ${confidence >= 80 ? 'high' : confidence >= 60 ? 'moderate' : 'low'} based on your data quality.`,
        metrics: ['runway_months', 'survival_18m', 'cash_balance'],
        dataSources: ['truth_scan', 'simulation', 'scenario'],
        suggestion: { label: 'Run bridge scenario', action: 'bridge_round' },
        timestamp: new Date(),
      };
    }
    
    return {
      role: 'assistant',
      content: `Based on your current data (confidence: ${confidence}/100):\n\n• Monthly Revenue: $${(metrics.mrr?.value || 45000).toLocaleString()}\n• Gross Margin: ${metrics.gross_margin?.value || 75}%\n• Net Burn: $${(metrics.net_burn?.value || 15000).toLocaleString()}/month\n• Runway: ${metrics.runway_months?.value?.toFixed(1) || 16.5} months\n\nWhat specific aspect would you like to explore? I can run simulations, compare scenarios, or explain any metric.`,
      metrics: ['mrr', 'gross_margin', 'net_burn', 'runway_months'],
      dataSources: ['truth_scan'],
      timestamp: new Date(),
    };
  };
  
  const handlePromptClick = (prompt: string) => {
    sendMessage(prompt);
  };
  
  if (!currentCompany) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">Select a company to use Copilot</p>
          </CardContent>
        </Card>
      </div>
    );
  }
  
  return (
    <div className="h-[calc(100vh-4rem)] flex">
      <div className="flex-1 flex flex-col p-4">
        <div className="mb-4">
          <h1 className="text-2xl font-semibold flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-primary" />
            Copilot
          </h1>
          <p className="text-sm text-muted-foreground">AI-powered financial advisor grounded in your data</p>
        </div>
        
        <ScrollArea className="flex-1 pr-4" ref={scrollAreaRef}>
          <div className="space-y-4 pb-4">
            {messages.map((message, i) => (
              <div
                key={i}
                className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {message.role === 'assistant' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                )}
                <div
                  className={`max-w-[80%] rounded-2xl p-4 ${
                    message.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-secondary'
                  }`}
                  data-testid={`message-${message.role}-${i}`}
                >
                  <p className="whitespace-pre-wrap text-sm">{message.content}</p>
                  
                  {message.dataSources && message.dataSources.length > 0 && (
                    <div className="mt-3 pt-2 border-t border-border/30">
                      <p className="text-xs text-muted-foreground mb-2">Data sources used:</p>
                      <div className="flex flex-wrap gap-1.5">
                        {message.dataSources.map((source) => {
                          const config = DATA_SOURCE_CONFIG[source];
                          const Icon = config.icon;
                          return (
                            <Badge 
                              key={source} 
                              variant="outline" 
                              className={`text-xs ${config.className}`}
                            >
                              <Icon className="h-3 w-3 mr-1" />
                              {config.label}
                            </Badge>
                          );
                        })}
                      </div>
                    </div>
                  )}
                  
                  {message.metrics && message.metrics.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs text-muted-foreground mb-1.5">Referenced metrics:</p>
                      <div className="flex flex-wrap gap-1">
                        {message.metrics.map((metric) => (
                          <Badge 
                            key={metric} 
                            variant="outline" 
                            className="text-xs font-mono"
                          >
                            {metric.replace(/_/g, ' ')}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {message.structuredResponse && (
                    <StructuredResponseDisplay response={message.structuredResponse} messageIndex={i} showSources={showSources} />
                  )}
                  
                  {message.suggestion && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="mt-3"
                      data-testid={`button-suggestion-${i}`}
                    >
                      <Play className="h-3 w-3 mr-1" />
                      {message.suggestion.label}
                    </Button>
                  )}
                  
                  {message.role === 'assistant' && i > 0 && (
                    <div className="mt-3 pt-2 border-t border-border/50">
                      <FeedbackButton testId={`feedback-${i}`} />
                    </div>
                  )}
                </div>
                {message.role === 'user' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                    <User className="h-4 w-4 text-primary-foreground" />
                  </div>
                )}
              </div>
            ))}
            {isTyping && (
              <div className="flex gap-3 justify-start">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                  <Bot className="h-4 w-4 text-primary" />
                </div>
                <div className="bg-secondary rounded-2xl p-4">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>
        
        <div className="mt-4 space-y-3">
          <div className="flex flex-wrap gap-2">
            {SUGGESTED_PROMPTS.map((prompt, i) => (
              <Button
                key={i}
                variant="outline"
                size="sm"
                onClick={() => handlePromptClick(prompt.label)}
                disabled={isTyping}
                className="whitespace-normal text-left h-auto py-2"
                data-testid={`button-prompt-${i}`}
              >
                <prompt.icon className="h-4 w-4 mr-2 flex-shrink-0" />
                <span>{prompt.label}</span>
              </Button>
            ))}
          </div>
          
          <div className="flex flex-wrap items-center gap-4 p-3 rounded-lg bg-secondary/50 border border-border/30">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Mode:</span>
              <Select value={mode} onValueChange={(v) => setMode(v as 'advisor' | 'analyst' | 'pitch')}>
                <SelectTrigger className="w-24 h-7 text-xs" data-testid="select-mode">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="advisor">Advisor</SelectItem>
                  <SelectItem value="analyst">Analyst</SelectItem>
                  <SelectItem value="pitch">Pitch</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Investor Lens:</span>
              <Select value={investorLens || 'none'} onValueChange={(v) => setInvestorLens(v === 'none' ? null : v)}>
                <SelectTrigger className="w-28 h-7 text-xs" data-testid="select-investor-lens">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None</SelectItem>
                  <SelectItem value="seed">Seed</SelectItem>
                  <SelectItem value="series_a">Series A</SelectItem>
                  <SelectItem value="series_b">Series B</SelectItem>
                  <SelectItem value="pe">PE</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="flex items-center gap-1.5">
              <Switch 
                id="challenge-mode" 
                checked={challengeMode} 
                onCheckedChange={setChallengeMode}
                data-testid="switch-challenge-mode"
              />
              <label htmlFor="challenge-mode" className="text-xs flex items-center gap-1 cursor-pointer">
                <Shield className="h-3 w-3" />
                Challenge
              </label>
            </div>
            
            <div className="flex items-center gap-1.5">
              <Switch 
                id="create-decision" 
                checked={createDecision} 
                onCheckedChange={setCreateDecision}
                data-testid="switch-create-decision"
              />
              <label htmlFor="create-decision" className="text-xs flex items-center gap-1 cursor-pointer">
                <FileText className="h-3 w-3" />
                Track Decision
              </label>
            </div>
            
            <div className="flex items-center gap-1.5">
              <Switch 
                id="show-sources" 
                checked={showSources} 
                onCheckedChange={setShowSources}
                data-testid="switch-show-sources"
              />
              <label htmlFor="show-sources" className="text-xs flex items-center gap-1 cursor-pointer">
                <Link2 className="h-3 w-3" />
                Show Sources
              </label>
            </div>
            
            <div className="flex items-center gap-1.5">
              <label className="text-xs flex items-center gap-1">
                <Shield className="h-3 w-3" />
                Privacy:
              </label>
              <Select value={piiMode} onValueChange={(v: 'off' | 'standard' | 'strict') => setPiiMode(v)} data-testid="select-pii-mode">
                <SelectTrigger className="h-7 w-24 text-xs" data-testid="select-pii-mode-trigger">
                  <SelectValue placeholder="Mode" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="off">Off</SelectItem>
                  <SelectItem value="standard">Standard</SelectItem>
                  <SelectItem value="strict">Strict</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask about your metrics, scenarios, or decisions..."
              disabled={isTyping}
              data-testid="input-copilot"
            />
            <Button onClick={handleSend} disabled={!input.trim() || isTyping} data-testid="button-send">
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
      
      <div className="w-80 border-l p-4 hidden lg:block">
        <h2 className="text-lg font-medium mb-4">Context</h2>
        
        {truthLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : (
          <div className="space-y-4">
            <Card className="overflow-visible">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Database className="h-4 w-4 text-emerald-400" />
                  Data Confidence
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold font-mono" data-testid="text-context-confidence">
                  {confidence}/100
                </div>
                <Badge
                  variant={confidence < 60 ? 'destructive' : 'secondary'}
                  className={confidence >= 80 ? 'bg-emerald-500/20 text-emerald-400' : confidence >= 60 ? 'bg-amber-500/20 text-amber-400' : ''}
                >
                  {confidence < 60 ? 'Low' : confidence < 80 ? 'Medium' : 'High'}
                </Badge>
              </CardContent>
            </Card>
            
            <Card className="overflow-visible">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-amber-400" />
                  Quality of Growth
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold font-mono" data-testid="text-context-qog">
                  {qualityOfGrowth}/100
                </div>
              </CardContent>
            </Card>
            
            {latestDataHealth && (
              <Card className="overflow-visible">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Activity className="h-4 w-4 text-blue-400" />
                    Data Health
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2">
                    <div className="text-2xl font-bold font-mono" data-testid="text-data-health-score">
                      {latestDataHealth.score}
                    </div>
                    <Badge
                      className={
                        latestDataHealth.grade === 'A' ? 'bg-emerald-500/20 text-emerald-400' :
                        latestDataHealth.grade === 'B' ? 'bg-blue-500/20 text-blue-400' :
                        latestDataHealth.grade === 'C' ? 'bg-amber-500/20 text-amber-400' :
                        latestDataHealth.grade === 'D' ? 'bg-orange-500/20 text-orange-400' :
                        'bg-red-500/20 text-red-400'
                      }
                      data-testid="text-data-health-grade"
                    >
                      Grade {latestDataHealth.grade}
                    </Badge>
                  </div>
                  {latestDataHealth.issues && latestDataHealth.issues.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {latestDataHealth.issues.slice(0, 2).map((issue, idx) => (
                        <div key={idx} className="text-xs text-muted-foreground flex items-start gap-1">
                          <AlertTriangle className={`h-3 w-3 mt-0.5 ${issue.severity === 'error' ? 'text-red-400' : issue.severity === 'warning' ? 'text-amber-400' : 'text-blue-400'}`} />
                          {issue.message}
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
            
            <Card className="overflow-visible">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Target className="h-4 w-4 text-purple-400" />
                  Current Scenario
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                {latestScenario ? (
                  <>
                    <p className="font-medium text-foreground">{latestScenario.name}</p>
                    <p>Pricing: {latestScenario.pricing_change_pct > 0 ? '+' : ''}{latestScenario.pricing_change_pct}%</p>
                    <p>Burn cut: {latestScenario.burn_reduction_pct}%</p>
                  </>
                ) : (
                  <p>No scenario selected</p>
                )}
              </CardContent>
            </Card>
            
            <Card className="overflow-visible">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <BarChart3 className="h-4 w-4 text-blue-400" />
                  Latest Simulation
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm">
                {simulation ? (
                  <>
                    <p>Runway P50: <span className="font-mono font-medium">{simulation.runway?.p50?.toFixed(1)} mo</span></p>
                    <p>Survival 18m: <span className="font-mono font-medium">{simulation.survival?.['18m']}%</span></p>
                  </>
                ) : (
                  <p className="text-muted-foreground">No simulation run yet</p>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
