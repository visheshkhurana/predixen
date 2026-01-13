import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Trophy, TrendingUp, Shield, AlertTriangle, Coins } from 'lucide-react';

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
}

interface DecisionRankingTableProps {
  rankings: DecisionScore[];
  onSelectScenario?: (scenarioKey: string) => void;
}

function formatCurrency(value: number): string {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  } else if (value >= 1000) {
    return `$${(value / 1000).toFixed(0)}K`;
  }
  return `$${value.toFixed(0)}`;
}

function getRankBadge(rank: number) {
  switch (rank) {
    case 1:
      return (
        <Badge className="bg-yellow-500/20 text-yellow-400">
          <Trophy className="h-3 w-3 mr-1" />
          Best
        </Badge>
      );
    case 2:
      return (
        <Badge className="bg-slate-400/20 text-slate-300">
          2nd
        </Badge>
      );
    case 3:
      return (
        <Badge className="bg-amber-600/20 text-amber-400">
          3rd
        </Badge>
      );
    default:
      return (
        <Badge variant="outline">
          #{rank}
        </Badge>
      );
  }
}

export function DecisionRankingTable({ rankings, onSelectScenario }: DecisionRankingTableProps) {
  if (!rankings || rankings.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Trophy className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">
            No decision rankings available. Run a multi-scenario simulation first.
          </p>
        </CardContent>
      </Card>
    );
  }
  
  const sortedRankings = [...rankings].sort((a, b) => a.rank - b.rank);
  
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Decision Ranking</CardTitle>
        <CardDescription>
          Scenarios ranked by composite score (survival, growth, risk, dilution, complexity)
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {sortedRankings.map((score) => (
            <div
              key={score.scenario_key}
              className={`p-4 rounded-lg border hover-elevate cursor-pointer transition-colors ${
                score.rank === 1 ? 'border-primary/50 bg-primary/5' : ''
              }`}
              onClick={() => onSelectScenario?.(score.scenario_key)}
              data-testid={`ranking-card-${score.scenario_key}`}
            >
              <div className="flex items-center justify-between gap-4 mb-3 flex-wrap">
                <div className="flex items-center gap-3">
                  {getRankBadge(score.rank)}
                  <span className="font-medium">{score.scenario_name}</span>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">Composite Score</p>
                  <p className="text-lg font-mono font-bold text-primary">
                    {(score.composite_score * 100).toFixed(0)}
                  </p>
                </div>
              </div>
              
              <Progress 
                value={score.composite_score * 100} 
                className="h-2 mb-4"
              />
              
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm">
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4 text-emerald-500" />
                  <div>
                    <p className="text-xs text-muted-foreground">Survival 18m</p>
                    <p className="font-mono font-medium">
                      {(score.survival_18m_prob * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-blue-500" />
                  <div>
                    <p className="text-xs text-muted-foreground">Expected ARR</p>
                    <p className="font-mono font-medium">
                      {formatCurrency(score.expected_arr_18m)}
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                  <div>
                    <p className="text-xs text-muted-foreground">Downside Risk</p>
                    <p className="font-mono font-medium">
                      {formatCurrency(score.downside_risk_cvar)}
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <Coins className="h-4 w-4 text-purple-500" />
                  <div>
                    <p className="text-xs text-muted-foreground">Dilution</p>
                    <p className="font-mono font-medium">
                      {(score.dilution_pct * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>
                
                <div>
                  <p className="text-xs text-muted-foreground">Complexity</p>
                  <p className="font-mono font-medium">
                    {score.complexity_score.toFixed(1)}/10
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
        
        <div className="mt-6 p-4 bg-muted/50 rounded-lg">
          <p className="text-xs text-muted-foreground">
            <strong>Scoring Weights:</strong> Survival (30%) + Growth (25%) + Downside Risk (20%) + Dilution (15%) + Complexity (10%)
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
