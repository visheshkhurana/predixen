import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { 
  TrendingUp, 
  TrendingDown, 
  Target, 
  Zap, 
  Shield,
  Layers,
  ArrowRight,
  CheckCircle,
  Info,
  AlertTriangle,
  Clock
} from "lucide-react";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

interface ScenarioTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
}

const categoryIcons: Record<string, React.ReactNode> = {
  conservative: <Shield className="h-5 w-5" />,
  aggressive: <Zap className="h-5 w-5" />,
  strategic: <Target className="h-5 w-5" />,
  stress_test: <TrendingDown className="h-5 w-5" />,
};

const categoryColors: Record<string, string> = {
  conservative: "bg-blue-500/10 text-blue-500",
  aggressive: "bg-orange-500/10 text-orange-500",
  strategic: "bg-purple-500/10 text-purple-500",
  stress_test: "bg-red-500/10 text-red-500",
};

const categoryLabels: Record<string, string> = {
  conservative: "Conservative",
  aggressive: "Aggressive",
  strategic: "Strategic",
  stress_test: "Stress Test",
};

const templateExpectedImpact: Record<string, { runway: string; burn: string; risk: "low" | "medium" | "high" }> = {
  baseline: { runway: "No change", burn: "0%", risk: "low" },
  conservative_cut: { runway: "+3-6 months", burn: "-25%", risk: "low" },
  aggressive_growth: { runway: "-2-3 months", burn: "+30%", risk: "high" },
  fundraise: { runway: "+12-18 months", burn: "+20%", risk: "medium" },
  downturn: { runway: "-4-6 months", burn: "0%", risk: "high" },
  expansion_focus: { runway: "+1-2 months", burn: "-10%", risk: "low" },
  pricing_increase: { runway: "+2-4 months", burn: "0%", risk: "medium" },
};

const templateAssumptions: Record<string, string[]> = {
  baseline: [
    "5% month-over-month growth rate",
    "3% monthly customer churn",
    "70% gross margin maintained",
    "No significant hiring or cost changes",
  ],
  conservative_cut: [
    "Reduce burn rate by 25%",
    "Growth slows to 2% MoM",
    "6-month hiring freeze",
    "15% operating cost reduction",
  ],
  aggressive_growth: [
    "Target 12% MoM growth",
    "30% increase in burn rate",
    "Add 5 new team members",
    "50% marketing spend increase",
  ],
  fundraise: [
    "$5M Series A at 20% dilution",
    "Fundraise closes in Month 3",
    "8% MoM growth post-funding",
    "Significant hiring post-close",
  ],
  downturn: [
    "Negative 2% monthly growth",
    "Churn doubles to 6%",
    "10% price pressure from market",
    "Emergency cost cuts in Month 4",
  ],
  expansion_focus: [
    "Focus on NRR over new logos",
    "Very low 2% churn target",
    "25% expansion revenue boost",
    "5% price increase on upgrades",
  ],
  pricing_increase: [
    "15% price increase for new customers",
    "10% price increase for existing",
    "Higher ARPU across base",
    "Potential 1.5% churn increase",
  ],
};

function getRiskBadgeVariant(risk: "low" | "medium" | "high") {
  switch (risk) {
    case "low":
      return "bg-green-500/10 text-green-500";
    case "medium":
      return "bg-amber-500/10 text-amber-500";
    case "high":
      return "bg-red-500/10 text-red-500";
  }
}

export default function TemplatesPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [, navigate] = useLocation();
  const [companyId] = useState(1);
  const [selectedTemplates, setSelectedTemplates] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [confirmTemplate, setConfirmTemplate] = useState<ScenarioTemplate | null>(null);

  const { data: templatesData, isLoading } = useQuery<{
    templates: ScenarioTemplate[];
    categories: string[];
  }>({
    queryKey: ["/api/templates/"],
  });

  const applyMutation = useMutation({
    mutationFn: async (templateId: string) => {
      const res = await apiRequest("POST", `/api/templates/companies/${companyId}/apply/${templateId}`);
      return res.json();
    },
    onSuccess: (data) => {
      toast({
        title: "Scenario Created",
        description: `Created "${data.scenario_name}" from template`,
      });
      queryClient.invalidateQueries({ queryKey: ["/api/scenarios"] });
      setConfirmTemplate(null);
      navigate(`/scenarios/${data.scenario_id}`);
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: String(error),
        variant: "destructive",
      });
    },
  });

  const bulkApplyMutation = useMutation({
    mutationFn: async (templateIds: string[]) => {
      const res = await apiRequest("POST", `/api/templates/companies/${companyId}/bulk-apply`, templateIds);
      return res.json();
    },
    onSuccess: (data) => {
      toast({
        title: "Scenarios Created",
        description: `Created ${data.total_created} scenarios for comparison`,
      });
      queryClient.invalidateQueries({ queryKey: ["/api/scenarios"] });
      setSelectedTemplates([]);
      navigate("/scenarios");
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: String(error),
        variant: "destructive",
      });
    },
  });

  const filteredTemplates = templatesData?.templates.filter((template) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      template.name.toLowerCase().includes(query) ||
      template.description.toLowerCase().includes(query) ||
      template.tags.some((tag) => tag.toLowerCase().includes(query))
    );
  });

  const toggleTemplate = (templateId: string) => {
    setSelectedTemplates((prev) =>
      prev.includes(templateId)
        ? prev.filter((id) => id !== templateId)
        : [...prev, templateId]
    );
  };

  const groupedTemplates = filteredTemplates?.reduce((acc, template) => {
    if (!acc[template.category]) {
      acc[template.category] = [];
    }
    acc[template.category].push(template);
    return acc;
  }, {} as Record<string, ScenarioTemplate[]>);

  const handleUseTemplate = (template: ScenarioTemplate) => {
    setConfirmTemplate(template);
  };

  const handleConfirmApply = () => {
    if (confirmTemplate) {
      applyMutation.mutate(confirmTemplate.id);
    }
  };

  const getImpact = (templateId: string) => {
    return templateExpectedImpact[templateId] || { runway: "Variable", burn: "Variable", risk: "medium" as const };
  };

  const getAssumptions = (templateId: string) => {
    return templateAssumptions[templateId] || [];
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold" data-testid="text-page-title">Scenario Templates</h1>
          <p className="text-muted-foreground">
            Pre-configured scenarios for common financial planning use cases
          </p>
        </div>
        {selectedTemplates.length > 0 && (
          <Button
            onClick={() => bulkApplyMutation.mutate(selectedTemplates)}
            disabled={bulkApplyMutation.isPending}
            data-testid="button-create-comparison"
          >
            <Layers className="h-4 w-4 mr-2" />
            Create {selectedTemplates.length} Scenarios for Comparison
          </Button>
        )}
      </div>

      <div className="flex gap-4 items-center flex-wrap">
        <Input
          placeholder="Search templates..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="max-w-sm"
          data-testid="input-search"
        />
        {selectedTemplates.length > 0 && (
          <Badge variant="secondary">
            {selectedTemplates.length} selected
          </Badge>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-8">
          {Array(2).fill(0).map((_, categoryIdx) => (
            <section key={categoryIdx}>
              <div className="flex items-center gap-3 mb-4">
                <Skeleton className="h-10 w-10 rounded-lg" />
                <div className="space-y-1">
                  <Skeleton className="h-5 w-40" />
                  <Skeleton className="h-3 w-64" />
                </div>
              </div>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Array(3).fill(0).map((_, i) => (
                  <Card key={i}>
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <Skeleton className="h-8 w-8 rounded" />
                          <Skeleton className="h-5 w-32" />
                        </div>
                        <Skeleton className="h-4 w-4" />
                      </div>
                      <Skeleton className="h-4 w-full mt-2" />
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex items-center gap-4">
                        <Skeleton className="h-4 w-24" />
                      </div>
                      <div className="flex items-center gap-4">
                        <Skeleton className="h-4 w-20" />
                        <Skeleton className="h-5 w-16 rounded-full" />
                      </div>
                      <div className="flex gap-1 pt-1">
                        <Skeleton className="h-5 w-12 rounded-full" />
                        <Skeleton className="h-5 w-16 rounded-full" />
                      </div>
                    </CardContent>
                    <CardFooter>
                      <Skeleton className="h-9 w-full" />
                    </CardFooter>
                  </Card>
                ))}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <div className="space-y-8">
          {groupedTemplates &&
            Object.entries(groupedTemplates).map(([category, templates]) => (
              <section key={category} data-testid={`section-category-${category}`}>
                <div className="flex items-center gap-3 mb-4">
                  <div className={`p-2 rounded-lg ${categoryColors[category]}`}>
                    {categoryIcons[category]}
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold">
                      {categoryLabels[category] || category.replace(/_/g, " ")} Scenarios
                    </h2>
                    <p className="text-sm text-muted-foreground">
                      {category === "conservative" && "Lower risk options focused on runway extension"}
                      {category === "aggressive" && "Higher risk options for accelerated growth"}
                      {category === "strategic" && "Targeted initiatives for specific outcomes"}
                      {category === "stress_test" && "Stress test scenarios for worst-case planning"}
                    </p>
                  </div>
                </div>
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {templates.map((template) => {
                    const impact = getImpact(template.id);
                    return (
                      <Card
                        key={template.id}
                        className={`hover-elevate transition-all ${
                          selectedTemplates.includes(template.id)
                            ? "ring-2 ring-primary"
                            : ""
                        }`}
                        data-testid={`card-template-${template.id}`}
                      >
                        <CardHeader className="pb-2">
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <div className={`p-1.5 rounded ${categoryColors[template.category]}`}>
                                {categoryIcons[template.category]}
                              </div>
                              <CardTitle className="text-lg">{template.name}</CardTitle>
                            </div>
                            <Checkbox
                              checked={selectedTemplates.includes(template.id)}
                              onCheckedChange={() => toggleTemplate(template.id)}
                              data-testid={`checkbox-${template.id}`}
                            />
                          </div>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <CardDescription className="cursor-help line-clamp-2">
                                {template.description}
                              </CardDescription>
                            </TooltipTrigger>
                            <TooltipContent side="bottom" className="max-w-xs">
                              <p>{template.description}</p>
                            </TooltipContent>
                          </Tooltip>
                        </CardHeader>
                        <CardContent className="space-y-3">
                          <div className="flex items-center gap-4 text-sm">
                            <div className="flex items-center gap-1.5">
                              <Clock className="h-4 w-4 text-muted-foreground" />
                              <span className="text-muted-foreground">Runway:</span>
                              <span className={`font-medium ${
                                impact.runway.startsWith("+") ? "text-green-500" :
                                impact.runway.startsWith("-") ? "text-red-500" : "text-muted-foreground"
                              }`}>
                                {impact.runway}
                              </span>
                            </div>
                          </div>
                          <div className="flex items-center gap-4 text-sm">
                            <div className="flex items-center gap-1.5">
                              <TrendingUp className="h-4 w-4 text-muted-foreground" />
                              <span className="text-muted-foreground">Burn:</span>
                              <span className={`font-medium ${
                                impact.burn.startsWith("-") ? "text-green-500" :
                                impact.burn.startsWith("+") ? "text-red-500" : "text-muted-foreground"
                              }`}>
                                {impact.burn}
                              </span>
                            </div>
                            <Badge className={`${getRiskBadgeVariant(impact.risk)} text-xs`}>
                              {impact.risk.charAt(0).toUpperCase() + impact.risk.slice(1)} Risk
                            </Badge>
                          </div>
                          <div className="flex flex-wrap gap-1 pt-1">
                            {template.tags.map((tag) => (
                              <Badge key={tag} variant="secondary" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        </CardContent>
                        <CardFooter>
                          <Button
                            className="w-full"
                            variant="outline"
                            onClick={() => handleUseTemplate(template)}
                            disabled={applyMutation.isPending}
                            data-testid={`button-apply-${template.id}`}
                          >
                            Use This Template
                            <ArrowRight className="h-4 w-4 ml-2" />
                          </Button>
                        </CardFooter>
                      </Card>
                    );
                  })}
                </div>
              </section>
            ))}
        </div>
      )}

      <Card className="bg-muted/50">
        <CardContent className="py-6">
          <div className="flex items-start gap-4">
            <CheckCircle className="h-6 w-6 text-green-500 mt-0.5" />
            <div>
              <h3 className="font-semibold mb-1">Quick Comparison</h3>
              <p className="text-sm text-muted-foreground">
                Select multiple templates using the checkboxes to create comparison scenarios.
                This allows you to simulate different strategies side-by-side and see which
                approach works best for your company.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Dialog open={!!confirmTemplate} onOpenChange={(open) => !open && setConfirmTemplate(null)}>
        <DialogContent className="sm:max-w-lg" data-testid="dialog-confirm-template">
          {confirmTemplate && (
            <>
              <DialogHeader>
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${categoryColors[confirmTemplate.category]}`}>
                    {categoryIcons[confirmTemplate.category]}
                  </div>
                  <div>
                    <DialogTitle>{confirmTemplate.name}</DialogTitle>
                    <DialogDescription className="text-left">
                      {categoryLabels[confirmTemplate.category] || confirmTemplate.category} Scenario Template
                    </DialogDescription>
                  </div>
                </div>
              </DialogHeader>
              
              <div className="space-y-4 py-2">
                <p className="text-sm text-muted-foreground">
                  {confirmTemplate.description}
                </p>

                <div className="space-y-2">
                  <h4 className="text-sm font-medium flex items-center gap-2">
                    <Info className="h-4 w-4" />
                    Key Assumptions
                  </h4>
                  <ul className="text-sm text-muted-foreground space-y-1 pl-6">
                    {getAssumptions(confirmTemplate.id).map((assumption, i) => (
                      <li key={i} className="list-disc">{assumption}</li>
                    ))}
                  </ul>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <h4 className="text-sm font-medium flex items-center gap-2">
                      <Clock className="h-4 w-4" />
                      Expected Runway Impact
                    </h4>
                    <p className={`text-lg font-semibold ${
                      getImpact(confirmTemplate.id).runway.startsWith("+") ? "text-green-500" :
                      getImpact(confirmTemplate.id).runway.startsWith("-") ? "text-red-500" : ""
                    }`}>
                      {getImpact(confirmTemplate.id).runway}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <h4 className="text-sm font-medium flex items-center gap-2">
                      <TrendingUp className="h-4 w-4" />
                      Expected Burn Change
                    </h4>
                    <p className={`text-lg font-semibold ${
                      getImpact(confirmTemplate.id).burn.startsWith("-") ? "text-green-500" :
                      getImpact(confirmTemplate.id).burn.startsWith("+") ? "text-red-500" : ""
                    }`}>
                      {getImpact(confirmTemplate.id).burn}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <AlertTriangle className={`h-4 w-4 ${
                    getImpact(confirmTemplate.id).risk === "high" ? "text-red-500" :
                    getImpact(confirmTemplate.id).risk === "medium" ? "text-amber-500" : "text-green-500"
                  }`} />
                  <span className="text-sm">
                    Risk Level: <span className="font-medium capitalize">{getImpact(confirmTemplate.id).risk}</span>
                  </span>
                </div>

                <div className="flex flex-wrap gap-1">
                  {confirmTemplate.tags.map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>

              <DialogFooter className="gap-2 sm:gap-0">
                <Button
                  variant="outline"
                  onClick={() => setConfirmTemplate(null)}
                  data-testid="button-cancel-apply"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleConfirmApply}
                  disabled={applyMutation.isPending}
                  data-testid="button-confirm-apply"
                >
                  {applyMutation.isPending ? "Creating..." : "Apply Template"}
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
