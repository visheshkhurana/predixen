import { useState, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { AnnotatedSlider } from '@/components/AnnotatedSlider';
import { SCENARIO_SLIDER_TOOLTIPS } from '@/lib/metricDefinitions';
import { cn } from '@/lib/utils';
import {
  ChevronLeft,
  ChevronRight,
  Play,
  Check,
  Info,
  Sparkles,
  DollarSign,
  TrendingUp,
  Briefcase,
  Rocket,
  Target,
  AlertTriangle,
  Lightbulb,
  Calendar,
  Percent,
  ArrowRight,
} from 'lucide-react';

interface ScenarioTemplate {
  name: string;
  description: string;
  tags: string[];
  deltas: Partial<ScenarioParams>;
}

interface ScenarioParams {
  name: string;
  pricing_change_pct: number;
  growth_uplift_pct: number;
  burn_reduction_pct: number;
  gross_margin_delta_pct: number;
  fundraise_month: number | null;
  fundraise_amount: number;
  tags: string[];
}

interface ScenarioWizardProps {
  templates: ScenarioTemplate[];
  onComplete: (scenario: ScenarioParams) => Promise<void>;
  isRunning: boolean;
  baseMetrics?: {
    cashOnHand: number;
    monthlyExpenses: number;
    monthlyRevenue: number;
    currentRunway: number;
    growthRate: number;
  };
}

const STEPS = [
  { id: 1, title: 'Template', icon: Lightbulb, description: 'Choose a starting point' },
  { id: 2, title: 'Parameters', icon: Target, description: 'Adjust financial levers' },
  { id: 3, title: 'Fundraising', icon: DollarSign, description: 'Model funding rounds' },
  { id: 4, title: 'Review', icon: Rocket, description: 'Confirm and run' },
];

const ALL_TAGS = ['baseline', 'growth', 'cost-cutting', 'pricing', 'fundraising', 'risk'];

function estimateRunwayImpact(
  params: ScenarioParams,
  baseMetrics?: ScenarioWizardProps['baseMetrics']
): { months: number; change: number; direction: 'positive' | 'negative' | 'neutral' } | null {
  if (!baseMetrics) return null;

  const burnReduction = baseMetrics.monthlyExpenses * (params.burn_reduction_pct / 100);
  const adjustedExpenses = baseMetrics.monthlyExpenses - burnReduction;

  const adjustedCash = baseMetrics.cashOnHand + params.fundraise_amount;

  const pricingImpact = baseMetrics.monthlyRevenue * (params.pricing_change_pct / 100);
  const growthImpact = baseMetrics.monthlyRevenue * (params.growth_uplift_pct / 100) * 0.5;
  const adjustedRevenue = baseMetrics.monthlyRevenue + pricingImpact + growthImpact;
  
  const netBurn = adjustedExpenses - adjustedRevenue;

  if (netBurn <= 0) {
    return { months: 999, change: 999 - baseMetrics.currentRunway, direction: 'positive' };
  }

  const newRunway = adjustedCash / netBurn;
  const change = newRunway - baseMetrics.currentRunway;

  return {
    months: Math.round(newRunway * 10) / 10,
    change: Math.round(change * 10) / 10,
    direction: change > 0.5 ? 'positive' : change < -0.5 ? 'negative' : 'neutral',
  };
}

function getSliderFeedback(
  param: keyof ScenarioParams,
  value: number
): { text: string; type: 'positive' | 'negative' | 'neutral' } {
  switch (param) {
    case 'pricing_change_pct':
      if (value > 10) return { text: 'Significant increase may slow acquisition', type: 'neutral' };
      if (value > 0) return { text: 'Improves unit economics', type: 'positive' };
      if (value < -5) return { text: 'May accelerate growth but reduce margins', type: 'neutral' };
      return { text: 'No change', type: 'neutral' };

    case 'growth_uplift_pct':
      if (value >= 15) return { text: 'Aggressive target requiring significant investment', type: 'neutral' };
      if (value > 5) return { text: 'Healthy growth acceleration', type: 'positive' };
      if (value < -5) return { text: 'Conservative/declining scenario', type: 'negative' };
      return { text: 'Steady state growth', type: 'neutral' };

    case 'burn_reduction_pct':
      if (value >= 25) return { text: 'Extends runway significantly but may impact team', type: 'neutral' };
      if (value > 10) return { text: 'Meaningful cost savings', type: 'positive' };
      if (value < 0) return { text: 'Increased spending on growth', type: 'neutral' };
      return { text: 'No change', type: 'neutral' };

    case 'gross_margin_delta_pct':
      if (value >= 10) return { text: 'Major efficiency improvement', type: 'positive' };
      if (value > 0) return { text: 'Better unit economics', type: 'positive' };
      if (value < 0) return { text: 'Declining margins', type: 'negative' };
      return { text: 'No change', type: 'neutral' };

    default:
      return { text: '', type: 'neutral' };
  }
}

export function ScenarioWizard({
  templates,
  onComplete,
  isRunning,
  baseMetrics,
}: ScenarioWizardProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [selectedTemplate, setSelectedTemplate] = useState<ScenarioTemplate | null>(null);
  const [params, setParams] = useState<ScenarioParams>({
    name: 'Custom Scenario',
    pricing_change_pct: 0,
    growth_uplift_pct: 0,
    burn_reduction_pct: 0,
    gross_margin_delta_pct: 0,
    fundraise_month: null,
    fundraise_amount: 0,
    tags: [],
  });

  const runwayImpact = useMemo(() => estimateRunwayImpact(params, baseMetrics), [params, baseMetrics]);

  const canProceed = useMemo(() => {
    switch (currentStep) {
      case 1:
        return true;
      case 2:
        return true;
      case 3:
        return true;
      case 4:
        return params.name.trim().length > 0;
      default:
        return false;
    }
  }, [currentStep, params]);

  const handleTemplateSelect = (template: ScenarioTemplate) => {
    setSelectedTemplate(template);
    setParams({
      ...params,
      name: template.name,
      pricing_change_pct: template.deltas.pricing_change_pct ?? 0,
      growth_uplift_pct: template.deltas.growth_uplift_pct ?? 0,
      burn_reduction_pct: template.deltas.burn_reduction_pct ?? 0,
      gross_margin_delta_pct: template.deltas.gross_margin_delta_pct ?? 0,
      fundraise_month: template.deltas.fundraise_month ?? null,
      fundraise_amount: template.deltas.fundraise_amount ?? 0,
      tags: template.tags,
    });
  };

  const handleNext = () => {
    if (currentStep < 4) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = () => {
    onComplete(params);
  };

  const formatCurrency = (value: number) => {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
    return `$${value}`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between" role="navigation" aria-label="Scenario Builder Steps">
        {STEPS.map((step, index) => (
          <div key={step.id} className="flex items-center flex-1">
            <button
              onClick={() => setCurrentStep(step.id)}
              className={cn(
                'flex items-center gap-3 p-3 rounded-lg transition-colors w-full',
                currentStep === step.id
                  ? 'bg-primary/10 text-primary'
                  : currentStep > step.id
                  ? 'text-muted-foreground'
                  : 'text-muted-foreground/50'
              )}
              aria-current={currentStep === step.id ? 'step' : undefined}
              aria-label={`Step ${step.id}: ${step.title}`}
              data-testid={`wizard-step-${step.id}`}
            >
              <div
                className={cn(
                  'flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium',
                  currentStep === step.id
                    ? 'bg-primary text-primary-foreground'
                    : currentStep > step.id
                    ? 'bg-primary/20 text-primary'
                    : 'bg-muted text-muted-foreground'
                )}
              >
                {currentStep > step.id ? (
                  <Check className="h-4 w-4" />
                ) : (
                  step.id
                )}
              </div>
              <div className="hidden md:block text-left">
                <p className="text-sm font-medium">{step.title}</p>
                <p className="text-xs text-muted-foreground">{step.description}</p>
              </div>
            </button>
            {index < STEPS.length - 1 && (
              <ArrowRight className="h-4 w-4 text-muted-foreground/30 mx-2 flex-shrink-0 hidden sm:block" />
            )}
          </div>
        ))}
      </div>

      {runwayImpact && currentStep >= 2 && (
        <Card className={cn(
          'border-l-4',
          runwayImpact.direction === 'positive' && 'border-l-green-500',
          runwayImpact.direction === 'negative' && 'border-l-red-500',
          runwayImpact.direction === 'neutral' && 'border-l-muted-foreground'
        )}>
          <CardContent className="py-3">
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium">Projected Impact</span>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">Estimated Runway</p>
                  <p className="text-lg font-mono font-semibold">
                    {runwayImpact.months >= 999 ? 'Profitable' : `${runwayImpact.months} months`}
                  </p>
                </div>
                {runwayImpact.months < 999 && runwayImpact.change !== 0 && (
                  <Badge
                    variant={runwayImpact.direction === 'positive' ? 'default' : runwayImpact.direction === 'negative' ? 'destructive' : 'secondary'}
                  >
                    {runwayImpact.change > 0 ? '+' : ''}{runwayImpact.change} mo
                  </Badge>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Card className="overflow-visible">
        <CardContent className="pt-6">
          {currentStep === 1 && (
            <div className="space-y-4">
              <div className="text-center mb-6">
                <h2 className="text-xl font-semibold">Choose a Starting Template</h2>
                <p className="text-muted-foreground text-sm mt-1">
                  Select a template or skip to create from scratch
                </p>
              </div>

              <ScrollArea className="h-[400px] pr-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {templates.map((template) => (
                    <button
                      key={template.name}
                      onClick={() => handleTemplateSelect(template)}
                      className={cn(
                        'p-4 rounded-lg border text-left transition-all hover-elevate',
                        selectedTemplate?.name === template.name
                          ? 'border-primary bg-primary/5'
                          : 'border-border'
                      )}
                      aria-pressed={selectedTemplate?.name === template.name}
                      data-testid={`template-${template.name.toLowerCase().replace(/\s/g, '-')}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{template.name}</span>
                            {selectedTemplate?.name === template.name && (
                              <Check className="h-4 w-4 text-primary" />
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground mt-1">
                            {template.description}
                          </p>
                        </div>
                      </div>
                      <div className="flex gap-1 mt-3 flex-wrap">
                        {template.tags.map((tag) => (
                          <Badge key={tag} variant="outline" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </button>
                  ))}
                </div>
              </ScrollArea>
            </div>
          )}

          {currentStep === 2 && (
            <div className="space-y-6">
              <div className="text-center mb-6">
                <h2 className="text-xl font-semibold">Adjust Financial Parameters</h2>
                <p className="text-muted-foreground text-sm mt-1">
                  Fine-tune the levers that affect your runway
                </p>
              </div>

              <div className="space-y-8">
                <div className="space-y-2">
                  <AnnotatedSlider
                    label="Pricing Change"
                    value={params.pricing_change_pct}
                    onChange={(v) => setParams({ ...params, pricing_change_pct: v })}
                    min={-20}
                    max={30}
                    tooltip={SCENARIO_SLIDER_TOOLTIPS.pricing_change_pct?.description}
                    markers={SCENARIO_SLIDER_TOOLTIPS.pricing_change_pct?.markers || []}
                    testId="slider-pricing"
                  />
                  <div className="flex items-center gap-1.5 mt-1">
                    <Info className="h-3 w-3 text-muted-foreground" />
                    <span className={cn(
                      'text-xs',
                      getSliderFeedback('pricing_change_pct', params.pricing_change_pct).type === 'positive' && 'text-green-600 dark:text-green-400',
                      getSliderFeedback('pricing_change_pct', params.pricing_change_pct).type === 'negative' && 'text-red-600 dark:text-red-400'
                    )}>
                      {getSliderFeedback('pricing_change_pct', params.pricing_change_pct).text}
                    </span>
                  </div>
                </div>

                <div className="space-y-2">
                  <AnnotatedSlider
                    label="Growth Uplift"
                    value={params.growth_uplift_pct}
                    onChange={(v) => setParams({ ...params, growth_uplift_pct: v })}
                    min={-10}
                    max={20}
                    tooltip={SCENARIO_SLIDER_TOOLTIPS.growth_uplift_pct?.description}
                    markers={SCENARIO_SLIDER_TOOLTIPS.growth_uplift_pct?.markers || []}
                    testId="slider-growth"
                  />
                  <div className="flex items-center gap-1.5 mt-1">
                    <Info className="h-3 w-3 text-muted-foreground" />
                    <span className={cn(
                      'text-xs',
                      getSliderFeedback('growth_uplift_pct', params.growth_uplift_pct).type === 'positive' && 'text-green-600 dark:text-green-400',
                      getSliderFeedback('growth_uplift_pct', params.growth_uplift_pct).type === 'negative' && 'text-red-600 dark:text-red-400'
                    )}>
                      {getSliderFeedback('growth_uplift_pct', params.growth_uplift_pct).text}
                    </span>
                  </div>
                </div>

                <div className="space-y-2">
                  <AnnotatedSlider
                    label="Burn Reduction"
                    value={params.burn_reduction_pct}
                    onChange={(v) => setParams({ ...params, burn_reduction_pct: v })}
                    min={-20}
                    max={40}
                    tooltip={SCENARIO_SLIDER_TOOLTIPS.burn_reduction_pct?.description}
                    markers={SCENARIO_SLIDER_TOOLTIPS.burn_reduction_pct?.markers || []}
                    testId="slider-burn"
                  />
                  <div className="flex items-center gap-1.5 mt-1">
                    <Info className="h-3 w-3 text-muted-foreground" />
                    <span className={cn(
                      'text-xs',
                      getSliderFeedback('burn_reduction_pct', params.burn_reduction_pct).type === 'positive' && 'text-green-600 dark:text-green-400',
                      getSliderFeedback('burn_reduction_pct', params.burn_reduction_pct).type === 'negative' && 'text-red-600 dark:text-red-400'
                    )}>
                      {getSliderFeedback('burn_reduction_pct', params.burn_reduction_pct).text}
                    </span>
                  </div>
                </div>

                <div className="space-y-2">
                  <AnnotatedSlider
                    label="Gross Margin Change"
                    value={params.gross_margin_delta_pct}
                    onChange={(v) => setParams({ ...params, gross_margin_delta_pct: v })}
                    min={-10}
                    max={20}
                    tooltip="Adjustment to gross margin percentage. Positive values improve profitability per dollar of revenue."
                    markers={[
                      { value: -10, label: '-10%' },
                      { value: 0, label: '0' },
                      { value: 10, label: '+10%' },
                      { value: 20, label: '+20%' },
                    ]}
                    testId="slider-margin"
                  />
                  <div className="flex items-center gap-1.5 mt-1">
                    <Info className="h-3 w-3 text-muted-foreground" />
                    <span className={cn(
                      'text-xs',
                      getSliderFeedback('gross_margin_delta_pct', params.gross_margin_delta_pct).type === 'positive' && 'text-green-600 dark:text-green-400',
                      getSliderFeedback('gross_margin_delta_pct', params.gross_margin_delta_pct).type === 'negative' && 'text-red-600 dark:text-red-400'
                    )}>
                      {getSliderFeedback('gross_margin_delta_pct', params.gross_margin_delta_pct).text}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {currentStep === 3 && (
            <div className="space-y-6">
              <div className="text-center mb-6">
                <h2 className="text-xl font-semibold">Fundraising Setup</h2>
                <p className="text-muted-foreground text-sm mt-1">
                  Model a funding round to extend runway
                </p>
              </div>

              <div className="max-w-md mx-auto space-y-6">
                <div className="space-y-2">
                  <div className="flex items-center gap-1.5">
                    <Label htmlFor="fundraise-month">Fundraise Month</Label>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button type="button" className="inline-flex">
                          <Info className="h-3.5 w-3.5 text-muted-foreground" />
                        </button>
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs">
                        <p className="text-sm">
                          Month in the projection when funding is received (1-24).
                          Leave empty if not planning a fundraise.
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <div className="relative">
                    <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="fundraise-month"
                      type="number"
                      value={params.fundraise_month || ''}
                      onChange={(e) =>
                        setParams({
                          ...params,
                          fundraise_month: e.target.value ? Number(e.target.value) : null,
                        })
                      }
                      min={1}
                      max={24}
                      placeholder="None"
                      className="pl-9"
                      aria-describedby="fundraise-month-desc"
                      data-testid="input-fundraise-month"
                    />
                  </div>
                  <p id="fundraise-month-desc" className="text-xs text-muted-foreground">
                    Leave empty if not planning a fundraise
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center gap-1.5">
                    <Label htmlFor="fundraise-amount">Fundraise Amount ($)</Label>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button type="button" className="inline-flex">
                          <Info className="h-3.5 w-3.5 text-muted-foreground" />
                        </button>
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs">
                        <p className="text-sm">
                          Amount of funding to model. Common rounds: $500K bridge, $1-2M seed, $5-10M Series A.
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <div className="relative">
                    <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="fundraise-amount"
                      type="number"
                      value={params.fundraise_amount || ''}
                      onChange={(e) =>
                        setParams({
                          ...params,
                          fundraise_amount: Number(e.target.value),
                        })
                      }
                      min={0}
                      placeholder="0"
                      className="pl-9 font-mono"
                      data-testid="input-fundraise-amount"
                    />
                  </div>
                </div>

                {params.fundraise_month && params.fundraise_amount > 0 && (
                  <div className="bg-muted/50 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Sparkles className="h-4 w-4 text-primary" />
                      <span className="font-medium text-sm">Funding Preview</span>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {formatCurrency(params.fundraise_amount)} will be added in month {params.fundraise_month}.
                      This models a {params.fundraise_amount >= 5000000 ? 'Series A' : params.fundraise_amount >= 1000000 ? 'Seed' : 'Bridge'} round.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {currentStep === 4 && (
            <div className="space-y-6">
              <div className="text-center mb-6">
                <h2 className="text-xl font-semibold">Review Your Scenario</h2>
                <p className="text-muted-foreground text-sm mt-1">
                  Confirm your settings before running the simulation
                </p>
              </div>

              <div className="max-w-lg mx-auto space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="scenario-name">Scenario Name</Label>
                  <Input
                    id="scenario-name"
                    value={params.name}
                    onChange={(e) => setParams({ ...params, name: e.target.value })}
                    placeholder="My Scenario"
                    data-testid="input-scenario-name"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Tags</Label>
                  <div className="flex gap-1 flex-wrap">
                    {ALL_TAGS.map((tag) => (
                      <Badge
                        key={tag}
                        variant={params.tags.includes(tag) ? 'default' : 'outline'}
                        className="cursor-pointer"
                        onClick={() => {
                          setParams({
                            ...params,
                            tags: params.tags.includes(tag)
                              ? params.tags.filter((t) => t !== tag)
                              : [...params.tags, tag],
                          });
                        }}
                        data-testid={`tag-${tag}`}
                      >
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div className="bg-muted/50 rounded-lg p-4 space-y-3">
                  <h3 className="font-medium text-sm flex items-center gap-2">
                    <Target className="h-4 w-4" />
                    Scenario Summary
                  </h3>
                  
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-muted-foreground">Pricing Change</span>
                      <p className="font-mono font-medium">
                        {params.pricing_change_pct > 0 ? '+' : ''}{params.pricing_change_pct}%
                      </p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Growth Uplift</span>
                      <p className="font-mono font-medium">
                        {params.growth_uplift_pct > 0 ? '+' : ''}{params.growth_uplift_pct}%
                      </p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Burn Reduction</span>
                      <p className="font-mono font-medium">
                        {params.burn_reduction_pct > 0 ? '+' : ''}{params.burn_reduction_pct}%
                      </p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Margin Change</span>
                      <p className="font-mono font-medium">
                        {params.gross_margin_delta_pct > 0 ? '+' : ''}{params.gross_margin_delta_pct}%
                      </p>
                    </div>
                    {params.fundraise_month && params.fundraise_amount > 0 && (
                      <>
                        <div>
                          <span className="text-muted-foreground">Fundraise Month</span>
                          <p className="font-mono font-medium">{params.fundraise_month}</p>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Fundraise Amount</span>
                          <p className="font-mono font-medium">{formatCurrency(params.fundraise_amount)}</p>
                        </div>
                      </>
                    )}
                  </div>
                </div>

                {runwayImpact && (
                  <div className={cn(
                    'rounded-lg p-4 flex items-center justify-between gap-4',
                    runwayImpact.direction === 'positive' && 'bg-green-500/10',
                    runwayImpact.direction === 'negative' && 'bg-red-500/10',
                    runwayImpact.direction === 'neutral' && 'bg-muted/50'
                  )}>
                    <div>
                      <span className="text-sm text-muted-foreground">Projected Runway</span>
                      <p className="text-2xl font-mono font-bold">
                        {runwayImpact.months >= 999 ? 'Profitable' : `${runwayImpact.months} months`}
                      </p>
                    </div>
                    {runwayImpact.months < 999 && runwayImpact.change !== 0 && (
                      <Badge
                        variant={runwayImpact.direction === 'positive' ? 'default' : 'destructive'}
                        className="text-base px-3 py-1"
                      >
                        {runwayImpact.change > 0 ? '+' : ''}{runwayImpact.change} months
                      </Badge>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </CardContent>

        <CardFooter className="flex justify-between gap-4 pt-6 border-t">
          <Button
            variant="outline"
            onClick={handleBack}
            disabled={currentStep === 1}
            data-testid="button-wizard-back"
          >
            <ChevronLeft className="h-4 w-4 mr-2" />
            Back
          </Button>

          {currentStep < 4 ? (
            <Button onClick={handleNext} disabled={!canProceed} data-testid="button-wizard-next">
              Next
              <ChevronRight className="h-4 w-4 ml-2" />
            </Button>
          ) : (
            <Button onClick={handleSubmit} disabled={isRunning || !canProceed} data-testid="button-run-simulation">
              <Play className="h-4 w-4 mr-2" />
              {isRunning ? 'Running Simulation...' : 'Run Simulation (1,000 scenarios)'}
            </Button>
          )}
        </CardFooter>
      </Card>
    </div>
  );
}
