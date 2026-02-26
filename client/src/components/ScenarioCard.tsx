import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { RiskGauge } from '@/components/RiskGauge';
import { cn } from '@/lib/utils';
import { useCurrency } from '@/hooks/useCurrency';
import {
  ChevronDown,
  ChevronUp,
  TrendingUp,
  TrendingDown,
  Tag,
  Scissors,
  DollarSign,
  Clock,
  Target,
  BarChart3,
  GripVertical,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
} from 'recharts';

interface ScenarioCardProps {
  id: string;
  name: string;
  runwayP50: number;
  runwayP10?: number;
  runwayP90?: number;
  survivalRate: number;
  endCash?: number;
  monthlyBurn?: number;
  assumptions?: {
    pricing_change_pct?: number;
    growth_uplift_pct?: number;
    burn_reduction_pct?: number;
    churn_change_pct?: number;
    cac_change_pct?: number;
    fundraise_amount?: number;
    fundraise_month?: number;
  };
  tags?: string[];
  presetUsed?: string;
  cashProjection?: number[];
  isBaseline?: boolean;
  isBest?: boolean;
  meetsBenchmark?: boolean;
  onSelect?: () => void;
  onDragStart?: () => void;
  draggable?: boolean;
  testId?: string;
}

export function ScenarioCard({
  id,
  name,
  runwayP50,
  runwayP10,
  runwayP90,
  survivalRate,
  endCash,
  monthlyBurn,
  assumptions,
  tags = [],
  presetUsed,
  cashProjection,
  isBaseline = false,
  isBest = false,
  meetsBenchmark = false,
  onSelect,
  onDragStart,
  draggable = false,
  testId,
}: ScenarioCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const { format: formatCurrency } = useCurrency();
  
  const miniChartData = cashProjection?.map((cash, index) => ({
    month: index + 1,
    cash,
  })) || Array.from({ length: 18 }, (_, i) => ({
    month: i + 1,
    cash: Math.max(0, 500000 - (30000 * (i + 1)) + (runwayP50 > 12 ? 10000 * i : 0)),
  }));
  
  const AssumptionItem = ({ icon: Icon, label, value, positive = true }: { 
    icon: any; 
    label: string; 
    value: string; 
    positive?: boolean;
  }) => (
    <div className="flex items-center gap-2 text-sm">
      <Icon className={cn('h-4 w-4', positive ? 'text-emerald-500' : 'text-amber-500')} />
      <span className="text-muted-foreground">{label}:</span>
      <span className="font-mono font-medium">{value}</span>
    </div>
  );
  
  return (
    <Card
      className={cn(
        'transition-all hover-elevate cursor-pointer',
        isBaseline && 'border-blue-500/30 bg-blue-500/5',
        isBest && 'border-amber-500/30 bg-amber-500/5',
        meetsBenchmark && 'border-emerald-500/30',
        !meetsBenchmark && survivalRate < 0.5 && 'border-red-500/30'
      )}
      data-testid={testId || `scenario-card-${id}`}
    >
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2">
              {draggable && (
                <GripVertical
                  className="h-5 w-5 text-muted-foreground cursor-grab"
                  onMouseDown={onDragStart}
                />
              )}
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <CardTitle className="text-base">{name}</CardTitle>
                  {isBaseline && <Badge variant="outline" className="text-xs">Baseline</Badge>}
                  {isBest && <Badge className="text-xs bg-amber-500">Best</Badge>}
                  {meetsBenchmark && <Badge variant="outline" className="text-xs border-emerald-500 text-emerald-600">Meets Target</Badge>}
                </div>
                {presetUsed && (
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Preset: {presetUsed}
                  </p>
                )}
              </div>
            </div>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </CollapsibleTrigger>
          </div>
        </CardHeader>
        
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
                <Clock className="h-3 w-3" />
                Runway
              </div>
              <p className="text-2xl font-mono font-bold">
                {runwayP50 >= 900 ? 'Sustainable' : runwayP50.toFixed(1)}
                {runwayP50 < 900 && <span className="text-sm text-muted-foreground ml-1">mo</span>}
              </p>
              {(runwayP10 || runwayP90) && (
                <p className="text-xs text-muted-foreground">
                  Range: {runwayP10 != null ? (runwayP10 >= 900 ? '∞' : runwayP10.toFixed(0)) : '?'} - {runwayP90 != null ? (runwayP90 >= 900 ? '∞' : runwayP90.toFixed(0)) : '?'} months
                </p>
              )}
            </div>
            
            <div>
              <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
                <Target className="h-3 w-3" />
                Survival
              </div>
              <RiskGauge survivalProbability={survivalRate} size="sm" showLabel={false} />
            </div>
          </div>
          
          <div className="h-16">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={miniChartData} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id={`gradient-${id}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="cash"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2}
                  fill={`url(#gradient-${id})`}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          
          {tags.length > 0 && (
            <div className="flex gap-1 flex-wrap">
              {tags.map((tag) => (
                <Badge key={tag} variant="outline" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>
          )}
          
          <CollapsibleContent className="space-y-4">
            <div className="pt-2 border-t space-y-2">
              <p className="text-sm font-medium">Key Assumptions</p>
              <div className="grid grid-cols-2 gap-2">
                {assumptions?.pricing_change_pct !== undefined && assumptions.pricing_change_pct !== 0 && (
                  <AssumptionItem
                    icon={Tag}
                    label="Pricing"
                    value={`${assumptions.pricing_change_pct > 0 ? '+' : ''}${assumptions.pricing_change_pct}%`}
                    positive={assumptions.pricing_change_pct > 0}
                  />
                )}
                {assumptions?.growth_uplift_pct !== undefined && assumptions.growth_uplift_pct !== 0 && (
                  <AssumptionItem
                    icon={TrendingUp}
                    label="Growth"
                    value={`${assumptions.growth_uplift_pct > 0 ? '+' : ''}${assumptions.growth_uplift_pct}%`}
                    positive={assumptions.growth_uplift_pct > 0}
                  />
                )}
                {assumptions?.burn_reduction_pct !== undefined && assumptions.burn_reduction_pct !== 0 && (
                  <AssumptionItem
                    icon={Scissors}
                    label={assumptions.burn_reduction_pct < 0 ? "Burn Increase" : "Burn Cut"}
                    value={assumptions.burn_reduction_pct < 0 ? `+${Math.abs(assumptions.burn_reduction_pct)}%` : `${assumptions.burn_reduction_pct}%`}
                    positive={assumptions.burn_reduction_pct > 0}
                  />
                )}
                {assumptions?.fundraise_amount !== undefined && assumptions.fundraise_amount > 0 && (
                  <AssumptionItem
                    icon={DollarSign}
                    label="Fundraise"
                    value={formatCurrency(assumptions.fundraise_amount)}
                    positive
                  />
                )}
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4 pt-2 border-t">
              <div>
                <p className="text-xs text-muted-foreground">Projected End Cash</p>
                <p className="text-lg font-mono font-semibold">{formatCurrency(endCash)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Monthly Burn</p>
                <p className="text-lg font-mono font-semibold">{formatCurrency(monthlyBurn)}</p>
              </div>
            </div>
            
            {onSelect && (
              <Button onClick={onSelect} className="w-full" data-testid={`button-select-${id}`}>
                <BarChart3 className="h-4 w-4 mr-2" />
                View Full Analysis
              </Button>
            )}
          </CollapsibleContent>
        </CardContent>
      </Collapsible>
    </Card>
  );
}
