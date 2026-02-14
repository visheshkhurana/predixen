import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Loader2, BarChart3, RefreshCw } from "lucide-react";
import { TornadoChart, type TornadoChartData } from "./TornadoChart";
import { apiRequest } from "@/lib/queryClient";

interface SensitivityParameter {
  name: string;
  label: string;
  baselineValue: number;
  minValue: number;
  maxValue: number;
  enabled: boolean;
}

const DEFAULT_PARAMETERS: SensitivityParameter[] = [
  { name: "baseline_growth_rate", label: "Growth Rate (%)", baselineValue: 0, minValue: 0, maxValue: 15, enabled: true },
  { name: "gross_margin", label: "Gross Margin (%)", baselineValue: 0, minValue: 50, maxValue: 90, enabled: true },
  { name: "churn_rate", label: "Churn Rate (%)", baselineValue: 0, minValue: 2, maxValue: 10, enabled: true },
  { name: "opex", label: "OpEx ($)", baselineValue: 0, minValue: 10000, maxValue: 40000, enabled: true },
  { name: "payroll", label: "Payroll ($)", baselineValue: 0, minValue: 30000, maxValue: 80000, enabled: true },
  { name: "pricing_change_pct", label: "Pricing Change (%)", baselineValue: 0, minValue: -20, maxValue: 20, enabled: false },
  { name: "burn_reduction_pct", label: "Burn Reduction (%)", baselineValue: 0, minValue: 0, maxValue: 30, enabled: false },
  { name: "fundraise_amount", label: "Fundraise ($)", baselineValue: 0, minValue: 0, maxValue: 1000000, enabled: false },
  { name: "cash_balance", label: "Cash Balance ($)", baselineValue: 0, minValue: 200000, maxValue: 1000000, enabled: true },
];

interface SensitivityPanelProps {
  scenarioId: number;
  scenarioInputs?: Record<string, any>;
}

export function SensitivityPanel({ scenarioId, scenarioInputs }: SensitivityPanelProps) {
  const [parameters, setParameters] = useState<SensitivityParameter[]>(() => {
    return DEFAULT_PARAMETERS.map((p) => ({
      ...p,
      baselineValue: scenarioInputs?.[p.name] ?? p.baselineValue,
    }));
  });

  const [results, setResults] = useState<TornadoChartData | null>(null);

  const runAnalysisMutation = useMutation({
    mutationFn: async () => {
      const enabledParams = parameters.filter((p) => p.enabled);
      const response = await apiRequest("POST", "/api/simulations/sensitivity", {
        scenario_id: scenarioId,
        parameters: enabledParams.map((p) => ({
          name: p.name,
          label: p.label,
          baselineValue: p.baselineValue,
          minValue: p.minValue,
          maxValue: p.maxValue,
        })),
        target_metric: "runway",
        config: {
          iterations: 500,
          horizon_months: 24,
        },
      });
      return response.json();
    },
    onSuccess: (data) => {
      setResults(data);
    },
  });

  const toggleParameter = (name: string) => {
    setParameters((prev) =>
      prev.map((p) => (p.name === name ? { ...p, enabled: !p.enabled } : p))
    );
  };

  const updateParameter = (name: string, field: keyof SensitivityParameter, value: number) => {
    setParameters((prev) =>
      prev.map((p) => (p.name === name ? { ...p, [field]: value } : p))
    );
  };

  const enabledCount = parameters.filter((p) => p.enabled).length;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Sensitivity Analysis Setup
          </CardTitle>
          <CardDescription>
            Select parameters to analyze their impact on runway. The analysis will vary each parameter
            from its low to high value while holding others constant.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid gap-4">
              {parameters.map((param) => (
                <div
                  key={param.name}
                  className={`flex items-start gap-4 p-3 rounded-lg border transition-colors ${
                    param.enabled ? "bg-muted/50 border-primary/20" : "bg-background"
                  }`}
                  data-testid={`param-${param.name}`}
                >
                  <Checkbox
                    id={param.name}
                    checked={param.enabled}
                    onCheckedChange={() => toggleParameter(param.name)}
                    data-testid={`checkbox-${param.name}`}
                  />
                  <div className="flex-1 space-y-2">
                    <Label htmlFor={param.name} className="font-medium cursor-pointer">
                      {param.label}
                    </Label>
                    {param.enabled && (
                      <div className="grid grid-cols-3 gap-3">
                        <div>
                          <Label className="text-xs text-muted-foreground">Low</Label>
                          <Input
                            type="number"
                            value={param.minValue}
                            onChange={(e) =>
                              updateParameter(param.name, "minValue", parseFloat(e.target.value))
                            }
                            className="h-8"
                            data-testid={`input-${param.name}-min`}
                          />
                        </div>
                        <div>
                          <Label className="text-xs text-muted-foreground">Baseline</Label>
                          <Input
                            type="number"
                            value={param.baselineValue}
                            onChange={(e) =>
                              updateParameter(param.name, "baselineValue", parseFloat(e.target.value))
                            }
                            className="h-8"
                            data-testid={`input-${param.name}-baseline`}
                          />
                        </div>
                        <div>
                          <Label className="text-xs text-muted-foreground">High</Label>
                          <Input
                            type="number"
                            value={param.maxValue}
                            onChange={(e) =>
                              updateParameter(param.name, "maxValue", parseFloat(e.target.value))
                            }
                            className="h-8"
                            data-testid={`input-${param.name}-max`}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="flex items-center justify-between pt-4 border-t">
              <p className="text-sm text-muted-foreground">
                {enabledCount} parameters selected
              </p>
              <Button
                onClick={() => runAnalysisMutation.mutate()}
                disabled={runAnalysisMutation.isPending || enabledCount === 0}
                data-testid="button-run-sensitivity"
              >
                {runAnalysisMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Running Analysis...
                  </>
                ) : (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Run Analysis
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {results && <TornadoChart data={results} maxBars={10} />}
    </div>
  );
}
