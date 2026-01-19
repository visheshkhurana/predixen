import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { HelpCircle, Calculator, TrendingUp, TrendingDown, Target } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ScenarioRunwayToggleProps {
  currentRunway: number | null;
  currentBurn: number | null;
  cashBalance: number | null;
  currency?: string;
}

type ScenarioType = 'current' | 'growth' | 'costcut';

interface Scenario {
  id: ScenarioType;
  name: string;
  description: string;
  icon: React.ReactNode;
  burnMultiplier: number;
  color: string;
}

const SCENARIOS: Scenario[] = [
  {
    id: 'current',
    name: 'Current Burn',
    description: 'Based on current spending',
    icon: <Target className="h-4 w-4" />,
    burnMultiplier: 1.0,
    color: 'bg-muted text-foreground',
  },
  {
    id: 'growth',
    name: 'Aggressive Growth',
    description: '+40% burn for faster growth',
    icon: <TrendingUp className="h-4 w-4" />,
    burnMultiplier: 1.4,
    color: 'bg-emerald-500/20 text-emerald-400',
  },
  {
    id: 'costcut',
    name: 'Cost Reduction',
    description: '-30% burn, extend runway',
    icon: <TrendingDown className="h-4 w-4" />,
    burnMultiplier: 0.7,
    color: 'bg-amber-500/20 text-amber-400',
  },
];

export function ScenarioRunwayToggle({ 
  currentRunway, 
  currentBurn, 
  cashBalance,
  currency = 'USD' 
}: ScenarioRunwayToggleProps) {
  const [activeScenario, setActiveScenario] = useState<ScenarioType>('current');

  const calculateRunway = (scenario: Scenario): number | null => {
    if (cashBalance == null || currentBurn == null || currentBurn <= 0) return null;
    const adjustedBurn = currentBurn * scenario.burnMultiplier;
    return cashBalance / adjustedBurn;
  };

  const formatRunway = (months: number | null): string => {
    if (months == null) return 'N/A';
    if (months > 36) return '36+ mo';
    return `${months.toFixed(1)} mo`;
  };

  const formatCurrency = (value: number | null): string => {
    if (value == null) return 'N/A';
    if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `${(value / 1000).toFixed(0)}K`;
    return value.toFixed(0);
  };

  const getRunwayVariant = (months: number | null): 'success' | 'warning' | 'danger' | 'default' => {
    if (months == null) return 'default';
    if (months >= 18) return 'success';
    if (months >= 12) return 'default';
    if (months >= 6) return 'warning';
    return 'danger';
  };

  const activeScenarioData = SCENARIOS.find(s => s.id === activeScenario)!;
  const calculatedRunway = calculateRunway(activeScenarioData);
  const adjustedBurn = currentBurn ? currentBurn * activeScenarioData.burnMultiplier : null;

  return (
    <Card className="overflow-visible">
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Calculator className="h-4 w-4 text-primary" />
          Scenario-Based Runway
          <Tooltip>
            <TooltipTrigger asChild>
              <button type="button" className="p-0.5">
                <HelpCircle className="h-3 w-3 text-muted-foreground" />
              </button>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p className="text-sm">
                Toggle between scenarios to see how different spending strategies affect your runway.
              </p>
            </TooltipContent>
          </Tooltip>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Scenario Toggles */}
        <div className="flex flex-wrap gap-2">
          {SCENARIOS.map((scenario) => (
            <Button
              key={scenario.id}
              variant={activeScenario === scenario.id ? 'default' : 'outline'}
              size="sm"
              onClick={() => setActiveScenario(scenario.id)}
              className={cn(
                'flex items-center gap-2',
                activeScenario === scenario.id && scenario.id === 'growth' && 'bg-emerald-600 hover:bg-emerald-700',
                activeScenario === scenario.id && scenario.id === 'costcut' && 'bg-amber-600 hover:bg-amber-700'
              )}
              data-testid={`scenario-${scenario.id}`}
            >
              {scenario.icon}
              {scenario.name}
            </Button>
          ))}
        </div>

        {/* Results */}
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 rounded-lg bg-muted/30 text-center">
            <p className="text-sm text-muted-foreground mb-1">Runway</p>
            <p 
              className={cn(
                'text-3xl font-bold font-mono',
                getRunwayVariant(calculatedRunway) === 'success' && 'text-emerald-500',
                getRunwayVariant(calculatedRunway) === 'warning' && 'text-amber-500',
                getRunwayVariant(calculatedRunway) === 'danger' && 'text-red-500'
              )}
              data-testid="scenario-runway-result"
              data-scenario={activeScenario}
              data-runway-value={calculatedRunway}
            >
              {formatRunway(calculatedRunway)}
            </p>
            {calculatedRunway !== currentRunway && currentRunway && (
              <Badge variant="secondary" className="mt-1 text-xs">
                {calculatedRunway && calculatedRunway > currentRunway ? '+' : ''}{calculatedRunway && currentRunway ? (calculatedRunway - currentRunway).toFixed(1) : 0} mo
              </Badge>
            )}
          </div>
          <div className="p-4 rounded-lg bg-muted/30 text-center">
            <p className="text-sm text-muted-foreground mb-1">Monthly Burn</p>
            <p className="text-3xl font-bold font-mono" data-testid="scenario-burn-result">
              ${formatCurrency(adjustedBurn)}
            </p>
            {adjustedBurn !== currentBurn && currentBurn && (
              <Badge variant="secondary" className="mt-1 text-xs">
                {activeScenarioData.burnMultiplier > 1 ? '+' : ''}{((activeScenarioData.burnMultiplier - 1) * 100).toFixed(0)}%
              </Badge>
            )}
          </div>
        </div>

        <p className="text-xs text-muted-foreground text-center">
          {activeScenarioData.description}
        </p>
      </CardContent>
    </Card>
  );
}
