import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  TrendingUp,
  Scissors,
  AlertTriangle,
  Zap,
  Target,
  DollarSign,
  BarChart3,
  MapPin,
  ArrowRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface TemplateCard {
  id: string;
  name: string;
  description: string;
  impact: string;
  keyChanges: string[];
  icon: React.ComponentType<any>;
  color: string;
  deltas: {
    pricing_change_pct?: number;
    growth_uplift_pct?: number;
    burn_reduction_pct?: number;
    gross_margin_delta_pct?: number;
    churn_change_pct?: number;
    cac_change_pct?: number;
  };
}

const TEMPLATE_CARDS: TemplateCard[] = [
  {
    id: 'baseline',
    name: 'Current Trajectory',
    description: 'No changes - see where you\'re headed',
    impact: 'Shows baseline runway and survival probability',
    keyChanges: ['No parameter changes', 'Reference point for comparisons'],
    icon: BarChart3,
    color: 'bg-slate-50 border-slate-200 dark:bg-slate-900 dark:border-slate-800',
    deltas: {
      pricing_change_pct: 0,
      growth_uplift_pct: 0,
      burn_reduction_pct: 0,
      gross_margin_delta_pct: 0,
      churn_change_pct: 0,
      cac_change_pct: 0,
    },
  },
  {
    id: 'aggressive-growth',
    name: 'Aggressive Growth',
    description: 'Maximize market capture and growth',
    impact: 'Accelerates revenue but increases burn',
    keyChanges: [
      'Growth +20% (from sales/marketing investment)',
      'Hiring +10% (engineering and sales team)',
      'Marketing +15% (paid acquisition acceleration)',
    ],
    icon: TrendingUp,
    color: 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800',
    deltas: {
      growth_uplift_pct: 20,
      burn_reduction_pct: -10,
      gross_margin_delta_pct: -2,
      cac_change_pct: 10,
    },
  },
  {
    id: 'cost-optimization',
    name: 'Cost Optimization',
    description: 'Reduce burn and extend runway quickly',
    impact: 'Extends runway by 6-9 months',
    keyChanges: [
      'Burn reduction 25% (discretionary spending cuts)',
      'Hiring freeze (no new hires)',
      'Marketing -15% (focus on organic growth)',
    ],
    icon: Scissors,
    color: 'bg-orange-50 border-orange-200 dark:bg-orange-900/20 dark:border-orange-800',
    deltas: {
      burn_reduction_pct: 25,
      growth_uplift_pct: -5,
      gross_margin_delta_pct: 3,
      cac_change_pct: -10,
    },
  },
  {
    id: 'recession-prep',
    name: 'Recession Prep',
    description: 'Stress test with revenue decline',
    impact: 'Shows survival scenario in downturn',
    keyChanges: [
      'Revenue -15% (customer churn risk)',
      'Burn reduction 30% (immediate cost cuts)',
      'Growth rate -10% (slower new customer acquisition)',
    ],
    icon: AlertTriangle,
    color: 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800',
    deltas: {
      growth_uplift_pct: -10,
      burn_reduction_pct: 30,
      churn_change_pct: 5,
      cac_change_pct: -15,
    },
  },
  {
    id: 'fundraise-scale',
    name: 'Fundraise & Scale',
    description: 'Model growth with new capital injection',
    impact: 'Enables aggressive growth with capital',
    keyChanges: [
      'Cash injection (+$2M capital)',
      'Growth +25% (funded expansion)',
      'Hiring +20% (team scale-up)',
    ],
    icon: Zap,
    color: 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800',
    deltas: {
      growth_uplift_pct: 25,
      burn_reduction_pct: -20,
      gross_margin_delta_pct: 2,
      cac_change_pct: 15,
    },
  },
  {
    id: 'unit-economics',
    name: 'Improve Unit Economics',
    description: 'Enhance margins and reduce customer acquisition cost',
    impact: 'Better profitability path',
    keyChanges: [
      'Churn reduction 30% (improved retention)',
      'Gross margin +10% (pricing power or COGS reduction)',
      'CAC reduction 20% (more efficient acquisition)',
    ],
    icon: Target,
    color: 'bg-purple-50 border-purple-200 dark:bg-purple-900/20 dark:border-purple-800',
    deltas: {
      churn_change_pct: -3,
      gross_margin_delta_pct: 10,
      cac_change_pct: -20,
      pricing_change_pct: 5,
    },
  },
  {
    id: 'bridge-profitability',
    name: 'Bridge to Profitability',
    description: 'Reach cash flow positive in 12-18 months',
    impact: 'Path to sustainable operations',
    keyChanges: [
      'Revenue growth +10% (disciplined acquisition)',
      'Burn reduction 40% (aggressive cost management)',
      'Hiring freeze (no new team members)',
    ],
    icon: DollarSign,
    color: 'bg-emerald-50 border-emerald-200 dark:bg-emerald-900/20 dark:border-emerald-800',
    deltas: {
      growth_uplift_pct: 10,
      burn_reduction_pct: 40,
      gross_margin_delta_pct: 5,
      cac_change_pct: -25,
    },
  },
  {
    id: 'market-expansion',
    name: 'Market Expansion',
    description: 'Enter new markets or verticals',
    impact: 'Significant revenue growth but higher costs',
    keyChanges: [
      'Revenue growth +30% (new market entry)',
      'Marketing +25% (go-to-market for new segment)',
      'COGS +15% (supporting new customers)',
    ],
    icon: MapPin,
    color: 'bg-indigo-50 border-indigo-200 dark:bg-indigo-900/20 dark:border-indigo-800',
    deltas: {
      growth_uplift_pct: 30,
      burn_reduction_pct: -15,
      gross_margin_delta_pct: -8,
      cac_change_pct: 20,
    },
  },
];

interface ScenarioTemplateGalleryProps {
  onSelectTemplate: (template: TemplateCard) => void;
  onSkip: () => void;
}

export function ScenarioTemplateGallery({
  onSelectTemplate,
  onSkip,
}: ScenarioTemplateGalleryProps) {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold">Quick Start with Templates</h2>
        <p className="text-muted-foreground">
          Choose a pre-built scenario based on your strategy, or start from scratch
        </p>
      </div>

      <ScrollArea className="w-full">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pb-4">
          {TEMPLATE_CARDS.map((template) => {
            const Icon = template.icon;
            return (
              <button
                key={template.id}
                onClick={() => onSelectTemplate(template)}
                className={cn(
                  'flex flex-col h-full text-left rounded-lg border-2 p-4 transition-all hover:shadow-lg hover:border-primary',
                  template.color
                )}
              >
                <div className="flex items-start justify-between mb-3">
                  <Icon className="h-6 w-6 text-primary flex-shrink-0" />
                  <ArrowRight className="h-4 w-4 text-muted-foreground/0 group-hover:text-primary/50 transition-colors" />
                </div>

                <div className="flex-1">
                  <h3 className="font-semibold text-sm mb-1">{template.name}</h3>
                  <p className="text-xs text-muted-foreground mb-3 line-clamp-2">
                    {template.description}
                  </p>

                  <div className="space-y-2 mb-4">
                    <p className="text-xs font-medium text-primary">Key Changes:</p>
                    <ul className="space-y-1">
                      {template.keyChanges.slice(0, 2).map((change, idx) => (
                        <li key={idx} className="text-xs text-muted-foreground">
                          • {change}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="pt-3 border-t border-border/50">
                    <p className="text-xs font-medium text-foreground mb-1">Expected Impact:</p>
                    <p className="text-xs text-muted-foreground">{template.impact}</p>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-border/50">
                  <Badge variant="secondary" className="text-xs">
                    Use Template
                  </Badge>
                </div>
              </button>
            );
          })}
        </div>
      </ScrollArea>

      <div className="flex gap-3 justify-center pt-4 border-t">
        <Button variant="outline" onClick={onSkip} className="px-8">
          Build from Scratch
        </Button>
      </div>
    </div>
  );
}

export type { TemplateCard };
export { TEMPLATE_CARDS };
