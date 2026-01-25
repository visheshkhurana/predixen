import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { BookOpen, Search, Info } from 'lucide-react';

interface GlossaryTerm {
  term: string;
  definition: string;
  calculation?: string;
  example?: string;
  category: 'metric' | 'concept' | 'action';
}

const GLOSSARY_TERMS: GlossaryTerm[] = [
  {
    term: 'Runway',
    definition: 'The number of months your company can operate before running out of cash, based on your current burn rate.',
    calculation: 'Runway = Cash Balance / Monthly Burn Rate',
    example: 'If you have $500K in the bank and burn $50K/month, your runway is 10 months.',
    category: 'metric',
  },
  {
    term: 'Survival Probability',
    definition: 'The likelihood that your company will have positive cash at a given point in the future, based on Monte Carlo simulation of various market scenarios.',
    calculation: 'Calculated by running 1,000 simulated scenarios and counting how many result in positive cash.',
    example: 'An 80% survival rate at 18 months means 800 out of 1,000 simulated scenarios showed positive cash at month 18.',
    category: 'metric',
  },
  {
    term: 'P10 / P50 / P90',
    definition: 'Percentile values from Monte Carlo simulations. P50 is the median (most likely outcome), P10 is the pessimistic case (10th percentile), and P90 is the optimistic case (90th percentile).',
    example: 'If P10=8 months, P50=12 months, P90=18 months, there\'s a 50% chance of reaching 12 months runway, and only 10% chance of reaching 18 months.',
    category: 'concept',
  },
  {
    term: 'Burn Rate',
    definition: 'The rate at which your company is spending money. Net burn includes revenue, while gross burn is total expenses before revenue.',
    calculation: 'Net Burn = Monthly Expenses - Monthly Revenue',
    example: 'If you spend $100K/month and earn $40K/month, your net burn is $60K/month.',
    category: 'metric',
  },
  {
    term: 'Burn Reduction',
    definition: 'A percentage decrease in your monthly operating expenses, typically achieved through cost-cutting measures.',
    example: 'A 20% burn reduction on $100K monthly expenses saves $20K/month, adding runway without raising capital.',
    category: 'action',
  },
  {
    term: 'Pricing Change',
    definition: 'Adjusting your product or service pricing. Increases improve unit economics but may affect customer acquisition.',
    example: 'A 10% price increase on $50K MRR adds $5K/month revenue, but may slow growth by 2-3%.',
    category: 'action',
  },
  {
    term: 'Growth Uplift',
    definition: 'An increase in your revenue growth rate compared to baseline projections, typically from improved sales, marketing, or product-market fit.',
    example: 'A 5% growth uplift means growing at 15% instead of 10% monthly, compounding over time.',
    category: 'action',
  },
  {
    term: 'Churn Rate',
    definition: 'The percentage of customers or revenue lost each month. Lower churn means better retention and higher lifetime value.',
    calculation: 'Monthly Churn = Lost Customers / Starting Customers',
    example: 'A 5% monthly churn means losing half your customers every 14 months.',
    category: 'metric',
  },
  {
    term: 'CAC (Customer Acquisition Cost)',
    definition: 'The total cost to acquire a new customer, including marketing, sales, and onboarding expenses.',
    calculation: 'CAC = Total Sales & Marketing Spend / New Customers Acquired',
    example: 'If you spend $10K on marketing and acquire 100 customers, your CAC is $100.',
    category: 'metric',
  },
  {
    term: 'Gross Margin',
    definition: 'The percentage of revenue remaining after subtracting the cost of goods sold (COGS). Higher margins mean more cash from each sale.',
    calculation: 'Gross Margin = (Revenue - COGS) / Revenue × 100%',
    example: 'With $100K revenue and $30K COGS, gross margin is 70%.',
    category: 'metric',
  },
  {
    term: 'Monte Carlo Simulation',
    definition: 'A computational technique that runs thousands of scenarios with randomized inputs to model uncertainty and calculate probability distributions.',
    example: 'Rather than a single forecast, Monte Carlo shows the range of possible outcomes and their likelihoods.',
    category: 'concept',
  },
  {
    term: 'Regime',
    definition: 'A market condition state (Base, Downturn, Breakout) that affects simulation parameters. Different regimes model economic uncertainty.',
    example: 'In a "Downturn" regime, growth slows and churn increases, stress-testing your scenario.',
    category: 'concept',
  },
  {
    term: 'Sensitivity Analysis',
    definition: 'Testing how changes in individual drivers (growth, churn, etc.) impact outcomes like runway, to identify which levers matter most.',
    example: 'If a 5% churn reduction extends runway by 6 months, retention is a high-leverage area to focus on.',
    category: 'concept',
  },
];

interface GlossaryModalProps {
  trigger?: React.ReactNode;
  initialTerm?: string;
}

export function GlossaryModal({ trigger, initialTerm }: GlossaryModalProps) {
  const [searchQuery, setSearchQuery] = useState(initialTerm || '');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  
  const filteredTerms = GLOSSARY_TERMS.filter((item) => {
    const matchesSearch = searchQuery === '' || 
      item.term.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.definition.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = !selectedCategory || item.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });
  
  const categoryColors = {
    metric: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
    concept: 'bg-purple-500/10 text-purple-600 dark:text-purple-400',
    action: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
  };
  
  return (
    <Dialog>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" size="sm" data-testid="button-glossary">
            <BookOpen className="h-4 w-4 mr-2" />
            Glossary
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            Financial Terms Glossary
          </DialogTitle>
          <DialogDescription>
            Definitions and explanations of key metrics and concepts
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search terms..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
                data-testid="input-glossary-search"
              />
            </div>
          </div>
          
          <div className="flex gap-2">
            <Button
              variant={selectedCategory === null ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory(null)}
            >
              All
            </Button>
            <Button
              variant={selectedCategory === 'metric' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory('metric')}
            >
              Metrics
            </Button>
            <Button
              variant={selectedCategory === 'concept' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory('concept')}
            >
              Concepts
            </Button>
            <Button
              variant={selectedCategory === 'action' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory('action')}
            >
              Actions
            </Button>
          </div>
          
          <ScrollArea className="h-[400px] pr-4">
            <div className="space-y-4">
              {filteredTerms.map((item) => (
                <div key={item.term} className="border rounded-lg p-4 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-semibold">{item.term}</h3>
                    <Badge variant="secondary" className={categoryColors[item.category]}>
                      {item.category}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{item.definition}</p>
                  {item.calculation && (
                    <div className="bg-muted/50 rounded p-2">
                      <p className="text-xs font-medium text-muted-foreground mb-1">Formula</p>
                      <code className="text-sm font-mono">{item.calculation}</code>
                    </div>
                  )}
                  {item.example && (
                    <div className="bg-primary/5 rounded p-2">
                      <p className="text-xs font-medium text-primary mb-1">Example</p>
                      <p className="text-sm">{item.example}</p>
                    </div>
                  )}
                </div>
              ))}
              
              {filteredTerms.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  <Info className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No terms found matching your search</p>
                </div>
              )}
            </div>
          </ScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  );
}

interface TermTooltipProps {
  term: string;
  children: React.ReactNode;
}

export function TermTooltip({ term, children }: TermTooltipProps) {
  const glossaryItem = GLOSSARY_TERMS.find(
    (item) => item.term.toLowerCase() === term.toLowerCase()
  );
  
  if (!glossaryItem) {
    return <>{children}</>;
  }
  
  return (
    <span className="group relative inline-flex items-center gap-1 cursor-help border-b border-dashed border-muted-foreground/50">
      {children}
      <Info className="h-3 w-3 text-muted-foreground" />
      <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-popover border rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
        <p className="font-medium text-sm mb-1">{glossaryItem.term}</p>
        <p className="text-xs text-muted-foreground">{glossaryItem.definition}</p>
      </span>
    </span>
  );
}
