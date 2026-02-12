import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Slider } from '@/components/ui/slider';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { 
  TrendingUp, AlertTriangle, Clock, Link2, ChevronDown, ChevronUp, 
  Sparkles, Trophy, Target, Zap, HelpCircle, Play, RefreshCw, 
  Calendar, DollarSign, BarChart3, Check, X, Pause,
  ListChecks, Search, ArrowRight
} from 'lucide-react';
import { cn } from '@/lib/utils';

export type DecisionStatus = 'pending' | 'adopted' | 'deferred' | 'rejected';

interface Assumption {
  key: string;
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string;
}

interface DecisionCardProps {
  id?: string;
  rank: number;
  title: string;
  rationale: string;
  expectedImpact: {
    delta_survival_18m: number;
    delta_runway_p50: number;
  };
  risks: string[];
  keyAssumption: string;
  timeHorizon?: string;
  dependencies?: string[];
  detailedRiskFactors?: string[];
  runwayImpactDetails?: string;
  survivalImpactDetails?: string;
  executionPlaybook?: string[];
  researchInsights?: string[];
  secondOrderEffects?: string[];
  status?: DecisionStatus;
  onStatusChange?: (status: DecisionStatus) => void;
  onAdoptPlan?: () => void;
  onRunScenario?: () => void;
  onRefineAssumptions?: (assumptions: Record<string, number>) => void;
  isNew?: boolean;
  isChanged?: boolean;
  testId?: string;
  maxSurvivalImpact?: number;
  maxRunwayChange?: number;
}

const METRIC_TOOLTIPS = {
  survivalImpact: {
    title: 'Survival Impact (18 months)',
    description: 'Change in probability that your company will maintain positive cash flow over the next 18 months.',
    importance: 'Higher values indicate a safer path forward. Aim for scenarios that improve survival by 5%+ points.',
  },
  runwayChange: {
    title: 'Runway Change',
    description: 'How many additional (or fewer) months of operation this decision provides before running out of cash.',
    importance: 'Positive values extend your time to reach milestones. Negative values require faster execution.',
  },
  risksAssumptions: {
    title: 'Risks & Assumptions',
    description: 'Key factors that must hold true for this recommendation to succeed, and potential downsides.',
    importance: 'Review these carefully. If assumptions don\'t match your situation, the projected impact may differ.',
  },
};

function MetricTooltip({ type, children }: { type: keyof typeof METRIC_TOOLTIPS; children: React.ReactNode }) {
  const tooltip = METRIC_TOOLTIPS[type];
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="inline-flex items-center gap-1 cursor-help">
          {children}
          <HelpCircle className="h-3 w-3 text-muted-foreground opacity-60 hover:opacity-100 transition-opacity" />
        </span>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-xs p-3">
        <div className="space-y-2">
          <p className="font-medium text-sm">{tooltip.title}</p>
          <p className="text-xs text-muted-foreground">{tooltip.description}</p>
          <p className="text-xs text-primary/80">{tooltip.importance}</p>
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

function ImpactBar({ 
  value, 
  maxValue, 
  label,
  isPositive 
}: { 
  value: number; 
  maxValue: number; 
  label: string;
  isPositive: boolean;
}) {
  const absValue = Math.abs(value);
  const percentage = maxValue > 0 ? Math.min(100, (absValue / maxValue) * 100) : 0;
  
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className={cn(
          "font-mono font-semibold",
          isPositive ? "text-emerald-500" : "text-red-500"
        )}>
          {isPositive ? '+' : ''}{value.toFixed(1)}{label.includes('Runway') ? ' mo' : '%'}
        </span>
      </div>
      <div className="h-2.5 bg-secondary rounded-full overflow-hidden">
        <div 
          className={cn(
            "h-full rounded-full transition-all duration-500",
            isPositive ? "bg-emerald-500" : "bg-red-500"
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

function AssumptionSlider({
  assumption,
  onChange,
}: {
  assumption: Assumption;
  onChange: (key: string, value: number) => void;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{assumption.label}</span>
        <span className="font-mono font-medium">
          {assumption.value}{assumption.unit}
        </span>
      </div>
      <Slider
        value={[assumption.value]}
        onValueChange={([val]) => onChange(assumption.key, val)}
        min={assumption.min}
        max={assumption.max}
        step={assumption.step}
        className="h-1"
      />
    </div>
  );
}

export function DecisionCard({
  id,
  rank,
  title,
  rationale,
  expectedImpact,
  risks,
  keyAssumption,
  timeHorizon = '2-4 weeks',
  dependencies = [],
  detailedRiskFactors = [],
  runwayImpactDetails,
  survivalImpactDetails,
  executionPlaybook = [],
  researchInsights = [],
  secondOrderEffects = [],
  status = 'pending',
  onStatusChange,
  onAdoptPlan,
  onRunScenario,
  onRefineAssumptions,
  isNew = false,
  isChanged = false,
  testId = 'decision-card',
  maxSurvivalImpact = 20,
  maxRunwayChange = 12,
}: DecisionCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [assumptions, setAssumptions] = useState<Record<string, number>>({
    growth_rate: 10,
    cost_reduction: 0,
    fundraise_amount: 0,
  });

  const defaultAssumptions: Assumption[] = useMemo(() => {
    const lowerTitle = title.toLowerCase();
    
    if (lowerTitle.includes('fund') || lowerTitle.includes('raise')) {
      return [
        { key: 'fundraise_amount', label: 'Amount Raised', value: assumptions.fundraise_amount ?? 2000000, min: 500000, max: 10000000, step: 250000, unit: '' },
        { key: 'dilution', label: 'Expected Dilution', value: assumptions.dilution ?? 20, min: 5, max: 40, step: 1, unit: '%' },
      ];
    }
    if (lowerTitle.includes('growth') || lowerTitle.includes('revenue')) {
      return [
        { key: 'growth_rate', label: 'Monthly Growth Rate', value: assumptions.growth_rate ?? 10, min: 0, max: 30, step: 1, unit: '%' },
        { key: 'marketing_spend', label: 'Marketing Spend', value: assumptions.marketing_spend ?? 50000, min: 10000, max: 200000, step: 5000, unit: '' },
      ];
    }
    if (lowerTitle.includes('cost') || lowerTitle.includes('cut') || lowerTitle.includes('reduce')) {
      return [
        { key: 'cost_reduction', label: 'Cost Reduction', value: assumptions.cost_reduction ?? 20, min: 5, max: 50, step: 5, unit: '%' },
        { key: 'timeline', label: 'Implementation (weeks)', value: assumptions.timeline ?? 4, min: 1, max: 12, step: 1, unit: ' weeks' },
      ];
    }
    
    return [
      { key: 'growth_rate', label: 'Growth Rate', value: assumptions.growth_rate ?? 10, min: 0, max: 30, step: 1, unit: '%' },
    ];
  }, [title, assumptions]);

  const handleAssumptionChange = (key: string, value: number) => {
    const newAssumptions = { ...assumptions, [key]: value };
    setAssumptions(newAssumptions);
    onRefineAssumptions?.(newAssumptions);
  };

  const getRankStyles = () => {
    switch (rank) {
      case 1:
        return {
          cardClass: 'border-emerald-500/50 bg-gradient-to-br from-emerald-500/5 to-transparent',
          iconBg: 'bg-emerald-500',
          icon: Trophy,
          badgeClass: 'bg-emerald-500 text-white border-emerald-600',
          label: '#1 Recommended',
        };
      case 2:
        return {
          cardClass: 'border-primary/30 bg-gradient-to-br from-primary/5 to-transparent',
          iconBg: 'bg-primary',
          icon: Target,
          badgeClass: 'bg-primary/20 text-primary border-primary/30',
          label: '#2 Alternative',
        };
      case 3:
        return {
          cardClass: 'border-slate-500/30',
          iconBg: 'bg-slate-500',
          icon: Zap,
          badgeClass: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
          label: '#3 Option',
        };
      default:
        return {
          cardClass: '',
          iconBg: 'bg-muted',
          icon: Zap,
          badgeClass: 'bg-muted text-muted-foreground',
          label: `#${rank} Option`,
        };
    }
  };

  const getStatusConfig = () => {
    switch (status) {
      case 'adopted':
        return { icon: Check, class: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', label: 'Adopted' };
      case 'deferred':
        return { icon: Pause, class: 'bg-amber-500/20 text-amber-400 border-amber-500/30', label: 'Deferred' };
      case 'rejected':
        return { icon: X, class: 'bg-red-500/20 text-red-400 border-red-500/30', label: 'Rejected' };
      default:
        return null;
    }
  };

  const rankStyles = getRankStyles();
  const RankIcon = rankStyles.icon;
  const statusConfig = getStatusConfig();
  const allRisks = detailedRiskFactors.length > 0 ? detailedRiskFactors : risks;
  const isRecommended = rank === 1;

  return (
    <Card 
      className={cn(
        "overflow-visible relative transition-all duration-300",
        rankStyles.cardClass,
        isNew && "ring-2 ring-emerald-500/50 shadow-emerald-500/20 shadow-lg",
        isChanged && "ring-2 ring-amber-500/50 shadow-amber-500/20 shadow-lg"
      )} 
      data-testid={testId}
    >
      {(isNew || isChanged) && (
        <div className="absolute -top-2 -right-2 z-10">
          <Badge 
            className={cn(
              "flex items-center gap-1 shadow-md",
              isNew ? "bg-emerald-500 text-white" : "bg-amber-500 text-white"
            )}
          >
            <Sparkles className="h-3 w-3" />
            {isNew ? 'New' : 'Updated'}
          </Badge>
        </div>
      )}
      
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-3">
            <div className={cn(
              "w-10 h-10 rounded-lg flex items-center justify-center",
              rankStyles.iconBg
            )}>
              <RankIcon className="h-5 w-5 text-white" />
            </div>
            <div>
              <Badge className={cn("text-xs font-bold", rankStyles.badgeClass)}>
                {rankStyles.label}
              </Badge>
              {statusConfig && (
                <Badge className={cn("text-xs ml-2", statusConfig.class)}>
                  <statusConfig.icon className="h-3 w-3 mr-1" />
                  {statusConfig.label}
                </Badge>
              )}
            </div>
          </div>
        </div>
        <CardTitle className="text-xl font-bold mt-3 leading-tight">{title}</CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-5">
        <p className="text-sm text-muted-foreground leading-relaxed">{rationale}</p>
        
        <div className="space-y-3 p-4 rounded-xl bg-secondary/50">
          <div className="flex items-center gap-2 text-sm font-medium mb-3">
            <BarChart3 className="h-4 w-4 text-primary" />
            <span>Impact Analysis</span>
          </div>
          
          <MetricTooltip type="survivalImpact">
            <span className="text-xs text-muted-foreground">Survival Impact (18m)</span>
          </MetricTooltip>
          <ImpactBar 
            value={expectedImpact.delta_survival_18m}
            maxValue={maxSurvivalImpact}
            label="Survival Impact"
            isPositive={expectedImpact.delta_survival_18m >= 0}
          />
          
          <div className="pt-2">
            <MetricTooltip type="runwayChange">
              <span className="text-xs text-muted-foreground">Runway Change</span>
            </MetricTooltip>
            <ImpactBar 
              value={expectedImpact.delta_runway_p50}
              maxValue={maxRunwayChange}
              label="Runway Change"
              isPositive={expectedImpact.delta_runway_p50 >= 0}
            />
          </div>
        </div>
        
        {risks.length > 0 && (
          <div className="space-y-2">
            <MetricTooltip type="risksAssumptions">
              <span className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
                <AlertTriangle className="h-3 w-3 text-amber-500" />
                Risks & Assumptions
              </span>
            </MetricTooltip>
            <ul className="text-sm text-muted-foreground space-y-1.5 ml-4">
              {risks.slice(0, 2).map((risk, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-amber-500 mt-0.5">-</span>
                  <span>{risk}</span>
                </li>
              ))}
            </ul>
            <p className="text-xs italic text-muted-foreground/80 pl-4">{keyAssumption}</p>
          </div>
        )}
        
        <div className="flex items-center gap-2 pt-2 flex-wrap border-t border-border pt-4">
          {isRecommended ? (
            <>
              <Button 
                onClick={onAdoptPlan || onRunScenario}
                className="bg-emerald-500 hover:bg-emerald-600 text-white"
                data-testid={`${testId}-adopt-btn`}
              >
                <Play className="h-4 w-4 mr-2" />
                Adopt Plan
              </Button>
              <Button 
                variant="outline"
                onClick={onRunScenario}
                data-testid={`${testId}-run-scenario-btn`}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Run Scenario
              </Button>
            </>
          ) : (
            <>
              <Button 
                variant="secondary"
                onClick={onRunScenario}
                data-testid={`${testId}-run-scenario-btn`}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Run Scenario
              </Button>
              <Button 
                variant="ghost"
                onClick={() => setIsExpanded(true)}
                data-testid={`${testId}-refine-btn`}
              >
                Refine Assumptions
              </Button>
            </>
          )}
          
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => setIsExpanded(!isExpanded)}
            className="ml-auto"
            data-testid={`${testId}-expand`}
          >
            {isExpanded ? (
              <>
                <span className="text-sm mr-2">Hide Details</span>
                <ChevronUp className="h-4 w-4" />
              </>
            ) : (
              <>
                <span className="text-sm mr-2">View Details</span>
                <ChevronDown className="h-4 w-4" />
              </>
            )}
          </Button>
        </div>
        
        {isExpanded && (
          <div className="pt-4 mt-2 border-t border-border space-y-5 animate-in slide-in-from-top-2 duration-200">
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-secondary/50">
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
                  <Clock className="h-4 w-4" />
                  <span className="font-medium">Time Horizon</span>
                </div>
                <p className="text-lg font-semibold">{timeHorizon}</p>
              </div>
              
              <div className="p-4 rounded-xl bg-secondary/50">
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
                  <Link2 className="h-4 w-4" />
                  <span className="font-medium">Dependencies</span>
                </div>
                {dependencies.length > 0 ? (
                  <ul className="text-sm space-y-1">
                    {dependencies.map((dep, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-primary mt-0.5">-</span>
                        <span>{dep}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">No dependencies</p>
                )}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-secondary/30 space-y-4">
              <div className="flex items-center gap-2 text-sm font-medium">
                <TrendingUp className="h-4 w-4 text-primary" />
                <span>Adjust Assumptions</span>
              </div>
              <p className="text-xs text-muted-foreground">
                Modify these values to see how they affect the projected outcome.
              </p>
              <div className="space-y-4">
                {defaultAssumptions.map((assumption) => (
                  <AssumptionSlider
                    key={assumption.key}
                    assumption={assumption}
                    onChange={handleAssumptionChange}
                  />
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3">
              <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20">
                <div className="flex items-center gap-2 text-xs text-emerald-400 mb-2">
                  <TrendingUp className="h-4 w-4" />
                  <span className="font-medium">Runway Impact</span>
                </div>
                <p className="text-sm">
                  {runwayImpactDetails || `Expected to ${expectedImpact.delta_runway_p50 >= 0 ? 'extend' : 'reduce'} runway by ${Math.abs(expectedImpact.delta_runway_p50).toFixed(1)} months at P50 confidence level.`}
                </p>
              </div>
              <div className="p-4 rounded-xl bg-primary/5 border border-primary/20">
                <div className="flex items-center gap-2 text-xs text-primary mb-2">
                  <BarChart3 className="h-4 w-4" />
                  <span className="font-medium">Survival Probability</span>
                </div>
                <p className="text-sm">
                  {survivalImpactDetails || `18-month survival probability ${expectedImpact.delta_survival_18m >= 0 ? 'increases' : 'decreases'} by ${Math.abs(expectedImpact.delta_survival_18m).toFixed(1)} percentage points.`}
                </p>
              </div>
            </div>
            
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                Full Rationale
              </p>
              <p className="text-sm leading-relaxed">{rationale}</p>
            </div>
            
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground flex items-center gap-2">
                <DollarSign className="h-4 w-4" />
                Key Assumption
              </p>
              <p className="text-sm italic bg-amber-500/10 p-3 rounded-lg border border-amber-500/20">{keyAssumption}</p>
            </div>

            {executionPlaybook.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground flex items-center gap-2">
                  <ListChecks className="h-4 w-4 text-primary" />
                  Execution Playbook
                </p>
                <ol className="text-sm space-y-1.5 ml-1">
                  {executionPlaybook.map((step, i) => (
                    <li key={i} className="flex items-start gap-2.5 p-2 rounded-lg bg-primary/5">
                      <span className="text-xs font-bold text-primary bg-primary/10 rounded-full w-5 h-5 flex items-center justify-center flex-shrink-0 mt-0.5">{i + 1}</span>
                      <span>{step}</span>
                    </li>
                  ))}
                </ol>
              </div>
            )}

            {researchInsights.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground flex items-center gap-2">
                  <Search className="h-4 w-4 text-primary" />
                  Research Insights
                </p>
                <ul className="text-sm space-y-1.5">
                  {researchInsights.map((insight, i) => (
                    <li key={i} className="flex items-start gap-2 p-2 rounded-lg bg-secondary/50">
                      <ArrowRight className="h-3 w-3 mt-1 text-primary flex-shrink-0" />
                      <span>{insight}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {secondOrderEffects.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-amber-500" />
                  Second-Order Effects
                </p>
                <ul className="text-sm space-y-1.5">
                  {secondOrderEffects.map((effect, i) => (
                    <li key={i} className="flex items-start gap-2 text-muted-foreground">
                      <span className="text-amber-500 mt-0.5 flex-shrink-0">~</span>
                      <span>{effect}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            <div className="space-y-3">
              <p className="text-xs font-medium text-muted-foreground flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500" />
                All Risk Factors
              </p>
              <ul className="text-sm space-y-2">
                {allRisks.map((risk, i) => (
                  <li key={i} className="flex items-start gap-3 p-2 rounded-lg bg-red-500/5 border border-red-500/10">
                    <AlertTriangle className="h-4 w-4 mt-0.5 text-red-400 flex-shrink-0" />
                    <span>{risk}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="flex items-center gap-2 pt-4 border-t border-border">
              <span className="text-xs text-muted-foreground">Status:</span>
              {onStatusChange && (
                <Select
                  value={status}
                  onValueChange={(value) => onStatusChange(value as DecisionStatus)}
                >
                  <SelectTrigger 
                    className="w-36 h-9" 
                    data-testid={`${testId}-status-select`}
                  >
                    <SelectValue placeholder="Set status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="adopted">Adopted</SelectItem>
                    <SelectItem value="deferred">Deferred</SelectItem>
                    <SelectItem value="rejected">Rejected</SelectItem>
                  </SelectContent>
                </Select>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
