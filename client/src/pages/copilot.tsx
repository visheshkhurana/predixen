import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { FeedbackButton } from '@/components/FeedbackButton';
import { Send, Sparkles, TrendingUp, TrendingDown, DollarSign, Play } from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useTruthScan, useSimulation, useScenarios } from '@/api/hooks';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  metrics?: string[];
  suggestion?: { label: string; action: string };
}

const SUGGESTED_PROMPTS = [
  { label: 'Extend runway by 6 months', icon: TrendingUp },
  { label: "What's the riskiest assumption?", icon: TrendingDown },
  { label: 'What if fundraise slips 3 months?', icon: DollarSign },
];

export default function CopilotPage() {
  const { currentCompany } = useFounderStore();
  const { data: truthScan, isLoading: truthLoading } = useTruthScan(currentCompany?.id || null);
  const { data: scenarios } = useScenarios(currentCompany?.id || null);
  const latestScenario = scenarios?.[0];
  const { data: simulation } = useSimulation(latestScenario?.id || null);
  
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: "I'm your AI financial advisor. I can help you understand your metrics, explore scenarios, and make data-driven decisions. What would you like to know?",
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  
  const confidence = truthScan?.data_confidence_score || 0;
  const qualityOfGrowth = truthScan?.quality_of_growth_index || 0;
  const metrics = truthScan?.metrics || {};
  
  const handleSend = async () => {
    if (!input.trim()) return;
    
    const userMessage: Message = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);
    
    setTimeout(() => {
      const response = generateResponse(input, metrics, confidence);
      setMessages((prev) => [...prev, response]);
      setIsTyping(false);
    }, 1500);
  };
  
  const generateResponse = (query: string, metrics: any, confidence: number): Message => {
    const lowerQuery = query.toLowerCase();
    
    if (lowerQuery.includes('runway') || lowerQuery.includes('extend')) {
      return {
        role: 'assistant',
        content: `Based on your current metrics, your runway is ${metrics.runway_months?.value?.toFixed(1) || 16.5} months (P50). To extend by 6 months, I recommend:\n\n1. **Reduce burn by 15%** - This alone could add 3-4 months\n2. **Implement 10% price increase** - With your strong NRR of ${metrics.net_revenue_retention?.value || 108}%, churn risk is minimal\n3. **Defer non-critical hires** - Push Q2 hires to Q3\n\nWould you like me to run a simulation with these changes?`,
        metrics: ['runway_months', 'net_burn', 'net_revenue_retention'],
        suggestion: { label: 'Run burn cut scenario', action: 'burn_cut_15' },
      };
    }
    
    if (lowerQuery.includes('risk') || lowerQuery.includes('assumption')) {
      return {
        role: 'assistant',
        content: `Your riskiest assumption is **revenue concentration**. Your top 5 customers represent ${metrics.concentration_top5?.value || 32}% of revenue.\n\nIf you lose your largest customer, runway drops from ${metrics.runway_months?.value?.toFixed(1) || 16.5} to approximately 11 months.\n\nRecommendation: Prioritize customer diversification and increase logo count before your next fundraise.`,
        metrics: ['concentration_top5', 'customer_count', 'runway_months'],
      };
    }
    
    if (lowerQuery.includes('fundraise') || lowerQuery.includes('slip')) {
      return {
        role: 'assistant',
        content: `If your fundraise slips 3 months:\n\n• Current runway: ${metrics.runway_months?.value?.toFixed(1) || 16.5} months\n• Survival probability at 18m: ${simulation?.survival?.['18m'] || 65}%\n• Post-slip survival: ~52%\n\nMitigation options:\n1. Secure a bridge round now ($500K-750K)\n2. Implement immediate burn reduction (15-20%)\n3. Accelerate revenue with pricing optimization\n\nThe confidence in these projections is ${confidence >= 80 ? 'high' : confidence >= 60 ? 'moderate' : 'low'} based on your data quality.`,
        metrics: ['runway_months', 'survival_18m', 'cash_balance'],
        suggestion: { label: 'Run bridge scenario', action: 'bridge_round' },
      };
    }
    
    return {
      role: 'assistant',
      content: `Based on your current data (confidence: ${confidence}/100):\n\n• Monthly Revenue: $${(metrics.mrr?.value || 45000).toLocaleString()}\n• Gross Margin: ${metrics.gross_margin?.value || 75}%\n• Net Burn: $${(metrics.net_burn?.value || 15000).toLocaleString()}/month\n• Runway: ${metrics.runway_months?.value?.toFixed(1) || 16.5} months\n\nWhat specific aspect would you like to explore? I can run simulations, compare scenarios, or explain any metric.`,
      metrics: ['mrr', 'gross_margin', 'net_burn', 'runway_months'],
    };
  };
  
  const handlePromptClick = (prompt: string) => {
    setInput(prompt);
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
        
        <ScrollArea className="flex-1 pr-4">
          <div className="space-y-4">
            {messages.map((message, i) => (
              <div
                key={i}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg p-4 ${
                    message.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-secondary'
                  }`}
                  data-testid={`message-${message.role}-${i}`}
                >
                  <p className="whitespace-pre-wrap text-sm">{message.content}</p>
                  {message.metrics && message.metrics.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {message.metrics.map((metric) => (
                        <Badge key={metric} variant="outline" className="text-xs">
                          {metric}
                        </Badge>
                      ))}
                    </div>
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
              </div>
            ))}
            {isTyping && (
              <div className="flex justify-start">
                <div className="bg-secondary rounded-lg p-4">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" />
                    <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce delay-100" />
                    <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce delay-200" />
                  </div>
                </div>
              </div>
            )}
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
                data-testid={`button-prompt-${i}`}
              >
                <prompt.icon className="h-4 w-4 mr-1" />
                {prompt.label}
              </Button>
            ))}
          </div>
          
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask about your metrics, scenarios, or decisions..."
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
                <CardTitle className="text-sm">Data Confidence</CardTitle>
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
                <CardTitle className="text-sm">Quality of Growth</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold font-mono" data-testid="text-context-qog">
                  {qualityOfGrowth}/100
                </div>
              </CardContent>
            </Card>
            
            <Card className="overflow-visible">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Current Scenario</CardTitle>
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
                <CardTitle className="text-sm">Latest Simulation</CardTitle>
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
