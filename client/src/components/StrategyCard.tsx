import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Minus, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

export interface StrategyPreview {
  id: string;
  name: string;
  description: string;
  narrative: string;
  icon: React.ReactNode;
  projectedRunway: number;
  survivalProbability: number;
  arrGrowth: number;
  burnChange: number;
  assumptions: string[];
  riskLevel: 'low' | 'medium' | 'high';
  recommended?: boolean;
}

interface StrategyCardProps {
  strategy: StrategyPreview;
  currentRunway?: number;
  onSimulate: (strategyId: string) => void;
  isSelected?: boolean;
  isLoading?: boolean;
  className?: string;
}

function getRiskBadgeColor(risk: 'low' | 'medium' | 'high') {
  switch (risk) {
    case 'low': return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20';
    case 'medium': return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
    case 'high': return 'bg-red-500/10 text-red-500 border-red-500/20';
  }
}

function RunwayChange({ current, projected }: { current?: number; projected: number }) {
  if (!current) return null;
  const change = projected - current;
  const isPositive = change > 0;
  const isNeutral = Math.abs(change) < 0.5;
  
  return (
    <div className={cn(
      "flex items-center gap-1 text-xs font-medium",
      isNeutral ? "text-muted-foreground" : isPositive ? "text-emerald-500" : "text-red-500"
    )}>
      {isNeutral ? (
        <Minus className="w-3 h-3" />
      ) : isPositive ? (
        <TrendingUp className="w-3 h-3" />
      ) : (
        <TrendingDown className="w-3 h-3" />
      )}
      {isNeutral ? 'No change' : `${isPositive ? '+' : ''}${change.toFixed(1)}mo`}
    </div>
  );
}

export function StrategyCard({
  strategy,
  currentRunway,
  onSimulate,
  isSelected,
  isLoading,
  className,
}: StrategyCardProps) {
  return (
    <Card
      className={cn(
        "relative transition-all cursor-pointer hover-elevate",
        isSelected && "ring-2 ring-primary border-primary",
        className
      )}
      onClick={() => !isLoading && onSimulate(strategy.id)}
      data-testid={`strategy-card-${strategy.id}`}
    >
      {strategy.recommended && (
        <Badge 
          className="absolute -top-2 -right-2 bg-primary text-primary-foreground text-xs"
          data-testid="badge-recommended"
        >
          Recommended
        </Badge>
      )}
      
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <CardTitle className="text-base flex items-center gap-2">
              {strategy.icon}
              {strategy.name}
            </CardTitle>
            <CardDescription className="mt-1 text-sm">
              {strategy.description}
            </CardDescription>
          </div>
          <Badge 
            variant="outline" 
            className={cn("text-xs capitalize", getRiskBadgeColor(strategy.riskLevel))}
          >
            {strategy.riskLevel} risk
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        <p className="text-xs text-muted-foreground italic">
          "{strategy.narrative}"
        </p>
        
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Runway</div>
            <div className="flex items-baseline gap-2">
              <span className="text-lg font-semibold">{Number(strategy.projectedRunway).toFixed(1)}mo</span>
              <RunwayChange current={currentRunway} projected={strategy.projectedRunway} />
            </div>
          </div>
          
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Survival (18m)</div>
            <div className="text-lg font-semibold">{Number(strategy.survivalProbability).toFixed(1)}%</div>
          </div>
          
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">ARR Growth</div>
            <div className={cn(
              "text-lg font-semibold",
              strategy.arrGrowth > 0 ? "text-emerald-500" : "text-muted-foreground"
            )}>
              {strategy.arrGrowth > 0 ? '+' : ''}{Number(strategy.arrGrowth).toFixed(0)}%
            </div>
          </div>
          
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Burn Change</div>
            <div className={cn(
              "text-lg font-semibold",
              strategy.burnChange < 0 ? "text-emerald-500" : strategy.burnChange > 0 ? "text-red-500" : "text-muted-foreground"
            )}>
              {strategy.burnChange > 0 ? '+' : ''}{Number(strategy.burnChange).toFixed(0)}%
            </div>
          </div>
        </div>
        
        <div className="pt-2 border-t border-border/50">
          <div className="text-xs text-muted-foreground mb-2">Key assumptions:</div>
          <ul className="space-y-1">
            {strategy.assumptions.slice(0, 3).map((assumption, idx) => (
              <li key={idx} className="text-xs flex items-start gap-2">
                <span className="w-1 h-1 rounded-full bg-muted-foreground/50 mt-1.5 shrink-0" />
                {assumption}
              </li>
            ))}
          </ul>
        </div>
        
        <Button
          onClick={(e) => { e.stopPropagation(); onSimulate(strategy.id); }}
          disabled={isLoading}
          className="w-full gap-2"
          data-testid={`button-simulate-${strategy.id}`}
        >
          {isLoading ? 'Simulating...' : 'Simulate This Strategy'}
          <ArrowRight className="w-4 h-4" />
        </Button>
      </CardContent>
    </Card>
  );
}
