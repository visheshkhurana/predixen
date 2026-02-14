import { useState, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { 
  Target, 
  AlertTriangle, 
  CheckCircle2, 
  Loader2,
  TrendingUp,
  Info,
  Lightbulb,
  Play,
  BarChart3,
  Rocket,
  Users,
  DollarSign,
  Clock,
  Percent,
  ChevronRight
} from 'lucide-react';
import { Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip } from 'recharts';
import { formatCurrencyAbbrev } from '@/lib/utils';

interface SensitivityDriver {
  driver: string;
  impact_direction: string;
  impact_magnitude: number;
  threshold_value: number | null;
  explanation: string;
  current_value: number;
  target_threshold: number;
  recommended_change: number;
  achievable: boolean;
  gap_contribution: number;
  benchmark_value: number | null;
  benchmark_comparison: string | null;
}

interface GapBreakdown {
  driver: string;
  contribution_pct: number;
  absolute_contribution: number;
}

interface SensitivityResult {
  target_runway_months: number;
  target_probability: number;
  achievable: boolean;
  current_probability: number;
  total_gap: number;
  key_drivers: SensitivityDriver[];
  gap_breakdown: GapBreakdown[];
  recommendations: string[];
}

interface SensitivityAnalysisPanelProps {
  data: SensitivityResult | null;
  isLoading?: boolean;
  onRunAnalysis?: (targetRunway: number, targetProbability: number) => void;
  onWhatIf?: (driver: string, change: number) => void;
}

const DRIVER_ICONS: Record<string, typeof Rocket> = {
  growth_rate: Rocket,
  churn_rate: Users,
  gross_margin: Percent,
  cac: DollarSign,
  dso: Clock,
  conversion_rate: TrendingUp,
};

const DRIVER_LABELS: Record<string, string> = {
  growth_rate: 'Growth Rate',
  churn_rate: 'Churn Rate',
  gross_margin: 'Gross Margin',
  cac: 'Customer Acquisition Cost',
  dso: 'Days Sales Outstanding',
  conversion_rate: 'Conversion Rate',
};

const DRIVER_DESCRIPTIONS: Record<string, string> = {
  growth_rate: 'Increasing growth rate accelerates revenue, extending runway by building cash reserves faster.',
  churn_rate: 'Reducing churn improves customer retention, leading to more predictable recurring revenue.',
  gross_margin: 'Higher gross margin means more cash generated per dollar of revenue.',
  cac: 'Lower acquisition costs mean more efficient customer growth and better unit economics.',
  dso: 'Faster collections improve cash flow timing and reduce working capital needs.',
  conversion_rate: 'Better conversion means more customers from the same marketing spend.',
};

const GAP_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

function formatDriverValue(driver: string, value: number): string {
  if (driver === 'cac') return formatCurrencyAbbrev(value);
  if (driver === 'dso') return `${value.toFixed(0)} days`;
  return `${value.toFixed(1)}%`;
}

function TargetControls({ 
  targetRunway, 
  targetProbability, 
  onUpdate,
  isLoading 
}: { 
  targetRunway: number; 
  targetProbability: number;
  onUpdate: (runway: number, probability: number) => void;
  isLoading: boolean;
}) {
  const [localRunway, setLocalRunway] = useState(targetRunway);
  const [localProbability, setLocalProbability] = useState(targetProbability * 100);

  return (
    <Card className="border-primary/20">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Target className="h-5 w-5 text-primary" />
          <CardTitle className="text-base">Set Your Targets</CardTitle>
        </div>
        <CardDescription>
          Define your runway goal and confidence level to see what changes are needed
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="target-runway" className="text-sm font-medium">
                Target Runway
              </Label>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p>Number of months of cash runway you want to achieve. 18 months is typically recommended before fundraising.</p>
                </TooltipContent>
              </Tooltip>
            </div>
            <div className="flex items-center gap-2">
              <Slider
                id="target-runway"
                min={6}
                max={36}
                step={1}
                value={[localRunway]}
                onValueChange={([v]) => setLocalRunway(v)}
                className="flex-1"
                data-testid="slider-target-runway"
              />
              <span className="font-mono text-sm w-12 text-right" data-testid="text-slider-runway-value">{localRunway}mo</span>
            </div>
          </div>
          
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="target-probability" className="text-sm font-medium">
                Confidence Level
              </Label>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p>Probability of achieving your target runway. 70% is a reasonable confidence level that accounts for uncertainty.</p>
                </TooltipContent>
              </Tooltip>
            </div>
            <div className="flex items-center gap-2">
              <Slider
                id="target-probability"
                min={50}
                max={95}
                step={5}
                value={[localProbability]}
                onValueChange={([v]) => setLocalProbability(v)}
                className="flex-1"
                data-testid="slider-target-probability"
              />
              <span className="font-mono text-sm w-12 text-right" data-testid="text-slider-probability-value">{localProbability}%</span>
            </div>
          </div>
        </div>
        
        <Button 
          onClick={() => onUpdate(localRunway, localProbability / 100)}
          disabled={isLoading}
          className="w-full"
          data-testid="button-run-analysis"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Play className="h-4 w-4 mr-2" />
              Run Analysis
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}

function GapBreakdownChart({ breakdown, totalGap }: { breakdown: GapBreakdown[]; totalGap: number }) {
  const chartData = useMemo(() => 
    breakdown.map((g, i) => ({
      name: DRIVER_LABELS[g.driver] || g.driver,
      value: g.contribution_pct,
      color: GAP_COLORS[i % GAP_COLORS.length],
    })),
    [breakdown]
  );

  if (breakdown.length === 0 || totalGap <= 0) {
    return null;
  }

  return (
    <Card data-testid="card-gap-breakdown">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-primary" />
          <CardTitle className="text-base">Probability Gap Breakdown</CardTitle>
        </div>
        <CardDescription>
          How each driver contributes to closing the <span data-testid="text-gap-total">{totalGap.toFixed(1)}%</span> gap
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[200px]" data-testid="chart-gap-breakdown">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical">
              <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
              <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 12 }} />
              <RechartsTooltip 
                formatter={(value: number) => [`${value.toFixed(1)}%`, 'Contribution']}
              />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        
        <div className="mt-4 flex flex-wrap gap-2" data-testid="gap-breakdown-badges">
          {breakdown.map((g, i) => (
            <Badge 
              key={g.driver} 
              variant="outline"
              className="text-xs"
              style={{ borderColor: GAP_COLORS[i % GAP_COLORS.length] }}
              data-testid={`badge-gap-${g.driver}`}
            >
              <span 
                className="w-2 h-2 rounded-full mr-1"
                style={{ backgroundColor: GAP_COLORS[i % GAP_COLORS.length] }}
              />
              {DRIVER_LABELS[g.driver]}: {g.contribution_pct.toFixed(0)}%
            </Badge>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function EnhancedDriverCard({ 
  driver, 
  onWhatIf,
  rank
}: { 
  driver: SensitivityDriver; 
  onWhatIf?: (driver: string, change: number) => void;
  rank: number;
}) {
  const Icon = DRIVER_ICONS[driver.driver] || TrendingUp;
  const label = DRIVER_LABELS[driver.driver] || driver.driver;
  const description = DRIVER_DESCRIPTIONS[driver.driver] || driver.explanation;
  
  const progressValue = useMemo(() => {
    if (driver.impact_direction === 'decrease') {
      if (driver.current_value <= driver.target_threshold) return 100;
      return Math.max(0, Math.min(100, (driver.target_threshold / driver.current_value) * 100));
    } else {
      if (driver.current_value >= driver.target_threshold) return 100;
      return Math.max(0, Math.min(100, (driver.current_value / driver.target_threshold) * 100));
    }
  }, [driver]);

  const distanceToTarget = useMemo(() => {
    const diff = driver.target_threshold - driver.current_value;
    return driver.impact_direction === 'decrease' ? -diff : diff;
  }, [driver]);

  const isAchieved = progressValue >= 100;

  return (
    <Card className={`transition-all ${isAchieved ? 'border-emerald-500/30' : 'hover-elevate'}`} data-testid={`card-driver-${driver.driver}`}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <div className={`p-2 rounded-lg ${isAchieved ? 'bg-emerald-500/20' : 'bg-primary/10'}`}>
              <Icon className={`h-4 w-4 ${isAchieved ? 'text-emerald-500' : 'text-primary'}`} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h4 className="font-medium text-sm" data-testid={`text-driver-name-${driver.driver}`}>{label}</h4>
                {rank <= 3 && (
                  <Badge variant="secondary" className="text-xs">
                    #{rank} Impact
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground">{description}</p>
            </div>
          </div>
          
          {isAchieved ? (
            <Badge className="bg-emerald-500/20 text-emerald-400 shrink-0" data-testid={`badge-status-${driver.driver}`}>
              <CheckCircle2 className="h-3 w-3 mr-1" />
              Achieved
            </Badge>
          ) : (
            <Badge 
              variant="outline" 
              className={driver.achievable ? 'text-amber-500' : 'text-red-500'}
              data-testid={`badge-status-${driver.driver}`}
            >
              {driver.achievable ? 'Achievable' : 'Challenging'}
            </Badge>
          )}
        </div>
        
        <div className="grid grid-cols-3 gap-2 mb-3 text-center">
          <div className="p-2 bg-muted/50 rounded-lg">
            <p className="text-xs text-muted-foreground">Current</p>
            <p className="font-mono font-medium text-sm" data-testid={`text-current-${driver.driver}`}>
              {formatDriverValue(driver.driver, driver.current_value)}
            </p>
          </div>
          <div className="p-2 bg-muted/50 rounded-lg flex items-center justify-center">
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className={`p-2 rounded-lg ${isAchieved ? 'bg-emerald-500/10' : 'bg-primary/10'}`}>
            <p className="text-xs text-muted-foreground">Target</p>
            <p className={`font-mono font-medium text-sm ${isAchieved ? 'text-emerald-500' : 'text-primary'}`} data-testid={`text-target-${driver.driver}`}>
              {formatDriverValue(driver.driver, driver.target_threshold)}
            </p>
          </div>
        </div>
        
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Progress to Target</span>
            <span className={`font-mono ${isAchieved ? 'text-emerald-500' : ''}`} data-testid={`text-progress-${driver.driver}`}>
              {isAchieved ? 'Complete' : `${distanceToTarget > 0 ? '+' : ''}${formatDriverValue(driver.driver, distanceToTarget)} needed`}
            </span>
          </div>
          <Progress 
            value={progressValue} 
            className="h-2"
            data-testid={`progress-bar-${driver.driver}`}
          />
        </div>
        
        <div className="flex items-center justify-between mt-3 pt-3 border-t">
          <div className="flex items-center gap-2 text-xs">
            <Badge 
              variant="outline" 
              className={driver.impact_magnitude > 5 ? 'text-emerald-500' : 'text-muted-foreground'}
              data-testid={`badge-impact-${driver.driver}`}
            >
              {driver.impact_magnitude.toFixed(1)}% impact
            </Badge>
            {driver.gap_contribution > 0 && (
              <Badge variant="outline" className="text-muted-foreground" data-testid={`badge-contribution-${driver.driver}`}>
                {driver.gap_contribution.toFixed(0)}% of gap
              </Badge>
            )}
          </div>
          
          {driver.benchmark_value && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge 
                  variant="outline" 
                  className={
                    driver.benchmark_comparison === 'top_quartile' ? 'text-emerald-500' :
                    driver.benchmark_comparison === 'below_median' ? 'text-amber-500' :
                    'text-muted-foreground'
                  }
                  data-testid={`badge-benchmark-${driver.driver}`}
                >
                  vs {formatDriverValue(driver.driver, driver.benchmark_value)} median
                </Badge>
              </TooltipTrigger>
              <TooltipContent>
                <p className="text-xs">
                  {driver.benchmark_comparison === 'top_quartile' && 'You are in the top 25% of companies'}
                  {driver.benchmark_comparison === 'above_median' && 'You are above the industry median'}
                  {driver.benchmark_comparison === 'below_median' && 'You are below the industry median'}
                </p>
              </TooltipContent>
            </Tooltip>
          )}
        </div>

        {onWhatIf && !isAchieved && driver.recommended_change > 0 && (
          <Button
            variant="ghost"
            size="sm"
            className="w-full mt-3"
            onClick={() => onWhatIf(driver.driver, driver.recommended_change)}
            data-testid={`button-whatif-${driver.driver}`}
          >
            <Lightbulb className="h-4 w-4 mr-2" />
            Try "What If?" Scenario
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

function SummaryCards({ data }: { data: SensitivityResult }) {
  const gapColor = data.current_probability >= data.target_probability 
    ? 'text-emerald-500' 
    : data.total_gap <= 10 ? 'text-amber-500' : 'text-red-500';

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="summary-cards">
      <Card className="p-4 text-center">
        <p className="text-xs text-muted-foreground mb-1">Target Runway</p>
        <p className="text-2xl font-mono font-bold text-primary" data-testid="text-target-runway">
          {data.target_runway_months}mo
        </p>
      </Card>
      
      <Card className="p-4 text-center">
        <p className="text-xs text-muted-foreground mb-1">Target Confidence</p>
        <p className="text-2xl font-mono font-bold" data-testid="text-target-confidence">
          {(data.target_probability * 100).toFixed(0)}%
        </p>
      </Card>
      
      <Card className="p-4 text-center">
        <p className="text-xs text-muted-foreground mb-1">Current Probability</p>
        <p className="text-2xl font-mono font-bold" data-testid="text-current-probability">
          {(data.current_probability * 100).toFixed(0)}%
        </p>
      </Card>
      
      <Card className={`p-4 text-center ${data.achievable ? '' : 'border-amber-500/30'}`}>
        <p className="text-xs text-muted-foreground mb-1">Probability Gap</p>
        <p className={`text-2xl font-mono font-bold ${gapColor}`} data-testid="text-probability-gap">
          {data.total_gap > 0 ? `-${data.total_gap.toFixed(1)}%` : 'None'}
        </p>
      </Card>
    </div>
  );
}

export function SensitivityAnalysisPanel({ 
  data, 
  isLoading,
  onRunAnalysis,
  onWhatIf
}: SensitivityAnalysisPanelProps) {
  const [targetRunway, setTargetRunway] = useState(data?.target_runway_months || 18);
  const [targetProbability, setTargetProbability] = useState(data?.target_probability || 0.7);

  const handleRunAnalysis = (runway: number, probability: number) => {
    setTargetRunway(runway);
    setTargetProbability(probability);
    onRunAnalysis?.(runway, probability);
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <div className="grid grid-cols-4 gap-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }
  
  if (!data) {
    return (
      <div className="space-y-6">
        <TargetControls
          targetRunway={targetRunway}
          targetProbability={targetProbability}
          onUpdate={handleRunAnalysis}
          isLoading={isLoading || false}
        />
        
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <Target className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground mb-2">
              Set your targets and run the analysis to discover which drivers have the biggest impact
            </p>
            <p className="text-sm text-muted-foreground">
              Find out "what must be true" to achieve your desired runway with confidence
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }
  
  const sortedDrivers = [...data.key_drivers].sort((a, b) => b.impact_magnitude - a.impact_magnitude);
  
  return (
    <div className="space-y-6">
      <TargetControls
        targetRunway={data.target_runway_months}
        targetProbability={data.target_probability}
        onUpdate={handleRunAnalysis}
        isLoading={isLoading || false}
      />
      
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">Analysis Results</h2>
          {data.achievable ? (
            <Badge className="bg-emerald-500/20 text-emerald-400">
              <CheckCircle2 className="h-3 w-3 mr-1" />
              Target Achievable
            </Badge>
          ) : (
            <Badge variant="destructive">
              <AlertTriangle className="h-3 w-3 mr-1" />
              Gap to Close
            </Badge>
          )}
        </div>
      </div>
      
      <SummaryCards data={data} />
      
      {data.gap_breakdown.length > 0 && data.total_gap > 0 && (
        <GapBreakdownChart breakdown={data.gap_breakdown} totalGap={data.total_gap} />
      )}
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-4">
          <h3 className="font-medium flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-primary" />
            Key Drivers (Ranked by Impact)
          </h3>
          <div className="space-y-3">
            {sortedDrivers.slice(0, 3).map((driver, index) => (
              <EnhancedDriverCard 
                key={driver.driver} 
                driver={driver} 
                onWhatIf={onWhatIf}
                rank={index + 1}
              />
            ))}
          </div>
        </div>
        
        <div className="space-y-4">
          {data.recommendations && data.recommendations.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  <Lightbulb className="h-5 w-5 text-amber-500" />
                  <CardTitle className="text-base">Recommendations</CardTitle>
                </div>
                <CardDescription>
                  Actions to close the probability gap
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3" data-testid="list-recommendations">
                  {data.recommendations.map((rec, index) => (
                    <li key={index} className="flex items-start gap-2 p-2 rounded-lg bg-muted/50" data-testid={`item-recommendation-${index}`}>
                      <CheckCircle2 className="h-4 w-4 mt-0.5 text-primary shrink-0" />
                      <span className="text-sm">{rec}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
          
          {sortedDrivers.length > 3 && (
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-muted-foreground">Other Drivers</h4>
              {sortedDrivers.slice(3).map((driver, index) => (
                <EnhancedDriverCard 
                  key={driver.driver} 
                  driver={driver}
                  onWhatIf={onWhatIf}
                  rank={index + 4}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
