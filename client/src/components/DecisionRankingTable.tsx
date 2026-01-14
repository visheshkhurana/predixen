import { useState, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { 
  Trophy, TrendingUp, TrendingDown, Shield, AlertTriangle, Coins, 
  Info, ArrowUpRight, ArrowDownRight, Minus, SlidersHorizontal, 
  Gauge, ChevronDown, ChevronUp
} from 'lucide-react';

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

const SCORING_WEIGHTS = {
  survival: 0.30,
  growth: 0.25,
  downside_risk: 0.20,
  dilution: 0.15,
  complexity: 0.10
};

function formatCurrency(value: number): string {
  const absValue = Math.abs(value);
  if (absValue >= 1000000) {
    return `$${(value / 1000000).toFixed(1)} M`;
  } else if (absValue >= 1000) {
    return `$${(value / 1000).toFixed(0)} K`;
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

function ScoreBreakdownBar({ 
  survivalScore, 
  growthScore, 
  riskScore, 
  dilutionScore, 
  complexityScore 
}: {
  survivalScore: number;
  growthScore: number;
  riskScore: number;
  dilutionScore: number;
  complexityScore: number;
}) {
  const segments = [
    { label: 'Survival', value: survivalScore, color: 'bg-emerald-500', weight: SCORING_WEIGHTS.survival },
    { label: 'Growth', value: growthScore, color: 'bg-blue-500', weight: SCORING_WEIGHTS.growth },
    { label: 'Risk', value: riskScore, color: 'bg-amber-500', weight: SCORING_WEIGHTS.downside_risk },
    { label: 'Dilution', value: dilutionScore, color: 'bg-purple-500', weight: SCORING_WEIGHTS.dilution },
    { label: 'Complexity', value: complexityScore, color: 'bg-slate-500', weight: SCORING_WEIGHTS.complexity },
  ];

  return (
    <div className="space-y-2">
      <div className="flex h-3 rounded-full overflow-hidden bg-muted">
        {segments.map((seg, idx) => (
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

export function DecisionRankingTable({ 
  rankings, 
  baselineKey,
  onSelectScenario,
  testId = 'decision-ranking'
}: DecisionRankingTableProps) {
  const [sortBy, setSortBy] = useState<SortField>('composite_score');
  const [sortDesc, setSortDesc] = useState(true);
  const [expandedCard, setExpandedCard] = useState<string | null>(null);

  const baseline = useMemo(() => {
    if (baselineKey) {
      return rankings.find(r => r.scenario_key === baselineKey);
    }
    return rankings.find(r => r.scenario_name.toLowerCase().includes('baseline')) || rankings[0];
  }, [rankings, baselineKey]);

  const sortedRankings = useMemo(() => {
    const sorted = [...rankings].sort((a, b) => {
      let aVal = a[sortBy];
      let bVal = b[sortBy];
      
      if (sortBy === 'downside_risk_cvar' || sortBy === 'dilution_pct' || sortBy === 'complexity_score') {
        return sortDesc ? aVal - bVal : bVal - aVal;
      }
      
      return sortDesc ? bVal - aVal : aVal - bVal;
    });
    return sorted;
  }, [rankings, sortBy, sortDesc]);

  const computeComponentScores = (score: DecisionScore) => {
    if (score.survival_component !== undefined) {
      return {
        survivalScore: score.survival_component,
        growthScore: score.growth_component || 0,
        riskScore: score.risk_component || 0,
        dilutionScore: score.dilution_component || 0,
        complexityScore: score.complexity_component || 0,
      };
    }
    const survivalScore = Math.min(1, score.survival_18m_prob / 100) * SCORING_WEIGHTS.survival;
    const maxArr = Math.max(...rankings.map(r => r.expected_arr_18m));
    const growthScore = (maxArr > 0 ? score.expected_arr_18m / maxArr : 0) * SCORING_WEIGHTS.growth;
    const maxRisk = Math.max(...rankings.map(r => Math.abs(r.downside_risk_cvar)));
    const riskScore = (maxRisk > 0 ? 1 - Math.abs(score.downside_risk_cvar) / maxRisk : 1) * SCORING_WEIGHTS.downside_risk;
    const dilutionScore = (1 - (score.dilution_pct / 100)) * SCORING_WEIGHTS.dilution;
    const complexityScore = (1 - (score.complexity_score / 10)) * SCORING_WEIGHTS.complexity;
    
    return { survivalScore, growthScore, riskScore, dilutionScore, complexityScore };
  };

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
            <CardTitle className="text-lg">Decision Ranking</CardTitle>
            <CardDescription>
              Scenarios ranked by composite score with relative comparisons
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
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
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4" role="list" aria-label="Scenario rankings">
          {sortedRankings.map((score) => {
            const isBaseline = score.scenario_key === baseline?.scenario_key;
            const isExpanded = expandedCard === score.scenario_key;
            const componentScores = computeComponentScores(score);
            
            return (
              <article
                key={score.scenario_key}
                className={`p-4 rounded-lg border hover-elevate cursor-pointer transition-colors ${
                  score.rank === 1 ? 'border-primary/50 bg-primary/5' : ''
                } ${isBaseline ? 'ring-2 ring-muted' : ''}`}
                onClick={() => onSelectScenario?.(score.scenario_key)}
                data-testid={`ranking-card-${score.scenario_key}`}
                role="listitem"
                aria-label={`${score.scenario_name}, rank ${score.rank}`}
              >
                <div className="flex items-center justify-between gap-4 mb-3 flex-wrap">
                  <div className="flex items-center gap-3">
                    {getRankBadge(score.rank)}
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
                              {(score.composite_score * 100).toFixed(0)}
                            </p>
                          </div>
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-80" align="end">
                        <div className="space-y-3">
                          <h4 className="font-medium text-sm">Score Breakdown</h4>
                          <p className="text-xs text-muted-foreground">
                            Composite = Survival (30%) + Growth (25%) + Risk (20%) + Dilution (15%) + Complexity (10%)
                          </p>
                          <ScoreBreakdownBar {...componentScores} />
                          <div className="pt-2 border-t">
                            <p className="text-xs text-muted-foreground">
                              Final Score: <span className="font-mono font-bold">{(score.composite_score * 100).toFixed(1)}</span> / 100
                            </p>
                          </div>
                        </div>
                      </PopoverContent>
                    </Popover>
                  </div>
                </div>
                
                <Progress 
                  value={Math.min(100, score.composite_score * 100)} 
                  className="h-2 mb-4"
                  aria-label={`Composite score: ${(score.composite_score * 100).toFixed(0)}%`}
                />
                
                <dl className="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm">
                  <div className="flex items-center gap-2">
                    <Shield className="h-4 w-4 text-emerald-500 flex-shrink-0" aria-hidden="true" />
                    <div>
                      <dt className="text-xs text-muted-foreground">Survival 18m</dt>
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
                        {!isBaseline && baseline && (
                          <DeltaIndicator 
                            current={score.survival_18m_prob} 
                            baseline={baseline.survival_18m_prob}
                            suffix="%"
                          />
                        )}
                      </dd>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-blue-500 flex-shrink-0" aria-hidden="true" />
                    <div>
                      <dt className="text-xs text-muted-foreground">Expected ARR</dt>
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
                        {!isBaseline && baseline && baseline.expected_arr_18m > 0 && (
                          <DeltaIndicator 
                            current={score.expected_arr_18m} 
                            baseline={baseline.expected_arr_18m}
                            formatFn={(delta) => {
                              const pct = (delta / baseline.expected_arr_18m * 100);
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
                      <dt className="text-xs text-muted-foreground">Downside Risk</dt>
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
                      <dt className="text-xs text-muted-foreground">Dilution</dt>
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
                      <dt className="text-xs text-muted-foreground">Complexity</dt>
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

                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full mt-3 text-xs"
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedCard(isExpanded ? null : score.scenario_key);
                  }}
                  data-testid={`button-expand-${score.scenario_key}`}
                  aria-expanded={isExpanded}
                  aria-controls={`breakdown-${score.scenario_key}`}
                >
                  {isExpanded ? (
                    <>
                      <ChevronUp className="h-3 w-3 mr-1" />
                      Hide Score Breakdown
                    </>
                  ) : (
                    <>
                      <ChevronDown className="h-3 w-3 mr-1" />
                      Show Score Breakdown
                    </>
                  )}
                </Button>

                {isExpanded && (
                  <div 
                    id={`breakdown-${score.scenario_key}`}
                    className="mt-4 pt-4 border-t"
                  >
                    <h4 className="text-sm font-medium mb-3">Component Score Breakdown</h4>
                    <ScoreBreakdownBar {...componentScores} />
                  </div>
                )}
              </article>
            );
          })}
        </div>
        
        <div className="mt-6 p-4 bg-muted/50 rounded-lg">
          <div className="flex items-start gap-2">
            <Info className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
            <div className="text-xs text-muted-foreground space-y-1">
              <p>
                <strong>Scoring Weights:</strong> Survival (30%) + Growth (25%) + Downside Risk (20%) + Dilution (15%) + Complexity (10%)
              </p>
              <p>
                Relative changes are compared against the <strong>Baseline</strong> scenario. Green indicates improvement, red indicates decline.
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
