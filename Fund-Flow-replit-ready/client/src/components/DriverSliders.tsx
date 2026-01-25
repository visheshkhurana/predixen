import { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Play, RotateCcw, Info, AlertTriangle } from 'lucide-react';

interface DriverConfig {
  key: string;
  label: string;
  min: number;
  max: number;
  step: number;
  unit: string;
  description: string;
  category: 'growth' | 'costs' | 'efficiency';
}

const DRIVER_CONFIGS: DriverConfig[] = [
  { key: 'pricing_change_pct', label: 'Pricing Change', min: -50, max: 100, step: 5, unit: '%', description: 'Adjust your product pricing', category: 'growth' },
  { key: 'growth_uplift_pct', label: 'Growth Uplift', min: -30, max: 50, step: 5, unit: '%', description: 'Expected change in growth rate', category: 'growth' },
  { key: 'burn_reduction_pct', label: 'Burn Reduction', min: 0, max: 80, step: 5, unit: '%', description: 'Reduce monthly operating expenses', category: 'costs' },
  { key: 'gross_margin_delta_pct', label: 'Margin Improvement', min: -20, max: 30, step: 2, unit: '%', description: 'Change in gross margin', category: 'efficiency' },
  { key: 'churn_reduction_pct', label: 'Churn Reduction', min: 0, max: 50, step: 5, unit: '%', description: 'Reduce customer churn through initiatives', category: 'efficiency' },
];

interface DriverSlidersProps {
  initialValues?: Record<string, number>;
  onChange?: (values: Record<string, number>) => void;
  onSimulate?: (values: Record<string, number>) => void;
  isSimulating?: boolean;
  warnings?: Array<{ field: string; message: string; severity: string }>;
}

export function DriverSliders({
  initialValues = {},
  onChange,
  onSimulate,
  isSimulating = false,
  warnings = []
}: DriverSlidersProps) {
  const [values, setValues] = useState<Record<string, number>>(() => {
    const defaults: Record<string, number> = {};
    DRIVER_CONFIGS.forEach(config => {
      defaults[config.key] = initialValues[config.key] ?? 0;
    });
    return defaults;
  });

  useEffect(() => {
    onChange?.(values);
  }, [values, onChange]);

  const handleChange = (key: string, newValue: number[]) => {
    setValues(prev => ({ ...prev, [key]: newValue[0] }));
  };

  const handleReset = () => {
    const defaults: Record<string, number> = {};
    DRIVER_CONFIGS.forEach(config => {
      defaults[config.key] = 0;
    });
    setValues(defaults);
  };

  const getWarningForField = (key: string) => {
    return warnings.find(w => w.field === key);
  };

  const groupedConfigs = useMemo(() => {
    const groups: Record<string, DriverConfig[]> = {
      growth: [],
      costs: [],
      efficiency: []
    };
    DRIVER_CONFIGS.forEach(config => {
      groups[config.category].push(config);
    });
    return groups;
  }, []);

  const categoryLabels = {
    growth: 'Revenue & Growth',
    costs: 'Cost Management',
    efficiency: 'Operational Efficiency'
  };

  const hasChanges = Object.values(values).some(v => v !== 0);

  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <CardTitle className="text-lg">Scenario Drivers</CardTitle>
            <CardDescription>
              Adjust key business levers to see their impact on your runway
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleReset}
              disabled={!hasChanges}
              data-testid="button-reset-drivers"
            >
              <RotateCcw className="h-4 w-4 mr-2" />
              Reset
            </Button>
            <Button 
              size="sm"
              onClick={() => onSimulate?.(values)}
              disabled={isSimulating}
              data-testid="button-simulate-drivers"
            >
              <Play className="h-4 w-4 mr-2" />
              {isSimulating ? 'Simulating...' : 'Simulate'}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {Object.entries(groupedConfigs).map(([category, configs]) => (
          <div key={category} className="space-y-4">
            <h4 className="text-sm font-medium text-muted-foreground">
              {categoryLabels[category as keyof typeof categoryLabels]}
            </h4>
            <div className="grid gap-4">
              {configs.map(config => {
                const warning = getWarningForField(config.key);
                const value = values[config.key] ?? 0;
                
                return (
                  <div key={config.key} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Label htmlFor={config.key} className="text-sm">
                          {config.label}
                        </Label>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Info className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                          </TooltipTrigger>
                          <TooltipContent>
                            <p className="max-w-xs">{config.description}</p>
                          </TooltipContent>
                        </Tooltip>
                        {warning && (
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <AlertTriangle className={`h-3.5 w-3.5 ${warning.severity === 'error' ? 'text-destructive' : 'text-yellow-500'}`} />
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>{warning.message}</p>
                            </TooltipContent>
                          </Tooltip>
                        )}
                      </div>
                      <Badge 
                        variant={value === 0 ? 'secondary' : value > 0 ? 'default' : 'outline'}
                        className="font-mono text-xs"
                      >
                        {value > 0 ? '+' : ''}{value}{config.unit}
                      </Badge>
                    </div>
                    <Slider
                      id={config.key}
                      min={config.min}
                      max={config.max}
                      step={config.step}
                      value={[value]}
                      onValueChange={(v) => handleChange(config.key, v)}
                      className="w-full"
                      data-testid={`slider-${config.key}`}
                    />
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>{config.min}{config.unit}</span>
                      <span>{config.max}{config.unit}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
