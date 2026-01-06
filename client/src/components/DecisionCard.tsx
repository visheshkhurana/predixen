import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { TrendingUp, AlertTriangle, Play, Check, X, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DecisionCardProps {
  rank: number;
  title: string;
  rationale: string;
  expectedImpact: {
    delta_survival_18m: number;
    delta_runway_p50: number;
  };
  risks: string[];
  keyAssumption: string;
  onValidate?: () => void;
  onSelect?: () => void;
  onAccept?: () => void;
  onReject?: () => void;
  status?: 'pending' | 'accepted' | 'rejected';
  testId?: string;
}

export function DecisionCard({
  rank,
  title,
  rationale,
  expectedImpact,
  risks,
  keyAssumption,
  onValidate,
  onSelect,
  onAccept,
  onReject,
  status = 'pending',
  testId = 'decision-card',
}: DecisionCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const getRankBadge = () => {
    switch (rank) {
      case 1:
        return (
          <Badge className="bg-emerald-500 text-white">
            #1 Recommended
          </Badge>
        );
      case 2:
        return (
          <Badge variant="secondary" className="bg-primary/20 text-primary">
            #2 Alternative
          </Badge>
        );
      case 3:
        return (
          <Badge variant="secondary" className="text-muted-foreground">
            #3 Option
          </Badge>
        );
      default:
        return null;
    }
  };
  
  return (
    <Card className="overflow-visible" data-testid={testId}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2">
            {getRankBadge()}
            <CardTitle className="text-lg">{title}</CardTitle>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">{rationale}</p>
        
        <div className="grid grid-cols-2 gap-4">
          <div className="p-3 rounded-lg bg-secondary">
            <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
              <TrendingUp className="h-3 w-3" />
              <span>Survival Impact (18m)</span>
            </div>
            <span className="text-lg font-mono font-semibold text-emerald-400">
              {expectedImpact.delta_survival_18m >= 0 ? '+' : ''}
              {expectedImpact.delta_survival_18m.toFixed(1)}%
            </span>
          </div>
          
          <div className="p-3 rounded-lg bg-secondary">
            <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
              <TrendingUp className="h-3 w-3" />
              <span>Runway Change</span>
            </div>
            <span className="text-lg font-mono font-semibold text-emerald-400">
              {expectedImpact.delta_runway_p50 >= 0 ? '+' : ''}
              {expectedImpact.delta_runway_p50.toFixed(1)} mo
            </span>
          </div>
        </div>
        
        {risks.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <AlertTriangle className="h-3 w-3" />
              <span>Risks & Assumptions</span>
            </div>
            <ul className="text-xs text-muted-foreground space-y-1">
              {risks.slice(0, 2).map((risk, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-muted-foreground">-</span>
                  <span>{risk}</span>
                </li>
              ))}
            </ul>
            <p className="text-xs italic text-muted-foreground">{keyAssumption}</p>
          </div>
        )}
        
        <div className="flex items-center gap-2 pt-2 flex-wrap">
          {status === 'pending' && (
            <>
              {onAccept && (
                <Button size="sm" onClick={onAccept} data-testid={`${testId}-accept`}>
                  <Check className="h-3 w-3 mr-1" />
                  Accept
                </Button>
              )}
              {onReject && (
                <Button variant="outline" size="sm" onClick={onReject} data-testid={`${testId}-reject`}>
                  <X className="h-3 w-3 mr-1" />
                  Reject
                </Button>
              )}
              {onValidate && (
                <Button variant="ghost" size="sm" onClick={onValidate} data-testid={`${testId}-validate`}>
                  <Play className="h-3 w-3 mr-1" />
                  Simulate
                </Button>
              )}
            </>
          )}
          {status === 'accepted' && (
            <Badge className="bg-emerald-500/20 text-emerald-400">
              <Check className="h-3 w-3 mr-1" />
              Accepted
            </Badge>
          )}
          {status === 'rejected' && (
            <Badge variant="secondary" className="text-muted-foreground">
              <X className="h-3 w-3 mr-1" />
              Rejected
            </Badge>
          )}
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => setIsExpanded(!isExpanded)}
            className="ml-auto"
            data-testid={`${testId}-expand`}
          >
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </div>
        
        {isExpanded && (
          <div className="pt-3 mt-3 border-t border-border space-y-3">
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">Full Rationale</p>
              <p className="text-sm">{rationale}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">Key Assumption</p>
              <p className="text-sm italic">{keyAssumption}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">All Risks</p>
              <ul className="text-sm space-y-1">
                {risks.map((risk, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <AlertTriangle className="h-3 w-3 mt-0.5 text-amber-500 flex-shrink-0" />
                    <span>{risk}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
