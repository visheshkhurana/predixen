import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Badge } from '@/components/ui/badge';
import { HelpCircle, Users, UserPlus, DollarSign } from 'lucide-react';
import { formatCurrencyAbbrev } from '@/lib/utils';

interface HeadcountPanelProps {
  headcount: number | null;
  plannedHires: number | null;
  revenuePerEmployee: number | null;
  currency?: string;
}

export function HeadcountPanel({ 
  headcount, 
  plannedHires, 
  revenuePerEmployee,
  currency = 'USD' 
}: HeadcountPanelProps) {
  const formatCurrency = (value: number | null) => {
    if (value == null) return 'N/A';
    return formatCurrencyAbbrev(value, currency);
  };

  // Revenue per employee benchmarks
  const getRpeVariant = (): 'success' | 'warning' | 'default' => {
    if (revenuePerEmployee == null) return 'default';
    if (revenuePerEmployee >= 15000) return 'success';  // $15k+ per employee/month is good
    if (revenuePerEmployee >= 8000) return 'default';
    return 'warning';
  };

  return (
    <Card className="overflow-visible">
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Users className="h-4 w-4 text-primary" />
          Headcount & Hiring
          <Tooltip>
            <TooltipTrigger asChild>
              <button type="button" className="p-0.5">
                <HelpCircle className="h-3 w-3 text-muted-foreground" />
              </button>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p className="text-sm">
                Current team size, planned hiring, and revenue efficiency per employee.
              </p>
            </TooltipContent>
          </Tooltip>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-3 rounded-lg bg-muted/30" data-testid="metric-headcount">
            <div className="flex items-center justify-center gap-1 text-muted-foreground mb-1">
              <Users className="h-3 w-3" />
              <span className="text-xs">Current</span>
            </div>
            <p className="text-2xl font-bold font-mono">{headcount ?? 'N/A'}</p>
            <p className="text-xs text-muted-foreground">employees</p>
          </div>
          
          <div className="text-center p-3 rounded-lg bg-muted/30" data-testid="metric-planned-hires">
            <div className="flex items-center justify-center gap-1 text-muted-foreground mb-1">
              <UserPlus className="h-3 w-3" />
              <span className="text-xs">Planned</span>
            </div>
            <p className="text-2xl font-bold font-mono text-emerald-500">+{plannedHires ?? 0}</p>
            <p className="text-xs text-muted-foreground">hires</p>
          </div>
          
          <div className="text-center p-3 rounded-lg bg-muted/30" data-testid="metric-rev-per-emp">
            <div className="flex items-center justify-center gap-1 text-muted-foreground mb-1">
              <DollarSign className="h-3 w-3" />
              <span className="text-xs">Rev/Emp</span>
            </div>
            <p className={`text-2xl font-bold font-mono ${
              getRpeVariant() === 'success' ? 'text-emerald-500' : 
              getRpeVariant() === 'warning' ? 'text-amber-500' : ''
            }`}>
              {formatCurrency(revenuePerEmployee)}
            </p>
            <p className="text-xs text-muted-foreground">monthly</p>
          </div>
        </div>

        {headcount && plannedHires && plannedHires > 0 && (
          <div className="mt-4 pt-4 border-t">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">After hiring:</span>
              <Badge variant="secondary">
                {headcount + plannedHires} employees ({((plannedHires / headcount) * 100).toFixed(0)}% growth)
              </Badge>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
