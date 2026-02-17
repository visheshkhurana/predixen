import { useState, useMemo, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { AnnotatedSlider } from '@/components/AnnotatedSlider';
import { AICopilotGuidance } from '@/components/AICopilotGuidance';
import { ScenarioTutorial, TutorialTrigger } from '@/components/ScenarioTutorial';
import { ScenarioSummarySidebar } from '@/components/ScenarioSummarySidebar';
import { CustomEventBuilder, type ScenarioEvent } from '@/components/CustomEventBuilder';
import { ScenarioTagManager } from '@/components/ScenarioTagManager';
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
  TrendingDown,
  Briefcase,
  Rocket,
  Target,
  AlertTriangle,
  Lightbulb,
  Calendar,
  Percent,
  ArrowRight,
  AlertCircle,
  Tag,
  Scissors,
  Users,
  UserPlus,
  Zap,
  Shield,
  Flame,
} from 'lucide-react';

interface ScenarioTemplate {
  id?: string;
  name: string;
  description: string;
  tags: string[];
  deltas: Partial<ScenarioParams>;
  baselineDiff?: string;
}

interface ScenarioParams {
  name: string;
  pricing_change_pct: number;
  growth_uplift_pct: number;
  burn_reduction_pct: number;
  gross_margin_delta_pct: number;
  churn_change_pct: number;
  cac_change_pct: number;
  fundraise_month: number | null;
  fundraise_amount: number;
  tags: string[];
  template_id?: string;
  baseline_diff?: string;
}

interface ScenarioWizardProps {
  templates: ScenarioTemplate[];
  onComplete: (scenario: ScenarioParams) => Promise<void>;
  isRunning: boolean;
  companyId?: number;
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
  { id: 4, title: 'Events', icon: Zap, description: 'Add scenario events' },
  { id: 5, title: 'Review', icon: Rocket, description: 'Confirm and run' },
];

const ALL_TAGS = ['baseline', 'growth', 'cost-cutting', 'pricing', 'fundraising', 'risk'];

const SCENARIO_PRESETS = [
  {
    id: 'conservative',
    name: 'Conservative',
    icon: Shield,
    description: 'Focus on cost reduction and capital preservation with minimal growth risk.',
    values: {
      pricing_change_pct: 0,
      growth_uplift_pct: 0,
      burn_reduction_pct: 15,
      gross_margin_delta_pct: 0,
      churn_change_pct: 0,
      cac_change_pct: 0,
    },
  },
  {
    id: 'balanced',
    name: 'Balanced',
    icon: Target,
    description: 'Moderate price increases with steady growth expectations and efficiency gains.',
    values: {
      pricing_change_pct: 5,
      growth_uplift_pct: 5,
      burn_reduction_pct: 5,
      gross_margin_delta_pct: 2,
      churn_change_pct: -1,
      cac_change_pct: -5,
    },
  },
  {
    id: 'aggressive',
    name: 'Aggressive',
    icon: Flame,
    description: 'Maximize growth with higher prices and increased investment in acquisition.',
    values: {
      pricing_change_pct: 10,
      growth_uplift_pct: 15,
      burn_reduction_pct: -5,
      gross_margin_delta_pct: 3,
      churn_change_pct: -2,
      cac_change_pct: -10,
    },
  },
];

function generateNarrativeFeedback(params: ScenarioParams, runwayImpact: ReturnType<typeof estimateRunwayImpact>): string {
  const changes: string[] = [];
  
  if (params.pricing_change_pct > 0) {
    changes.push(`increasing prices by ${params.pricing_change_pct}%`);
  } else if (params.pricing_change_pct < 0) {
    changes.push(`reducing prices by ${Math.abs(params.pricing_change_pct)}%`);
  }
  
  if (params.growth_uplift_pct > 0) {
    changes.push(`accelerating growth by ${params.growth_uplift_pct}%`);
  } else if (params.growth_uplift_pct < 0) {
    changes.push(`expecting ${Math.abs(params.growth_uplift_pct)}% slower growth`);
  }
  
  if (params.burn_reduction_pct > 0) {
    changes.push(`cutting costs by ${params.burn_reduction_pct}%`);
  } else if (params.burn_reduction_pct < 0) {
    changes.push(`increasing spending by ${Math.abs(params.burn_reduction_pct)}%`);
  }
  
  if (params.churn_change_pct < 0) {
    changes.push(`improving retention by ${Math.abs(params.churn_change_pct)}%`);
  }
  
  if (params.cac_change_pct < 0) {
    changes.push(`reducing acquisition costs by ${Math.abs(params.cac_change_pct)}%`);
  }
  
  if (params.fundraise_amount > 0 && params.fundraise_month) {
    const amount = params.fundraise_amount >= 1000000 
      ? `$${(params.fundraise_amount / 1000000).toFixed(1)}M` 
      : `$${(params.fundraise_amount / 1000).toFixed(0)}K`;
    changes.push(`raising ${amount} in month ${params.fundraise_month}`);
  } else if (params.fundraise_amount > 0) {
    const amount = params.fundraise_amount >= 1000000 
      ? `$${(params.fundraise_amount / 1000000).toFixed(1)}M` 
      : `$${(params.fundraise_amount / 1000).toFixed(0)}K`;
    changes.push(`planning a ${amount} fundraise (month not yet set)`);
  }
  
  if (changes.length === 0) {
    return "No changes from baseline. Your runway remains unchanged.";
  }
  
  const changeText = changes.length === 1 
    ? changes[0] 
    : changes.slice(0, -1).join(', ') + ' and ' + changes[changes.length - 1];
  
  if (!runwayImpact) {
    return `You're ${changeText}.`;
  }
  
  if (runwayImpact.months >= 999) {
    return `By ${changeText}, you're projected to become profitable.`;
  }
  
  const runwayText = runwayImpact.change > 0 
    ? `your runway extends by ${runwayImpact.change.toFixed(1)} months to ${runwayImpact.months.toFixed(1)} months`
    : runwayImpact.change < 0
    ? `your runway decreases by ${Math.abs(runwayImpact.change).toFixed(1)} months to ${runwayImpact.months.toFixed(1)} months`
    : `your runway stays at ${runwayImpact.months.toFixed(1)} months`;
  
  return `By ${changeText}, ${runwayText}.`;
}

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

    case 'churn_change_pct':
      if (value <= -2) return { text: 'Strong retention improvement', type: 'positive' };
      if (value < 0) return { text: 'Reduced churn', type: 'positive' };
      if (value >= 3) return { text: 'Significant churn risk', type: 'negative' };
      if (value > 0) return { text: 'Higher customer loss', type: 'negative' };
      return { text: 'Current churn rate', type: 'neutral' };

    case 'cac_change_pct':
      if (value <= -15) return { text: 'Highly efficient acquisition', type: 'positive' };
      if (value < 0) return { text: 'More efficient customer acquisition', type: 'positive' };
      if (value >= 10) return { text: 'Acquisition becoming expensive', type: 'negative' };
      if (value > 0) return { text: 'Slightly higher CAC', type: 'neutral' };
      return { text: 'Current CAC', type: 'neutral' };

    default:
      return { text: '', type: 'neutral' };
  }
}

const TUTORIAL_STORAGE_KEY = 'founderconsole_scenario_tutorial_dismissed';

function getValidationWarnings(params: ScenarioParams): { field: string; message: string }[] {
  const warnings: { field: string; message: string }[] = [];
  
  if (params.pricing_change_pct > 25) {
    warnings.push({ field: 'pricing_change_pct', message: 'Price increases above 25% may significantly reduce customer acquisition' });
  }
  if (params.pricing_change_pct < -15) {
    warnings.push({ field: 'pricing_change_pct', message: 'Large discounts may hurt margins without proportional growth' });
  }
  if (params.growth_uplift_pct > 15) {
    warnings.push({ field: 'growth_uplift_pct', message: 'Growth above 15% requires substantial investment or viral momentum' });
  }
  if (params.burn_reduction_pct > 30) {
    warnings.push({ field: 'burn_reduction_pct', message: 'Cutting burn by 30%+ may require layoffs or major restructuring' });
  }
  if (params.burn_reduction_pct < -15) {
    warnings.push({ field: 'burn_reduction_pct', message: 'Increasing burn significantly will shorten runway' });
  }
  if (params.fundraise_amount > 0 && !params.fundraise_month) {
    warnings.push({ field: 'fundraise_month', message: 'Set a fundraise month to model when funds arrive' });
  }
  if (params.fundraise_month && params.fundraise_amount <= 0) {
    warnings.push({ field: 'fundraise_amount', message: 'Set an amount to model the fundraise impact' });
  }
  
  return warnings;
}

export function ScenarioWizard({
  templates,
  onComplete,
  isRunning,
  companyId,
  baseMetrics,
}: ScenarioWizardProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [selectedTemplate, setSelectedTemplate] = useState<ScenarioTemplate | null>(null);
  const [showTutorial, setShowTutorial] = useState(false);
  const [activePreset, setActivePreset] = useState<string | null>(null);
  const [activeSlider, setActiveSlider] = useState<{ name: string; previousValue: number } | null>(null);
  const [params, setParams] = useState<ScenarioParams>({
    name: 'Custom Scenario',
    pricing_change_pct: 0,
    growth_uplift_pct: 0,
    burn_reduction_pct: 0,
    gross_margin_delta_pct: 0,
    churn_change_pct: 0,
    cac_change_pct: 0,
    fundraise_month: null,
    fundraise_amount: 0,
    tags: [],
  });
  const [customEvents, setCustomEvents] = useState<ScenarioEvent[]>([]);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const dismissed = localStorage.getItem(TUTORIAL_STORAGE_KEY);
      if (!dismissed) {
        setShowTutorial(true);
      }
    }
  }, []);

  const handleCloseTutorial = () => {
    setShowTutorial(false);
  };

  const handleNeverShowTutorial = () => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(TUTORIAL_STORAGE_KEY, 'true');
    }
    setShowTutorial(false);
  };

  const runwayImpact = useMemo(() => estimateRunwayImpact(params, baseMetrics), [params, baseMetrics]);
  const validationWarnings = useMemo(() => getValidationWarnings(params), [params]);
  const narrativeFeedback = useMemo(() => generateNarrativeFeedback(params, runwayImpact), [params, runwayImpact]);
  
  const handlePresetSelect = (presetId: string) => {
    const preset = SCENARIO_PRESETS.find(p => p.id === presetId);
    if (preset) {
      setActivePreset(presetId);
      setParams(prev => ({
        ...prev,
        ...preset.values,
        name: `${preset.name} Scenario`,
      }));
    }
  };

  const canProceed = useMemo(() => {
    switch (currentStep) {
      case 1:
        return true;
      case 2:
        return true;
      case 3:
        return true;
      case 4:
        return true;
      case 5:
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
      churn_change_pct: template.deltas.churn_change_pct ?? 0,
      cac_change_pct: template.deltas.cac_change_pct ?? 0,
      fundraise_month: template.deltas.fundraise_month ?? null,
      fundraise_amount: template.deltas.fundraise_amount ?? 0,
      tags: template.tags,
      template_id: template.id,
      baseline_diff: template.baselineDiff,
    });
    // Auto-advance to step 2 after template selection
    setTimeout(() => setCurrentStep(2), 150);
  };

  const handleNext = () => {
    if (currentStep < 5) {
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
    <>
      {showTutorial && (
        <ScenarioTutorial
          currentStep={currentStep}
          onClose={handleCloseTutorial}
          onNeverShowAgain={handleNeverShowTutorial}
        />
      )}
      
      {/* Prominent skip tutorial banner */}
      {showTutorial && (
        <Card className="mb-4 border-primary/20 bg-primary/5">
          <CardContent className="py-3">
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-2">
                <Lightbulb className="h-4 w-4 text-primary" />
                <span className="text-sm">
                  <span className="font-medium">Tutorial mode active</span>
                  <span className="text-muted-foreground ml-1.5">— Follow along or skip if you're familiar</span>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={handleCloseTutorial}
                  data-testid="button-dismiss-tutorial"
                >
                  Dismiss
                </Button>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={handleNeverShowTutorial}
                  data-testid="button-skip-tutorial"
                >
                  Skip tutorial forever
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
      
      <div className="flex gap-6">
        <div className="flex-1 space-y-6">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center flex-1" role="navigation" aria-label="Scenario Builder Steps">
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
            <TutorialTrigger onClick={() => setShowTutorial(true)} />
          </div>

          {validationWarnings.length > 0 && currentStep >= 2 && (
            <Card className="border-amber-500/50 bg-amber-500/5">
              <CardContent className="py-3">
                <div className="flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
                  <div className="space-y-1">
                    {validationWarnings.map((warning, i) => (
                      <p key={i} className="text-sm text-amber-700 dark:text-amber-400">
                        {warning.message}
                      </p>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

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

              {/* Preset Buttons */}
              <div className="space-y-3">
                <Label className="text-sm text-muted-foreground" id="preset-group-label">Quick Start Presets</Label>
                <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-labelledby="preset-group-label">
                  {SCENARIO_PRESETS.map((preset) => {
                    const PresetIcon = preset.icon;
                    return (
                      <button
                        key={preset.id}
                        onClick={() => handlePresetSelect(preset.id)}
                        role="radio"
                        aria-checked={activePreset === preset.id}
                        aria-label={`${preset.name} preset: ${preset.description}`}
                        className={cn(
                          'p-3 rounded-lg border text-left transition-all hover-elevate',
                          activePreset === preset.id
                            ? 'border-primary bg-primary/10'
                            : 'border-border'
                        )}
                        data-testid={`preset-${preset.id}`}
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <PresetIcon className="h-4 w-4 text-primary" />
                          <span className="font-medium text-sm">{preset.name}</span>
                        </div>
                        <p className="text-xs text-muted-foreground line-clamp-2">
                          {preset.description}
                        </p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Narrative Feedback Banner */}
              <div className="bg-muted/50 rounded-lg p-4 border border-border">
                <div className="flex items-start gap-3">
                  <Lightbulb className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                  <div>
                    <p className="text-sm font-medium mb-1">What This Means</p>
                    <p className="text-sm text-muted-foreground">
                      {narrativeFeedback}
                    </p>
                  </div>
                </div>
              </div>

              <Separator />

              <div className="space-y-8">
                <div className="space-y-2">
                  <AnnotatedSlider
                    label="Pricing Change"
                    icon={<Tag className="h-4 w-4 text-green-500" />}
                    value={params.pricing_change_pct}
                    onChange={(v) => { 
                      if (!activeSlider || activeSlider.name !== 'pricing_change_pct') {
                        setActiveSlider({ name: 'pricing_change_pct', previousValue: params.pricing_change_pct });
                      }
                      setActivePreset(null); 
                      setParams({ ...params, pricing_change_pct: v }); 
                    }}
                    min={-20}
                    max={30}
                    tooltip={SCENARIO_SLIDER_TOOLTIPS.pricing_change_pct?.description}
                    example={SCENARIO_SLIDER_TOOLTIPS.pricing_change_pct?.example}
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
                    icon={<TrendingUp className="h-4 w-4 text-green-500" />}
                    value={params.growth_uplift_pct}
                    onChange={(v) => { 
                      if (!activeSlider || activeSlider.name !== 'growth_uplift_pct') {
                        setActiveSlider({ name: 'growth_uplift_pct', previousValue: params.growth_uplift_pct });
                      }
                      setActivePreset(null); 
                      setParams({ ...params, growth_uplift_pct: v }); 
                    }}
                    min={-10}
                    max={20}
                    tooltip={SCENARIO_SLIDER_TOOLTIPS.growth_uplift_pct?.description}
                    example={SCENARIO_SLIDER_TOOLTIPS.growth_uplift_pct?.example}
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
                    icon={<Scissors className="h-4 w-4 text-orange-500" />}
                    value={params.burn_reduction_pct}
                    onChange={(v) => { 
                      if (!activeSlider || activeSlider.name !== 'burn_reduction_pct') {
                        setActiveSlider({ name: 'burn_reduction_pct', previousValue: params.burn_reduction_pct });
                      }
                      setActivePreset(null); 
                      setParams({ ...params, burn_reduction_pct: v }); 
                    }}
                    min={-20}
                    max={40}
                    tooltip={SCENARIO_SLIDER_TOOLTIPS.burn_reduction_pct?.description}
                    example={SCENARIO_SLIDER_TOOLTIPS.burn_reduction_pct?.example}
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
                    icon={<Percent className="h-4 w-4 text-blue-500" />}
                    value={params.gross_margin_delta_pct}
                    onChange={(v) => { 
                      if (!activeSlider || activeSlider.name !== 'gross_margin_delta_pct') {
                        setActiveSlider({ name: 'gross_margin_delta_pct', previousValue: params.gross_margin_delta_pct });
                      }
                      setActivePreset(null); 
                      setParams({ ...params, gross_margin_delta_pct: v }); 
                    }}
                    min={-10}
                    max={20}
                    tooltip={SCENARIO_SLIDER_TOOLTIPS.gross_margin_delta_pct?.description}
                    example={SCENARIO_SLIDER_TOOLTIPS.gross_margin_delta_pct?.example}
                    markers={SCENARIO_SLIDER_TOOLTIPS.gross_margin_delta_pct?.markers || []}
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

                <div className="space-y-2">
                  <AnnotatedSlider
                    label="Churn Rate Change"
                    icon={<Users className="h-4 w-4 text-red-500" />}
                    value={params.churn_change_pct}
                    onChange={(v) => { 
                      if (!activeSlider || activeSlider.name !== 'churn_change_pct') {
                        setActiveSlider({ name: 'churn_change_pct', previousValue: params.churn_change_pct });
                      }
                      setActivePreset(null); 
                      setParams({ ...params, churn_change_pct: v }); 
                    }}
                    min={-5}
                    max={5}
                    step={0.5}
                    tooltip={SCENARIO_SLIDER_TOOLTIPS.churn_change_pct?.description}
                    example={SCENARIO_SLIDER_TOOLTIPS.churn_change_pct?.example}
                    markers={SCENARIO_SLIDER_TOOLTIPS.churn_change_pct?.markers || []}
                    testId="slider-churn"
                  />
                  <div className="flex items-center gap-1.5 mt-1">
                    <Info className="h-3 w-3 text-muted-foreground" />
                    <span className={cn(
                      'text-xs',
                      getSliderFeedback('churn_change_pct', params.churn_change_pct).type === 'positive' && 'text-green-600 dark:text-green-400',
                      getSliderFeedback('churn_change_pct', params.churn_change_pct).type === 'negative' && 'text-red-600 dark:text-red-400'
                    )}>
                      {getSliderFeedback('churn_change_pct', params.churn_change_pct).text}
                    </span>
                  </div>
                </div>

                <div className="space-y-2">
                  <AnnotatedSlider
                    label="CAC Change"
                    icon={<UserPlus className="h-4 w-4 text-purple-500" />}
                    value={params.cac_change_pct}
                    onChange={(v) => { 
                      if (!activeSlider || activeSlider.name !== 'cac_change_pct') {
                        setActiveSlider({ name: 'cac_change_pct', previousValue: params.cac_change_pct });
                      }
                      setActivePreset(null); 
                      setParams({ ...params, cac_change_pct: v }); 
                    }}
                    min={-30}
                    max={20}
                    tooltip={SCENARIO_SLIDER_TOOLTIPS.cac_change_pct?.description}
                    example={SCENARIO_SLIDER_TOOLTIPS.cac_change_pct?.example}
                    markers={SCENARIO_SLIDER_TOOLTIPS.cac_change_pct?.markers || []}
                    testId="slider-cac"
                  />
                  <div className="flex items-center gap-1.5 mt-1">
                    <Info className="h-3 w-3 text-muted-foreground" />
                    <span className={cn(
                      'text-xs',
                      getSliderFeedback('cac_change_pct', params.cac_change_pct).type === 'positive' && 'text-green-600 dark:text-green-400',
                      getSliderFeedback('cac_change_pct', params.cac_change_pct).type === 'negative' && 'text-red-600 dark:text-red-400'
                    )}>
                      {getSliderFeedback('cac_change_pct', params.cac_change_pct).text}
                    </span>
                  </div>
                </div>
                
                {companyId && activeSlider && (
                  <div className="mt-6 pt-6 border-t">
                    <AICopilotGuidance
                      companyId={companyId}
                      assumption={activeSlider.name}
                      value={params[activeSlider.name as keyof ScenarioParams] as number}
                      previousValue={activeSlider.previousValue}
                      testId="ai-copilot-guidance-params"
                    />
                  </div>
                )}
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
                <h2 className="text-xl font-semibold">Scenario Events</h2>
                <p className="text-muted-foreground text-sm mt-1">
                  Add probabilistic events to model uncertainty
                </p>
              </div>
              
              <CustomEventBuilder
                events={customEvents}
                onChange={setCustomEvents}
              />
              
              {customEvents.length === 0 && (
                <div className="text-center py-6 text-muted-foreground text-sm">
                  No custom events added yet. Click "Add Event" above to model specific scenarios like fundraising, hiring changes, or pricing adjustments with probability distributions.
                </div>
              )}
            </div>
          )}

          {currentStep === 5 && (
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
                  <ScenarioTagManager
                    tags={params.tags}
                    onChange={(newTags) => setParams({ ...params, tags: newTags })}
                  />
                </div>

                <div className="bg-muted/50 rounded-lg p-4 space-y-3">
                  <h3 className="font-medium text-sm flex items-center gap-2">
                    <Target className="h-4 w-4" />
                    Scenario Summary
                  </h3>
                  
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="flex items-center gap-2">
                      <Tag className="h-4 w-4 text-green-500" />
                      <div>
                        <span className="text-muted-foreground text-xs">Pricing</span>
                        <p className="font-mono font-medium">
                          {params.pricing_change_pct > 0 ? '+' : ''}{params.pricing_change_pct}%
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-green-500" />
                      <div>
                        <span className="text-muted-foreground text-xs">Growth</span>
                        <p className="font-mono font-medium">
                          {params.growth_uplift_pct > 0 ? '+' : ''}{params.growth_uplift_pct}%
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Scissors className="h-4 w-4 text-orange-500" />
                      <div>
                        <span className="text-muted-foreground text-xs">Burn</span>
                        <p className="font-mono font-medium">
                          {params.burn_reduction_pct > 0 ? '+' : ''}{params.burn_reduction_pct}%
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Percent className="h-4 w-4 text-blue-500" />
                      <div>
                        <span className="text-muted-foreground text-xs">Margin</span>
                        <p className="font-mono font-medium">
                          {params.gross_margin_delta_pct > 0 ? '+' : ''}{params.gross_margin_delta_pct}%
                        </p>
                      </div>
                    </div>
                    {params.churn_change_pct !== 0 && (
                      <div className="flex items-center gap-2">
                        <Users className="h-4 w-4 text-red-500" />
                        <div>
                          <span className="text-muted-foreground text-xs">Churn</span>
                          <p className="font-mono font-medium">
                            {params.churn_change_pct > 0 ? '+' : ''}{params.churn_change_pct}%
                          </p>
                        </div>
                      </div>
                    )}
                    {params.cac_change_pct !== 0 && (
                      <div className="flex items-center gap-2">
                        <UserPlus className="h-4 w-4 text-purple-500" />
                        <div>
                          <span className="text-muted-foreground text-xs">CAC</span>
                          <p className="font-mono font-medium">
                            {params.cac_change_pct > 0 ? '+' : ''}{params.cac_change_pct}%
                          </p>
                        </div>
                      </div>
                    )}
                    {params.fundraise_month && params.fundraise_amount > 0 && (
                      <>
                        <div className="flex items-center gap-2">
                          <Calendar className="h-4 w-4 text-primary" />
                          <div>
                            <span className="text-muted-foreground text-xs">Fundraise Month</span>
                            <p className="font-mono font-medium">{params.fundraise_month}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <DollarSign className="h-4 w-4 text-primary" />
                          <div>
                            <span className="text-muted-foreground text-xs">Fundraise Amount</span>
                            <p className="font-mono font-medium">{formatCurrency(params.fundraise_amount)}</p>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                  
                  {customEvents.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-border">
                      <div className="flex items-center gap-2 mb-2">
                        <Zap className="h-4 w-4 text-amber-500" />
                        <span className="text-sm font-medium">Custom Events ({customEvents.length})</span>
                      </div>
                      <div className="space-y-1">
                        {customEvents.map((event) => (
                          <div key={event.id} className="text-xs text-muted-foreground flex items-center gap-2">
                            <span className="capitalize">{event.event_type.replace(/_/g, ' ')}</span>
                            <span>-</span>
                            <span>Month {event.start_month}</span>
                            <span>-</span>
                            <span>{event.probability}% chance</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Narrative summary */}
                <div className="bg-primary/5 rounded-lg p-4 border border-primary/20">
                  <div className="flex items-start gap-3">
                    <Lightbulb className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                    <p className="text-sm">{narrativeFeedback}</p>
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

          <div className="flex items-center gap-2">
            {currentStep === 4 && customEvents.length === 0 && (
              <Button 
                variant="ghost" 
                onClick={handleNext}
                className="text-muted-foreground"
                data-testid="button-skip-events"
              >
                Skip
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            )}
            {currentStep < 5 ? (
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
          </div>
        </CardFooter>
        </Card>
      </div>

      <div className="hidden lg:block w-72 flex-shrink-0">
        <ScenarioSummarySidebar params={params} baseMetrics={baseMetrics} />
      </div>
    </div>
    </>
  );
}
