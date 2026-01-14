import { useState, useMemo, useCallback, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { 
  Trophy, TrendingUp, Shield, AlertTriangle, Coins, 
  Info, ArrowUpRight, ArrowDownRight, SlidersHorizontal, 
  Gauge, ChevronDown, ChevronUp, Settings2, Filter, Download, 
  Lightbulb, BarChart3, BookOpen
} from 'lucide-react';
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, Legend } from 'recharts';

interface DecisionScore {
  scenario_key: string;
  scenario_name: string;
  survival_12m_prob: number;
  survival_18m_prob: number;
  expected_arr_18m: number;
  downside_risk_cvar: number;
  dilution_pct: number;
  complexity_score: number;
  composite_score: number;
  rank: number;
  survival_component?: number;
  growth_component?: number;
  risk_component?: number;
  dilution_component?: number;
  complexity_component?: number;
}

interface DecisionRankingTableProps {
  rankings: DecisionScore[];
  baselineKey?: string;
  onSelectScenario?: (scenarioKey: string) => void;
  testId?: string;
}

type SortField = 'composite_score' | 'survival_18m_prob' | 'expected_arr_18m' | 'downside_risk_cvar' | 'dilution_pct' | 'complexity_score';

interface ScoringWeights {
  survival: number;
  growth: number;
  downside_risk: number;
  dilution: number;
  complexity: number;
}

interface ThresholdFilters {
  minSurvival: number;
  maxDilution: number;
  maxComplexity: number;
  enabled: boolean;
}

const DEFAULT_WEIGHTS: ScoringWeights = {
  survival: 0.30,
  growth: 0.25,
  downside_risk: 0.20,
  dilution: 0.15,
  complexity: 0.10
};

const METRIC_DEFINITIONS: Record<string, { title: string; description: string; calculation: string; importance: string }> = {
  survival: {
    title: "Survival Probability (18m)",
    description: "The likelihood that your company will have positive cash balance 18 months from now based on Monte Carlo simulation.",
    calculation: "Calculated from 1,000+ simulation runs - percentage of scenarios where cash stays above zero.",
    importance: "Critical for understanding runway risk. A survival rate below 80% indicates significant business risk."
  },
  arr: {
    title: "Expected ARR (18m)",
    description: "Projected Annual Recurring Revenue at the 18-month mark, representing the median outcome across simulations.",
    calculation: "Median of monthly revenue projections × 12, accounting for growth rate, churn, and market conditions.",
    importance: "Key indicator of growth trajectory. Compare against industry benchmarks for your stage."
  },
  risk: {
    title: "Downside Risk (CVaR)",
    description: "Conditional Value at Risk - the expected cash position in the worst 10% of scenarios (P10).",
    calculation: "Average of bottom 10% of simulated cash outcomes. Negative values indicate potential cash shortfall.",
    importance: "Shows worst-case scenario impact. Plan for this downside to ensure business continuity."
  },
  dilution: {
    title: "Dilution Percentage",
    description: "Equity ownership given up through fundraising events in this scenario.",
    calculation: "Total new shares issued / (existing shares + new shares). Zero if no fundraising occurs.",
    importance: "Affects founder/team ownership. Balance growth capital needs against long-term ownership goals."
  },
  complexity: {
    title: "Execution Complexity",
    description: "A 0-10 score indicating how difficult the scenario is to execute, based on number of changes and dependencies.",
    calculation: "Sum of weighted factors: hiring changes, cost restructuring, fundraising, operational pivots.",
    importance: "Higher complexity means more execution risk. Simple plans are often more reliable."
  },
  composite: {
    title: "Composite Score",
    description: "A weighted combination of all metrics that balances growth potential against risk factors.",
    calculation: "Survival × W1 + Growth × W2 + (1-Risk) × W3 + (1-Dilution) × W4 + (1-Complexity) × W5",
    importance: "Use as a starting point for comparison, then customize weights based on your priorities."
  }
};

const SCENARIO_RECOMMENDATIONS: Record<string, string> = {
  'baseline': "Continue current trajectory. Best for stable markets with predictable customer demand.",
  'cost_cutting': "Extends runway significantly but may slow product development. Consider if market conditions are uncertain.",
  'aggressive_growth': "Maximizes growth but increases burn and risk. Ideal when market opportunity is time-sensitive.",
  'conservative_cut': "Balanced approach to runway extension while maintaining core capabilities.",
  'fundraise': "Maintains growth and minimizes cost cuts but introduces dilution. Ideal if capital is available.",
  'hiring_freeze': "Preserves cash without layoffs. May slow growth but maintains team morale.",
  'default': "Evaluate this scenario against your risk tolerance and growth ambitions."
};

function formatCurrency(value: number): string {
  const absValue = Math.abs(value);
  if (absValue >= 1000000000) {
    return `$${(value / 1000000000).toFixed(1)}B`;
  } else if (absValue >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  } else if (absValue >= 1000) {
    return `$${(value / 1000).toFixed(0)}K`;
  }
  return `$${value.toFixed(0)}`;
}

function formatFullCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(value);
}

function getRankBadge(rank: number) {
  switch (rank) {
    case 1:
      return (
        <Badge className="bg-yellow-500/20 text-yellow-400" aria-label="Best scenario">
          <Trophy className="h-3 w-3 mr-1" />
          Best
        </Badge>
      );
    case 2:
      return (
        <Badge className="bg-slate-400/20 text-slate-300" aria-label="Second best scenario">
          2nd
        </Badge>
      );
    case 3:
      return (
        <Badge className="bg-amber-600/20 text-amber-400" aria-label="Third best scenario">
          3rd
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" aria-label={`Rank ${rank}`}>
          #{rank}
        </Badge>
      );
  }
}

function DeltaIndicator({ 
  current, 
  baseline, 
  suffix = '', 
  inverted = false,
  formatFn 
}: { 
  current: number; 
  baseline: number; 
  suffix?: string; 
  inverted?: boolean;
  formatFn?: (val: number) => string;
}) {
  const delta = current - baseline;
  if (Math.abs(delta) < 0.01) {
    return <span className="text-xs text-muted-foreground ml-1">(+0{suffix})</span>;
  }
  
  const isPositive = inverted ? delta < 0 : delta > 0;
  const sign = delta > 0 ? '+' : '';
  const displayValue = formatFn 
    ? `${sign}${formatFn(delta)}` 
    : `${sign}${delta.toFixed(1)}${suffix}`;
  
  return (
    <span className={`text-xs ml-1 ${isPositive ? 'text-emerald-500' : 'text-red-500'}`}>
      {isPositive ? (
        <ArrowUpRight className="h-3 w-3 inline" />
      ) : (
        <ArrowDownRight className="h-3 w-3 inline" />
      )}
      {displayValue}
    </span>
  );
}

function MetricInfoIcon({ metricKey }: { metricKey: keyof typeof METRIC_DEFINITIONS }) {
  const definition = METRIC_DEFINITIONS[metricKey];
  if (!definition) return null;
  
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button 
          variant="ghost" 
          size="icon" 
          className="h-4 w-4 p-0 ml-1 opacity-60 hover:opacity-100"
          onClick={(e) => e.stopPropagation()}
          aria-label={`Learn more about ${definition.title}`}
        >
          <Info className="h-3 w-3" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80" align="start">
        <div className="space-y-2">
          <h4 className="font-medium text-sm flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-primary" />
            {definition.title}
          </h4>
          <p className="text-xs text-muted-foreground">{definition.description}</p>
          <div className="pt-2 border-t">
            <p className="text-xs"><strong>How it's calculated:</strong> {definition.calculation}</p>
          </div>
          <div className="pt-2 border-t">
            <p className="text-xs"><strong>Why it matters:</strong> {definition.importance}</p>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}

function ScoreBreakdownBar({ 
  survivalScore, 
  growthScore, 
  riskScore, 
  dilutionScore, 
  complexityScore,
  weights 
}: {
  survivalScore: number;
  growthScore: number;
  riskScore: number;
  dilutionScore: number;
  complexityScore: number;
  weights: ScoringWeights;
}) {
  const segments = [
    { label: 'Survival', value: survivalScore, color: 'bg-emerald-500', weight: weights.survival },
    { label: 'Growth', value: growthScore, color: 'bg-blue-500', weight: weights.growth },
    { label: 'Risk', value: riskScore, color: 'bg-amber-500', weight: weights.downside_risk },
    { label: 'Dilution', value: dilutionScore, color: 'bg-purple-500', weight: weights.dilution },
    { label: 'Complexity', value: complexityScore, color: 'bg-slate-500', weight: weights.complexity },
  ];

  return (
    <div className="space-y-2">
      <div className="flex h-3 rounded-full overflow-hidden bg-muted">
        {segments.map((seg) => (
          <div
            key={seg.label}
            className={`${seg.color} transition-all`}
            style={{ width: `${seg.value * 100}%` }}
            title={`${seg.label}: ${(seg.value * 100).toFixed(1)}`}
          />
        ))}
      </div>
      <div className="grid grid-cols-5 gap-1 text-xs">
        {segments.map(seg => (
          <div key={seg.label} className="text-center">
            <div className={`w-2 h-2 rounded-full ${seg.color} mx-auto mb-1`} />
            <p className="text-muted-foreground">{seg.label}</p>
            <p className="font-mono">{(seg.value * 100).toFixed(0)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function TradeOffRadarChart({ score, baseline, allScores }: { 
  score: DecisionScore; 
  baseline?: DecisionScore;
  allScores: DecisionScore[];
}) {
  const maxValues = useMemo(() => {
    if (allScores.length === 0) return { arr: 1, risk: 1 };
    const arrValues = allScores.map(s => s.expected_arr_18m);
    const riskValues = allScores.map(s => Math.abs(s.downside_risk_cvar));
    return {
      arr: Math.max(...arrValues, 1),
      risk: Math.max(...riskValues, 1),
    };
  }, [allScores]);

  const data = useMemo(() => [
    {
      metric: 'Survival',
      value: Math.min(100, score.survival_18m_prob),
      baseline: baseline ? Math.min(100, baseline.survival_18m_prob) : undefined,
      fullMark: 100,
    },
    {
      metric: 'Growth',
      value: Math.min(100, (score.expected_arr_18m / maxValues.arr) * 100),
      baseline: baseline ? Math.min(100, (baseline.expected_arr_18m / maxValues.arr) * 100) : undefined,
      fullMark: 100,
    },
    {
      metric: 'Low Risk',
      value: Math.max(0, 100 - (Math.abs(score.downside_risk_cvar) / maxValues.risk) * 100),
      baseline: baseline ? Math.max(0, 100 - (Math.abs(baseline.downside_risk_cvar) / maxValues.risk) * 100) : undefined,
      fullMark: 100,
    },
    {
      metric: 'Low Dilution',
      value: Math.max(0, 100 - score.dilution_pct),
      baseline: baseline ? Math.max(0, 100 - baseline.dilution_pct) : undefined,
      fullMark: 100,
    },
    {
      metric: 'Simplicity',
      value: Math.max(0, 100 - score.complexity_score * 10),
      baseline: baseline ? Math.max(0, 100 - baseline.complexity_score * 10) : undefined,
      fullMark: 100,
    },
  ], [score, baseline, maxValues]);

  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
          <PolarGrid stroke="hsl(var(--muted-foreground) / 0.3)" />
          <PolarAngleAxis 
            dataKey="metric" 
            tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }}
          />
          <PolarRadiusAxis 
            angle={90} 
            domain={[0, 100]} 
            tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 8 }}
            tickCount={5}
          />
          {baseline && (
            <Radar
              name="Baseline"
              dataKey="baseline"
              stroke="hsl(var(--muted-foreground))"
              fill="hsl(var(--muted-foreground))"
              fillOpacity={0.1}
              strokeDasharray="4 4"
            />
          )}
          <Radar
            name={score.scenario_name}
            dataKey="value"
            stroke="hsl(var(--primary))"
            fill="hsl(var(--primary))"
            fillOpacity={0.3}
          />
          <Legend wrapperStyle={{ fontSize: '10px' }} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

function WeightsPanel({ 
  weights, 
  onChange, 
  onReset 
}: { 
  weights: ScoringWeights; 
  onChange: (weights: ScoringWeights) => void;
  onReset: () => void;
}) {
  const updateWeight = (key: keyof ScoringWeights, value: number) => {
    const newWeights = { ...weights, [key]: value };
    const total = Object.values(newWeights).reduce((a, b) => a + b, 0);
    if (total > 0) {
      const normalized: ScoringWeights = {
        survival: newWeights.survival / total,
        growth: newWeights.growth / total,
        downside_risk: newWeights.downside_risk / total,
        dilution: newWeights.dilution / total,
        complexity: newWeights.complexity / total,
      };
      onChange(normalized);
    }
  };

  const weightItems = [
    { key: 'survival' as const, label: 'Survival', color: 'bg-emerald-500' },
    { key: 'growth' as const, label: 'Growth', color: 'bg-blue-500' },
    { key: 'downside_risk' as const, label: 'Risk', color: 'bg-amber-500' },
    { key: 'dilution' as const, label: 'Dilution', color: 'bg-purple-500' },
    { key: 'complexity' as const, label: 'Complexity', color: 'bg-slate-500' },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium">Customize Weights</h4>
        <Button variant="ghost" size="sm" onClick={onReset} className="text-xs">
          Reset to Default
        </Button>
      </div>
      <div className="space-y-3">
        {weightItems.map(({ key, label, color }) => (
          <div key={key} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${color}`} />
                <span>{label}</span>
              </div>
              <span className="font-mono">{(weights[key] * 100).toFixed(0)}%</span>
            </div>
            <Slider
              value={[weights[key] * 100]}
              onValueChange={([val]) => updateWeight(key, val / 100)}
              max={100}
              step={5}
              className="h-1"
            />
          </div>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        Weights automatically normalize to 100%. Higher weight = more influence on composite score.
      </p>
    </div>
  );
}

function FilterPanel({ 
  filters, 
  onChange 
}: { 
  filters: ThresholdFilters; 
  onChange: (filters: ThresholdFilters) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium">Filter Scenarios</h4>
        <div className="flex items-center gap-2">
          <Label htmlFor="filter-enabled" className="text-xs">Enable Filters</Label>
          <Switch 
            id="filter-enabled"
            checked={filters.enabled}
            onCheckedChange={(enabled) => onChange({ ...filters, enabled })}
          />
        </div>
      </div>
      <div className="space-y-3">
        <div className="space-y-1">
          <Label className="text-xs">Min Survival: {filters.minSurvival}%</Label>
          <Slider
            value={[filters.minSurvival]}
            onValueChange={([val]) => onChange({ ...filters, minSurvival: val })}
            max={100}
            step={5}
            disabled={!filters.enabled}
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs">Max Dilution: {filters.maxDilution}%</Label>
          <Slider
            value={[filters.maxDilution]}
            onValueChange={([val]) => onChange({ ...filters, maxDilution: val })}
            max={100}
            step={5}
            disabled={!filters.enabled}
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs">Max Complexity: {filters.maxComplexity}/10</Label>
          <Slider
            value={[filters.maxComplexity]}
            onValueChange={([val]) => onChange({ ...filters, maxComplexity: val })}
            max={10}
            step={1}
            disabled={!filters.enabled}
          />
        </div>
      </div>
    </div>
  );
}

function getScenarioRecommendation(score: DecisionScore): string {
  const key = score.scenario_key.toLowerCase();
  for (const [pattern, recommendation] of Object.entries(SCENARIO_RECOMMENDATIONS)) {
    if (key.includes(pattern)) {
      return recommendation;
    }
  }
  
  if (score.survival_18m_prob < 50) {
    return "High-risk scenario with survival probability below 50%. Consider risk mitigation strategies.";
  }
  if (score.dilution_pct > 20) {
    return "Significant equity dilution. Evaluate if the growth benefits justify ownership reduction.";
  }
  if (score.complexity_score > 7) {
    return "High execution complexity. Ensure you have the team and resources to implement effectively.";
  }
  if (score.survival_18m_prob > 90 && score.expected_arr_18m > 0) {
    return "Strong survival outlook with positive revenue trajectory. Solid foundation for growth.";
  }
  
  return SCENARIO_RECOMMENDATIONS.default;
}

interface RankedScore extends DecisionScore {
  displayRank: number;
  customScore: number;
}

function exportToCSV(rankings: RankedScore[], weights: ScoringWeights, baseline?: DecisionScore) {
  const headers = [
    'Rank', 'Scenario', 'Weighted Score', 'Survival 18m (%)', 'Expected ARR',
    'Downside Risk', 'Dilution (%)', 'Complexity', 'Survival Delta', 'ARR Delta'
  ];
  
  const rows = rankings.map(score => {
    const survivalDelta = baseline ? (score.survival_18m_prob - baseline.survival_18m_prob).toFixed(1) : 'N/A';
    const arrDelta = baseline && baseline.expected_arr_18m > 0 
      ? ((score.expected_arr_18m - baseline.expected_arr_18m) / baseline.expected_arr_18m * 100).toFixed(1) + '%'
      : 'N/A';
    
    return [
      score.displayRank,
      score.scenario_name,
      (score.customScore * 100).toFixed(1),
      score.survival_18m_prob.toFixed(1),
      score.expected_arr_18m.toFixed(0),
      score.downside_risk_cvar.toFixed(0),
      score.dilution_pct.toFixed(1),
      score.complexity_score.toFixed(1),
      survivalDelta,
      arrDelta
    ].join(',');
  });
  
  const weightsRow = `\n\nWeights Applied:,Survival ${(weights.survival * 100).toFixed(0)}%,Growth ${(weights.growth * 100).toFixed(0)}%,Risk ${(weights.downside_risk * 100).toFixed(0)}%,Dilution ${(weights.dilution * 100).toFixed(0)}%,Complexity ${(weights.complexity * 100).toFixed(0)}%`;
  const timestamp = `\nGenerated:,${new Date().toISOString()}`;
  
  const csv = [headers.join(','), ...rows].join('\n') + weightsRow + timestamp;
  
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `scenario-ranking-${new Date().toISOString().split('T')[0]}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function DecisionRankingTable({ 
  rankings, 
  baselineKey,
  onSelectScenario,
  testId = 'decision-ranking'
}: DecisionRankingTableProps) {
  const [sortBy, setSortBy] = useState<SortField>('composite_score');
  const [sortDesc, setSortDesc] = useState(true);
  const [expandedCard, setExpandedCard] = useState<string | null>(null);
  const [weights, setWeights] = useState<ScoringWeights>(DEFAULT_WEIGHTS);
  const [filters, setFilters] = useState<ThresholdFilters>({
    minSurvival: 0,
    maxDilution: 100,
    maxComplexity: 10,
    enabled: false
  });
  const [showWeightsPanel, setShowWeightsPanel] = useState(false);
  const [showFiltersPanel, setShowFiltersPanel] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('decisionWeights');
      if (saved) {
        try {
          setWeights(JSON.parse(saved));
        } catch {
          // Invalid JSON, use defaults
        }
      }
    }
  }, []);

  const handleWeightsChange = useCallback((newWeights: ScoringWeights) => {
    setWeights(newWeights);
    if (typeof window !== 'undefined') {
      localStorage.setItem('decisionWeights', JSON.stringify(newWeights));
    }
  }, []);

  const resetWeights = useCallback(() => {
    setWeights(DEFAULT_WEIGHTS);
    if (typeof window !== 'undefined') {
      localStorage.removeItem('decisionWeights');
    }
  }, []);

  const baseline = useMemo(() => {
    if (baselineKey) {
      return rankings.find(r => r.scenario_key === baselineKey);
    }
    return rankings.find(r => r.scenario_name.toLowerCase().includes('baseline')) || rankings[0];
  }, [rankings, baselineKey]);

  const computeCustomScore = useCallback((score: DecisionScore) => {
    const maxArr = Math.max(...rankings.map(r => r.expected_arr_18m));
    const maxRisk = Math.max(...rankings.map(r => Math.abs(r.downside_risk_cvar)));
    
    const survivalNorm = Math.min(1, score.survival_18m_prob / 100);
    const growthNorm = maxArr > 0 ? score.expected_arr_18m / maxArr : 0;
    const riskNorm = maxRisk > 0 ? 1 - Math.abs(score.downside_risk_cvar) / maxRisk : 1;
    const dilutionNorm = 1 - score.dilution_pct / 100;
    const complexityNorm = 1 - score.complexity_score / 10;
    
    return (
      survivalNorm * weights.survival +
      growthNorm * weights.growth +
      riskNorm * weights.downside_risk +
      dilutionNorm * weights.dilution +
      complexityNorm * weights.complexity
    );
  }, [rankings, weights]);

  const filteredAndSortedRankings = useMemo(() => {
    let filtered = rankings;
    
    if (filters.enabled) {
      filtered = rankings.filter(score => 
        score.survival_18m_prob >= filters.minSurvival &&
        score.dilution_pct <= filters.maxDilution &&
        score.complexity_score <= filters.maxComplexity
      );
    }
    
    const withCustomScores = filtered.map(score => ({
      ...score,
      customScore: computeCustomScore(score)
    }));
    
    const sorted = [...withCustomScores].sort((a, b) => {
      if (sortBy === 'composite_score') {
        return sortDesc ? b.customScore - a.customScore : a.customScore - b.customScore;
      }
      
      let aVal = a[sortBy];
      let bVal = b[sortBy];
      
      if (sortBy === 'downside_risk_cvar' || sortBy === 'dilution_pct' || sortBy === 'complexity_score') {
        return sortDesc ? aVal - bVal : bVal - aVal;
      }
      
      return sortDesc ? bVal - aVal : aVal - bVal;
    });
    
    return sorted.map((s, idx) => ({ ...s, displayRank: idx + 1 }));
  }, [rankings, sortBy, sortDesc, filters, computeCustomScore]);

  const computeComponentScores = useCallback((score: DecisionScore) => {
    if (score.survival_component !== undefined) {
      return {
        survivalScore: score.survival_component,
        growthScore: score.growth_component || 0,
        riskScore: score.risk_component || 0,
        dilutionScore: score.dilution_component || 0,
        complexityScore: score.complexity_component || 0,
      };
    }
    
    const maxArr = Math.max(...rankings.map(r => r.expected_arr_18m));
    const maxRisk = Math.max(...rankings.map(r => Math.abs(r.downside_risk_cvar)));
    
    const survivalScore = Math.min(1, score.survival_18m_prob / 100) * weights.survival;
    const growthScore = (maxArr > 0 ? score.expected_arr_18m / maxArr : 0) * weights.growth;
    const riskScore = (maxRisk > 0 ? 1 - Math.abs(score.downside_risk_cvar) / maxRisk : 1) * weights.downside_risk;
    const dilutionScore = (1 - (score.dilution_pct / 100)) * weights.dilution;
    const complexityScore = (1 - (score.complexity_score / 10)) * weights.complexity;
    
    return { survivalScore, growthScore, riskScore, dilutionScore, complexityScore };
  }, [rankings, weights]);

  const effectiveBaseline = useMemo(() => {
    if (!baseline) return undefined;
    const isBaselineInFiltered = filteredAndSortedRankings.some(
      s => s.scenario_key === baseline.scenario_key
    );
    return isBaselineInFiltered ? baseline : undefined;
  }, [baseline, filteredAndSortedRankings]);

  if (!rankings || rankings.length === 0) {
    return (
      <Card data-testid={testId}>
        <CardContent className="py-12 text-center">
          <Trophy className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">
            No decision rankings available. Run a multi-scenario simulation first.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid={testId}>
      <CardHeader>
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              Decision Ranking
              <MetricInfoIcon metricKey="composite" />
            </CardTitle>
            <CardDescription>
              Scenarios ranked by composite score with relative comparisons
            </CardDescription>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Popover open={showWeightsPanel} onOpenChange={setShowWeightsPanel}>
              <PopoverTrigger asChild>
                <Button 
                  variant="outline" 
                  size="sm"
                  data-testid="button-weights"
                >
                  <Settings2 className="h-4 w-4 mr-2" />
                  Weights
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-80" align="end">
                <WeightsPanel 
                  weights={weights} 
                  onChange={handleWeightsChange}
                  onReset={resetWeights}
                />
              </PopoverContent>
            </Popover>
            
            <Popover open={showFiltersPanel} onOpenChange={setShowFiltersPanel}>
              <PopoverTrigger asChild>
                <Button 
                  variant={filters.enabled ? "default" : "outline"}
                  size="sm"
                  data-testid="button-filters"
                >
                  <Filter className="h-4 w-4 mr-2" />
                  Filters
                  {filters.enabled && (
                    <Badge variant="secondary" className="ml-2 text-xs">ON</Badge>
                  )}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-80" align="end">
                <FilterPanel filters={filters} onChange={setFilters} />
              </PopoverContent>
            </Popover>
            
            <Select 
              value={sortBy} 
              onValueChange={(val) => setSortBy(val as SortField)}
            >
              <SelectTrigger className="w-[180px]" data-testid="select-sort-by">
                <SlidersHorizontal className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Sort by..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="composite_score">Composite Score</SelectItem>
                <SelectItem value="survival_18m_prob">Survival 18m</SelectItem>
                <SelectItem value="expected_arr_18m">Expected ARR</SelectItem>
                <SelectItem value="downside_risk_cvar">Downside Risk</SelectItem>
                <SelectItem value="dilution_pct">Dilution</SelectItem>
                <SelectItem value="complexity_score">Complexity</SelectItem>
              </SelectContent>
            </Select>
            
            <Button
              variant="outline"
              size="icon"
              onClick={() => setSortDesc(!sortDesc)}
              data-testid="button-toggle-sort-order"
              aria-label={sortDesc ? "Sort ascending" : "Sort descending"}
            >
              {sortDesc ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
            </Button>
            
            <Button
              variant="outline"
              size="icon"
              onClick={() => exportToCSV(filteredAndSortedRankings, weights, effectiveBaseline)}
              data-testid="button-export"
              aria-label="Export to CSV"
            >
              <Download className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {filters.enabled && filteredAndSortedRankings.length < rankings.length && (
          <div className="mb-4 p-3 bg-muted/50 rounded-lg flex items-center gap-2 text-sm">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <span>
              Showing {filteredAndSortedRankings.length} of {rankings.length} scenarios 
              (filtered by: Survival ≥ {filters.minSurvival}%, Dilution ≤ {filters.maxDilution}%, Complexity ≤ {filters.maxComplexity}/10)
            </span>
          </div>
        )}
        
        <div className="space-y-4" role="list" aria-label="Scenario rankings">
          {filteredAndSortedRankings.map((score) => {
            const isBaseline = score.scenario_key === effectiveBaseline?.scenario_key;
            const isExpanded = expandedCard === score.scenario_key;
            const componentScores = computeComponentScores(score);
            const customScore = computeCustomScore(score);
            const recommendation = getScenarioRecommendation(score);
            
            return (
              <article
                key={score.scenario_key}
                className={`p-4 rounded-lg border hover-elevate cursor-pointer transition-colors ${
                  score.displayRank === 1 ? 'border-primary/50 bg-primary/5' : ''
                } ${isBaseline ? 'ring-2 ring-muted' : ''}`}
                onClick={() => onSelectScenario?.(score.scenario_key)}
                data-testid={`ranking-card-${score.scenario_key}`}
                role="listitem"
                aria-label={`${score.scenario_name}, rank ${score.displayRank}`}
              >
                <div className="flex items-center justify-between gap-4 mb-3 flex-wrap">
                  <div className="flex items-center gap-3">
                    {getRankBadge(score.displayRank)}
                    <h3 className="font-medium">{score.scenario_name}</h3>
                    {isBaseline && (
                      <Badge variant="secondary" className="text-xs">Baseline</Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <Popover>
                      <PopoverTrigger asChild>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="h-auto py-1"
                          onClick={(e) => e.stopPropagation()}
                          data-testid={`button-score-breakdown-${score.scenario_key}`}
                          aria-label="View score breakdown"
                        >
                          <div className="text-right">
                            <p className="text-xs text-muted-foreground flex items-center gap-1">
                              Composite Score
                              <Info className="h-3 w-3" />
                            </p>
                            <p className="text-lg font-mono font-bold text-primary">
                              {(customScore * 100).toFixed(0)}
                            </p>
                          </div>
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-80" align="end">
                        <div className="space-y-3">
                          <h4 className="font-medium text-sm">Score Breakdown</h4>
                          <p className="text-xs text-muted-foreground">
                            Composite = Survival ({(weights.survival * 100).toFixed(0)}%) + Growth ({(weights.growth * 100).toFixed(0)}%) + Risk ({(weights.downside_risk * 100).toFixed(0)}%) + Dilution ({(weights.dilution * 100).toFixed(0)}%) + Complexity ({(weights.complexity * 100).toFixed(0)}%)
                          </p>
                          <ScoreBreakdownBar {...componentScores} weights={weights} />
                          <div className="pt-2 border-t">
                            <p className="text-xs text-muted-foreground">
                              Final Score: <span className="font-mono font-bold">{(customScore * 100).toFixed(1)}</span> / 100
                            </p>
                          </div>
                        </div>
                      </PopoverContent>
                    </Popover>
                  </div>
                </div>
                
                <Progress 
                  value={Math.min(100, customScore * 100)} 
                  className="h-2 mb-4"
                  aria-label={`Composite score: ${(customScore * 100).toFixed(0)}%`}
                />
                
                <dl className="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm">
                  <div className="flex items-center gap-2">
                    <Shield className="h-4 w-4 text-emerald-500 flex-shrink-0" aria-hidden="true" />
                    <div>
                      <dt className="text-xs text-muted-foreground flex items-center">
                        Survival 18m
                        <MetricInfoIcon metricKey="survival" />
                      </dt>
                      <dd className="font-mono font-medium">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span data-testid={`text-survival-${score.scenario_key}`}>
                              {Math.min(100, score.survival_18m_prob).toFixed(1)}%
                            </span>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Probability of surviving 18 months</p>
                          </TooltipContent>
                        </Tooltip>
                        {!isBaseline && effectiveBaseline && (
                          <DeltaIndicator 
                            current={score.survival_18m_prob} 
                            baseline={effectiveBaseline.survival_18m_prob}
                            suffix="%"
                          />
                        )}
                      </dd>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-blue-500 flex-shrink-0" aria-hidden="true" />
                    <div>
                      <dt className="text-xs text-muted-foreground flex items-center">
                        Expected ARR
                        <MetricInfoIcon metricKey="arr" />
                      </dt>
                      <dd className="font-mono font-medium">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span data-testid={`text-arr-${score.scenario_key}`}>
                              {formatCurrency(score.expected_arr_18m)}
                            </span>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>{formatFullCurrency(score.expected_arr_18m)}</p>
                          </TooltipContent>
                        </Tooltip>
                        {!isBaseline && effectiveBaseline && effectiveBaseline.expected_arr_18m > 0 && (
                          <DeltaIndicator 
                            current={score.expected_arr_18m} 
                            baseline={effectiveBaseline.expected_arr_18m}
                            formatFn={(delta) => {
                              const pct = (delta / effectiveBaseline.expected_arr_18m * 100);
                              return `${pct.toFixed(1)}%`;
                            }}
                          />
                        )}
                      </dd>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0" aria-hidden="true" />
                    <div>
                      <dt className="text-xs text-muted-foreground flex items-center">
                        Downside Risk
                        <MetricInfoIcon metricKey="risk" />
                      </dt>
                      <dd className="font-mono font-medium">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span data-testid={`text-risk-${score.scenario_key}`}>
                              {formatCurrency(Math.abs(score.downside_risk_cvar))}
                            </span>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>P10 cash position: {formatFullCurrency(score.downside_risk_cvar)}</p>
                            <p className="text-xs text-muted-foreground">Lower is better (less downside)</p>
                          </TooltipContent>
                        </Tooltip>
                      </dd>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Coins className="h-4 w-4 text-purple-500 flex-shrink-0" aria-hidden="true" />
                    <div>
                      <dt className="text-xs text-muted-foreground flex items-center">
                        Dilution
                        <MetricInfoIcon metricKey="dilution" />
                      </dt>
                      <dd className="font-mono font-medium">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span data-testid={`text-dilution-${score.scenario_key}`}>
                              {score.dilution_pct.toFixed(1)}%
                            </span>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Ownership dilution from fundraising</p>
                            <p className="text-xs text-muted-foreground">Lower is better</p>
                          </TooltipContent>
                        </Tooltip>
                      </dd>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Gauge className="h-4 w-4 text-slate-500 flex-shrink-0" aria-hidden="true" />
                    <div>
                      <dt className="text-xs text-muted-foreground flex items-center">
                        Complexity
                        <MetricInfoIcon metricKey="complexity" />
                      </dt>
                      <dd className="font-mono font-medium">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span data-testid={`text-complexity-${score.scenario_key}`}>
                              {score.complexity_score.toFixed(1)}/10
                            </span>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Execution complexity score (0-10 scale)</p>
                            <p className="text-xs text-muted-foreground">Lower is easier to execute</p>
                          </TooltipContent>
                        </Tooltip>
                      </dd>
                    </div>
                  </div>
                </dl>

                <Collapsible open={isExpanded} onOpenChange={(open) => setExpandedCard(open ? score.scenario_key : null)}>
                  <CollapsibleTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full mt-3 text-xs"
                      onClick={(e) => e.stopPropagation()}
                      data-testid={`button-expand-${score.scenario_key}`}
                      aria-expanded={isExpanded}
                    >
                      {isExpanded ? (
                        <>
                          <ChevronUp className="h-3 w-3 mr-1" />
                          Hide Details
                        </>
                      ) : (
                        <>
                          <ChevronDown className="h-3 w-3 mr-1" />
                          Show Trade-off Analysis & Recommendations
                        </>
                      )}
                    </Button>
                  </CollapsibleTrigger>
                  
                  <CollapsibleContent>
                    <div className="mt-4 pt-4 border-t space-y-4">
                      <div className="grid md:grid-cols-2 gap-4">
                        <div>
                          <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                            <BarChart3 className="h-4 w-4 text-primary" />
                            Trade-off Visualization
                          </h4>
                          <TradeOffRadarChart 
                            score={score} 
                            baseline={effectiveBaseline}
                            allScores={rankings}
                          />
                          <p className="text-xs text-muted-foreground mt-2">
                            Higher values are better. Dashed line shows baseline for comparison.
                          </p>
                        </div>
                        
                        <div>
                          <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                            <Lightbulb className="h-4 w-4 text-yellow-500" />
                            Recommendation
                          </h4>
                          <div className="p-3 bg-muted/50 rounded-lg">
                            <p className="text-sm">{recommendation}</p>
                          </div>
                          
                          <h4 className="text-sm font-medium mt-4 mb-2">Component Breakdown</h4>
                          <ScoreBreakdownBar {...componentScores} weights={weights} />
                        </div>
                      </div>
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              </article>
            );
          })}
        </div>
        
        <div className="mt-6 p-4 bg-muted/50 rounded-lg">
          <div className="flex items-start gap-2">
            <Info className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
            <div className="text-xs text-muted-foreground space-y-1">
              <p>
                <strong>Current Weights:</strong> Survival ({(weights.survival * 100).toFixed(0)}%) + Growth ({(weights.growth * 100).toFixed(0)}%) + Risk ({(weights.downside_risk * 100).toFixed(0)}%) + Dilution ({(weights.dilution * 100).toFixed(0)}%) + Complexity ({(weights.complexity * 100).toFixed(0)}%)
              </p>
              <p>
                Relative changes are compared against the <strong>Baseline</strong> scenario. Green indicates improvement, red indicates decline.
              </p>
              <p>
                Use the <strong>Weights</strong> button to customize how metrics influence the composite score. Use <strong>Filters</strong> to narrow down scenarios.
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
