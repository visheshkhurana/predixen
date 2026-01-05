import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ScenarioForm } from "@/components/scenario-form";
import { CashFlowChart } from "@/components/cash-flow-chart";
import { SimulationSummary } from "@/components/simulation-summary";
import { DataTable } from "@/components/data-table";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { apiRequest, queryClient } from "@/lib/queryClient";
import type { SimulationResult } from "@shared/schema";

export default function Scenarios() {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("chart");

  const { data: result, isLoading: resultLoading } = useQuery<SimulationResult>({
    queryKey: ["/api/simulations/latest"],
  });

  const simulateMutation = useMutation({
    mutationFn: async (values: any) => {
      const response = await apiRequest("POST", "/api/simulate", values);
      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["/api/simulations/latest"] });
      queryClient.invalidateQueries({ queryKey: ["/api/scenarios"] });
      toast({
        title: "Simulation complete",
        description: `Runway: ${data.summary.runwayMonths ? `${data.summary.runwayMonths} months` : "Profitable"}`,
      });
    },
    onError: (error) => {
      toast({
        title: "Simulation failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const handleSubmit = (values: any) => {
    simulateMutation.mutate(values);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Scenario Builder</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Model different financial scenarios and see their impact
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-2">
          <ScenarioForm onSubmit={handleSubmit} isLoading={simulateMutation.isPending} />
        </div>

        <div className="lg:col-span-3 space-y-6">
          {simulateMutation.isPending ? (
            <Card>
              <CardContent className="p-6">
                <div className="space-y-4">
                  <Skeleton className="h-8 w-48" />
                  <Skeleton className="h-[300px] w-full" />
                </div>
              </CardContent>
            </Card>
          ) : result ? (
            <>
              <SimulationSummary result={result} />
              
              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="chart" data-testid="tab-chart">
                    Cash Flow Chart
                  </TabsTrigger>
                  <TabsTrigger value="table" data-testid="tab-table">
                    Monthly Data
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="chart" className="mt-4">
                  <CashFlowChart projections={result.projections} />
                </TabsContent>
                <TabsContent value="table" className="mt-4">
                  <DataTable projections={result.projections} />
                </TabsContent>
              </Tabs>
            </>
          ) : (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-16">
                <div className="p-4 rounded-full bg-muted mb-4">
                  <ChartIcon className="h-8 w-8 text-muted-foreground" />
                </div>
                <h3 className="font-semibold text-lg mb-2">Run a simulation</h3>
                <p className="text-muted-foreground text-sm text-center max-w-md">
                  Fill in the scenario parameters and click "Run Simulation" to see your projected cash flow and runway
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function ChartIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M3 3v18h18" />
      <path d="m19 9-5 5-4-4-3 3" />
    </svg>
  );
}
