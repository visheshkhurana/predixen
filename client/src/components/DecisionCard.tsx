import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { TrendingUp, AlertTriangle, Clock, Link2, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

export type DecisionStatus = 'pending' | 'adopted' | 'deferred' | 'rejected';

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
  status?: DecisionStatus;
  onStatusChange?: (status: DecisionStatus) => void;
  isNew?: boolean;
  isChanged?: boolean;
  testId?: string;
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
  status = 'pending',
  onStatusChange,
  isNew = false,
  isChanged = false,
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

  const getStatusBadge = () => {
    switch (status) {
      case 'adopted':
        return (
          <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
            Adopted
          </Badge>
        );
      case 'deferred':
        return (
          <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30">
            Deferred
          </Badge>
        );
      case 'rejected':
        return (
          <Badge variant="secondary" className="text-muted-foreground">
            Rejected
          </Badge>
        );
      default:
        return null;
    }
  };

  const allRisks = detailedRiskFactors.length > 0 ? detailedRiskFactors : risks;

  return (
    <Card 
      className={cn(
        "overflow-visible relative",
        isNew && "ring-2 ring-emerald-500/50",
        isChanged && "ring-2 ring-amber-500/50"
      )} 
      data-testid={testId}
    >
      {(isNew || isChanged) && (
        <div className="absolute -top-2 -right-2 z-10">
          <Badge 
            className={cn(
              "flex items-center gap-1",
              isNew ? "bg-emerald-500 text-white" : "bg-amber-500 text-white"
            )}
          >
            <Sparkles className="h-3 w-3" />
            {isNew ? 'New' : 'Updated'}
          </Badge>
        </div>
      )}
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            {getRankBadge()}
            {status !== 'pending' && getStatusBadge()}
          </div>
        </div>
        <CardTitle className="text-lg mt-2">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">{rationale}</p>
        
        <div className="grid grid-cols-2 gap-4">
          <div className="p-3 rounded-lg bg-secondary">
            <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
              <TrendingUp className="h-3 w-3" />
              <span>Survival Impact (18m)</span>
            </div>
            <span className={cn(
              "text-lg font-mono font-semibold",
              expectedImpact.delta_survival_18m >= 0 ? "text-emerald-400" : "text-red-400"
            )}>
              {expectedImpact.delta_survival_18m >= 0 ? '+' : ''}
              {expectedImpact.delta_survival_18m.toFixed(1)}%
            </span>
          </div>
          
          <div className="p-3 rounded-lg bg-secondary">
            <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
              <TrendingUp className="h-3 w-3" />
              <span>Runway Change</span>
            </div>
            <span className={cn(
              "text-lg font-mono font-semibold",
              expectedImpact.delta_runway_p50 >= 0 ? "text-emerald-400" : "text-red-400"
            )}>
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
          {onStatusChange && (
            <Select
              value={status}
              onValueChange={(value) => onStatusChange(value as DecisionStatus)}
            >
              <SelectTrigger 
                className="w-32 h-8 text-xs" 
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
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => setIsExpanded(!isExpanded)}
            className="ml-auto"
            data-testid={`${testId}-expand`}
          >
            {isExpanded ? (
              <>
                <span className="text-xs mr-1">Less</span>
                <ChevronUp className="h-4 w-4" />
              </>
            ) : (
              <>
                <span className="text-xs mr-1">More</span>
                <ChevronDown className="h-4 w-4" />
              </>
            )}
          </Button>
        </div>
        
        {isExpanded && (
          <div className="pt-3 mt-3 border-t border-border space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 rounded-lg bg-secondary/50">
                <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
                  <Clock className="h-3 w-3" />
                  <span>Time Horizon</span>
                </div>
                <p className="text-sm font-medium">{timeHorizon}</p>
              </div>
              
              <div className="p-3 rounded-lg bg-secondary/50">
                <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
                  <Link2 className="h-3 w-3" />
                  <span>Dependencies</span>
                </div>
                {dependencies.length > 0 ? (
                  <ul className="text-xs space-y-1">
                    {dependencies.map((dep, i) => (
                      <li key={i} className="flex items-start gap-1">
                        <span className="text-muted-foreground">•</span>
                        <span>{dep}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-muted-foreground">No dependencies</p>
                )}
              </div>
            </div>

            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">Impact Details</p>
              <div className="grid grid-cols-1 gap-2">
                <div className="p-3 rounded-lg bg-secondary/50">
                  <p className="text-xs text-muted-foreground mb-1">Runway Impact</p>
                  <p className="text-sm">
                    {runwayImpactDetails || `Expected to ${expectedImpact.delta_runway_p50 >= 0 ? 'extend' : 'reduce'} runway by ${Math.abs(expectedImpact.delta_runway_p50).toFixed(1)} months at P50 confidence level.`}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-secondary/50">
                  <p className="text-xs text-muted-foreground mb-1">Survival Probability</p>
                  <p className="text-sm">
                    {survivalImpactDetails || `18-month survival probability ${expectedImpact.delta_survival_18m >= 0 ? 'increases' : 'decreases'} by ${Math.abs(expectedImpact.delta_survival_18m).toFixed(1)} percentage points.`}
                  </p>
                </div>
              </div>
            </div>
            
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">Full Rationale</p>
              <p className="text-sm">{rationale}</p>
            </div>
            
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">Key Assumption</p>
              <p className="text-sm italic">{keyAssumption}</p>
            </div>
            
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">All Risk Factors</p>
              <ul className="text-sm space-y-2">
                {allRisks.map((risk, i) => (
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
