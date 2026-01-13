import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { 
  TrendingUp, 
  TrendingDown, 
  Target, 
  Zap, 
  Shield,
  Layers,
  ArrowRight,
  CheckCircle
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

export default function TemplatesPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [, navigate] = useLocation();
  const [companyId] = useState(1);
  const [selectedTemplates, setSelectedTemplates] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");

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

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
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

      <div className="flex gap-4 items-center">
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
        <div className="text-center py-12 text-muted-foreground">
          Loading templates...
        </div>
      ) : (
        <div className="space-y-8">
          {groupedTemplates &&
            Object.entries(groupedTemplates).map(([category, templates]) => (
              <div key={category}>
                <div className="flex items-center gap-2 mb-4">
                  <div className={`p-2 rounded-lg ${categoryColors[category]}`}>
                    {categoryIcons[category]}
                  </div>
                  <h2 className="text-lg font-semibold capitalize">
                    {category.replace(/_/g, " ")} Scenarios
                  </h2>
                </div>
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {templates.map((template) => (
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
                        <div className="flex items-start justify-between">
                          <CardTitle className="text-lg">{template.name}</CardTitle>
                          <Checkbox
                            checked={selectedTemplates.includes(template.id)}
                            onCheckedChange={() => toggleTemplate(template.id)}
                            data-testid={`checkbox-${template.id}`}
                          />
                        </div>
                        <CardDescription>{template.description}</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="flex flex-wrap gap-1">
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
                          onClick={() => applyMutation.mutate(template.id)}
                          disabled={applyMutation.isPending}
                          data-testid={`button-apply-${template.id}`}
                        >
                          Use This Template
                          <ArrowRight className="h-4 w-4 ml-2" />
                        </Button>
                      </CardFooter>
                    </Card>
                  ))}
                </div>
              </div>
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
    </div>
  );
}
