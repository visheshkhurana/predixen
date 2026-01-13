import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface RegimeDistribution {
  base: number;
  downturn: number;
  breakout: number;
}

interface RegimeDistributionChartProps {
  distribution: RegimeDistribution;
  scenarioName?: string;
}

const REGIME_COLORS = {
  base: 'hsl(199, 89%, 55%)',
  downturn: 'hsl(0, 84%, 60%)',
  breakout: 'hsl(142, 70%, 45%)',
};

const REGIME_LABELS = {
  base: 'Base',
  downturn: 'Downturn',
  breakout: 'Breakout',
};

const REGIME_DESCRIPTIONS = {
  base: 'Normal market conditions with standard volatility',
  downturn: 'Challenging conditions with reduced growth and higher churn',
  breakout: 'Favorable conditions with accelerated growth potential',
};

const REGIME_ICONS = {
  base: Minus,
  downturn: TrendingDown,
  breakout: TrendingUp,
};

export function RegimeDistributionChart({ distribution, scenarioName }: RegimeDistributionChartProps) {
  const data = [
    { name: 'Base', value: distribution.base, color: REGIME_COLORS.base },
    { name: 'Downturn', value: distribution.downturn, color: REGIME_COLORS.downturn },
    { name: 'Breakout', value: distribution.breakout, color: REGIME_COLORS.breakout },
  ].filter(d => d.value > 0);
  
  const total = distribution.base + distribution.downturn + distribution.breakout;
  
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Regime Distribution</CardTitle>
        <CardDescription>
          {scenarioName ? `Market regime mix for ${scenarioName}` : 'Expected market conditions over simulation horizon'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {data.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  formatter={(value: number) => `${((value / total) * 100).toFixed(1)}%`}
                  contentStyle={{
                    backgroundColor: 'hsl(222 40% 12%)',
                    border: '1px solid hsl(222 30% 18%)',
                    borderRadius: '8px',
                  }}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
          
          <div className="space-y-4">
            {Object.entries(REGIME_LABELS).map(([key, label]) => {
              const Icon = REGIME_ICONS[key as keyof typeof REGIME_ICONS];
              const percentage = total > 0 
                ? (distribution[key as keyof RegimeDistribution] / total) * 100 
                : 0;
              
              return (
                <div key={key} className="p-3 rounded-lg border">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <div className="flex items-center gap-2">
                      <Icon 
                        className="h-4 w-4" 
                        style={{ color: REGIME_COLORS[key as keyof typeof REGIME_COLORS] }} 
                      />
                      <span className="font-medium">{label}</span>
                    </div>
                    <Badge 
                      variant="outline"
                      style={{ borderColor: REGIME_COLORS[key as keyof typeof REGIME_COLORS] }}
                    >
                      {percentage.toFixed(1)}%
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {REGIME_DESCRIPTIONS[key as keyof typeof REGIME_DESCRIPTIONS]}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
