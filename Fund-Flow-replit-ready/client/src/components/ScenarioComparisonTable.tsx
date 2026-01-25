import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ArrowUp, ArrowDown, Minus } from 'lucide-react';

interface ScenarioData {
  id: number;
  name: string;
  runway_p50?: number;
  survival_18m?: number;
  end_cash?: number;
  monthly_burn?: number;
  tags?: string[];
}

interface ScenarioComparisonTableProps {
  scenarios: ScenarioData[];
  baselineId?: number;
  testId?: string;
}

export function ScenarioComparisonTable({ 
  scenarios, 
  baselineId,
  testId = 'comparison-table' 
}: ScenarioComparisonTableProps) {
  if (scenarios.length === 0) {
    return null;
  }

  const baseline = scenarios.find(s => s.id === baselineId) || scenarios[0];

  const formatCurrency = (value: number | undefined) => {
    if (value === undefined || value === null) return 'N/A';
    if (Math.abs(value) >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`;
    }
    return `$${(value / 1000).toFixed(0)}K`;
  };

  const getDelta = (current: number | undefined, base: number | undefined) => {
    if (current === undefined || base === undefined) return null;
    return current - base;
  };

  const DeltaIndicator = ({ delta, suffix = '', inverted = false }: { delta: number | null; suffix?: string; inverted?: boolean }) => {
    if (delta === null || delta === 0) {
      return <Minus className="h-3 w-3 text-muted-foreground inline ml-1" />;
    }
    const isPositive = inverted ? delta < 0 : delta > 0;
    return (
      <span className={`text-xs ml-1 ${isPositive ? 'text-emerald-500' : 'text-red-500'}`}>
        {isPositive ? <ArrowUp className="h-3 w-3 inline" /> : <ArrowDown className="h-3 w-3 inline" />}
        {Math.abs(delta).toFixed(1)}{suffix}
      </span>
    );
  };

  return (
    <Card data-testid={testId}>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Scenario Comparison</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Scenario</TableHead>
                <TableHead className="text-right">Runway (P50)</TableHead>
                <TableHead className="text-right">Survival 18m</TableHead>
                <TableHead className="text-right">End Cash</TableHead>
                <TableHead className="text-right">Monthly Burn</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {scenarios.map((scenario) => {
                const isBaseline = scenario.id === baseline?.id;
                return (
                  <TableRow 
                    key={scenario.id} 
                    className={isBaseline ? 'bg-muted/50' : ''}
                    data-testid={`comparison-row-${scenario.id}`}
                  >
                    <TableCell>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium">{scenario.name}</span>
                        {isBaseline && <Badge variant="secondary">Baseline</Badge>}
                        {scenario.tags?.map(tag => (
                          <Badge key={tag} variant="outline" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {scenario.runway_p50?.toFixed(1) || 'N/A'} mo
                      {!isBaseline && (
                        <DeltaIndicator 
                          delta={getDelta(scenario.runway_p50, baseline?.runway_p50)} 
                          suffix=" mo"
                        />
                      )}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {scenario.survival_18m?.toFixed(0) || 'N/A'}%
                      {!isBaseline && (
                        <DeltaIndicator 
                          delta={getDelta(scenario.survival_18m, baseline?.survival_18m)} 
                          suffix="%"
                        />
                      )}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {formatCurrency(scenario.end_cash)}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {formatCurrency(scenario.monthly_burn)}
                      {!isBaseline && (
                        <DeltaIndicator 
                          delta={getDelta(scenario.monthly_burn, baseline?.monthly_burn)} 
                          inverted={true}
                        />
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
