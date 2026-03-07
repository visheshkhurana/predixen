import { useState, useMemo } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useFounderStore } from "@/store/founderStore";
import { apiRequest } from "@/lib/queryClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import {
  FileStack,
  BarChart3,
  Briefcase,
  FileText,
  Activity,
  Presentation,
  GitBranch,
  Loader2,
  Download,
  Copy,
  Check,
  Globe,
  Sparkles,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

const DOC_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  "bar-chart": BarChart3,
  "briefcase": Briefcase,
  "file-text": FileText,
  "activity": Activity,
  "presentation": Presentation,
  "git-branch": GitBranch,
};

const MODEL_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  "gpt-4o": { bg: "bg-emerald-500/10", text: "text-emerald-600 dark:text-emerald-400", label: "GPT-4o" },
  "claude": { bg: "bg-amber-500/10", text: "text-amber-600 dark:text-amber-400", label: "Claude" },
  "gemini": { bg: "bg-indigo-500/10", text: "text-indigo-600 dark:text-indigo-400", label: "Gemini" },
  "sonar": { bg: "bg-blue-500/10", text: "text-blue-600 dark:text-blue-400", label: "Perplexity" },
};

function getModelBadge(model: string) {
  const lower = (model || "").toLowerCase();
  for (const [key, config] of Object.entries(MODEL_COLORS)) {
    if (lower.includes(key)) return config;
  }
  return { bg: "bg-muted", text: "text-muted-foreground", label: model || "AI" };
}

interface DocType {
  id: string;
  name: string;
  description: string;
  icon: string;
  sections: string[];
}

interface GeneratedSection {
  title: string;
  content: string;
  model_used: string;
  provider_used: string;
  task_type: string;
  has_web_research: boolean;
}

interface GeneratedDoc {
  doc_type: DocType;
  sections: GeneratedSection[];
  company: { name: string };
  metrics: Record<string, number>;
  generated_at: string;
}

export default function DocGeneratorPage() {
  const { currentCompany } = useFounderStore();
  const { toast } = useToast();
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [customInstructions, setCustomInstructions] = useState("");
  const [includeWebResearch, setIncludeWebResearch] = useState(false);
  const [generatedDoc, setGeneratedDoc] = useState<GeneratedDoc | null>(null);
  const [copiedSection, setCopiedSection] = useState<number | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<number>>(new Set());

  const { data: docTypesData, isLoading: loadingTypes } = useQuery<{ doc_types: DocType[] }>({
    queryKey: ["/api/companies", currentCompany?.id, "doc-generator", "types"],
    queryFn: async () => {
      const res = await fetch(`/api/companies/${currentCompany?.id}/doc-generator/types`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error("Failed to load document types");
      return res.json();
    },
    enabled: !!currentCompany?.id,
  });

  const generateMutation = useMutation({
    mutationFn: async (docType: string) => {
      const res = await apiRequest("POST", `/api/companies/${currentCompany?.id}/doc-generator/generate`, {
        doc_type: docType,
        custom_instructions: customInstructions || null,
        include_web_research: includeWebResearch,
      });
      return res.json();
    },
    onSuccess: (data: GeneratedDoc) => {
      setGeneratedDoc(data);
      setExpandedSections(new Set(data.sections.map((_, i) => i)));
      toast({ title: "Document generated", description: `${data.doc_type.name} is ready` });
    },
    onError: (err: any) => {
      toast({ title: "Generation failed", description: err.message, variant: "destructive" });
    },
  });

  const handleGenerate = () => {
    if (!selectedType) return;
    generateMutation.mutate(selectedType);
  };

  const handleCopySection = (index: number, content: string) => {
    navigator.clipboard.writeText(content);
    setCopiedSection(index);
    setTimeout(() => setCopiedSection(null), 2000);
  };

  const handleCopyAll = () => {
    if (!generatedDoc) return;
    const fullText = generatedDoc.sections
      .map((s) => `## ${s.title}\n\n${s.content}`)
      .join("\n\n---\n\n");
    navigator.clipboard.writeText(fullText);
    toast({ title: "Copied", description: "Full document copied to clipboard" });
  };

  const handleDownloadMarkdown = () => {
    if (!generatedDoc) return;
    const md = `# ${generatedDoc.doc_type.name}\n**${generatedDoc.company.name}** | Generated ${new Date(generatedDoc.generated_at).toLocaleDateString()}\n\n` +
      generatedDoc.sections
        .map((s) => `## ${s.title}\n\n${s.content}`)
        .join("\n\n---\n\n");
    const blob = new Blob([md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${generatedDoc.doc_type.id}-${generatedDoc.company.name.toLowerCase().replace(/\s+/g, "-")}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const toggleSection = (index: number) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  const modelsUsed = useMemo(() => {
    if (!generatedDoc) return [];
    const seen = new Set<string>();
    return generatedDoc.sections
      .filter((s) => s.model_used && s.model_used !== "error")
      .map((s) => {
        const badge = getModelBadge(s.model_used);
        if (seen.has(badge.label)) return null;
        seen.add(badge.label);
        return badge;
      })
      .filter(Boolean) as { bg: string; text: string; label: string }[];
  }, [generatedDoc]);

  return (
    <div className="max-w-5xl mx-auto space-y-6 p-4 md:p-6">
      <div>
        <div className="flex items-center gap-3 mb-1">
          <FileStack className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold tracking-tight" data-testid="text-page-title">Document Generator</h1>
        </div>
        <p className="text-muted-foreground text-sm" data-testid="text-page-description">
          Generate financial models, investor memos, KPI reports, and more using your company data and AI.
        </p>
      </div>

      {!generatedDoc && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {loadingTypes
              ? Array.from({ length: 6 }).map((_, i) => (
                  <Skeleton key={i} className="h-32 rounded-lg" />
                ))
              : docTypesData?.doc_types?.map((dt) => {
                  const IconComp = DOC_ICONS[dt.icon] || FileText;
                  const isSelected = selectedType === dt.id;
                  return (
                    <Card
                      key={dt.id}
                      className={`cursor-pointer transition-all ${
                        isSelected
                          ? "ring-2 ring-primary border-primary shadow-md"
                          : "hover:border-primary/40 hover:shadow-sm"
                      }`}
                      onClick={() => setSelectedType(dt.id)}
                      data-testid={`card-doc-type-${dt.id}`}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start gap-3">
                          <div className={`p-2 rounded-lg ${isSelected ? "bg-primary/15" : "bg-muted"}`}>
                            <IconComp className={`h-5 w-5 ${isSelected ? "text-primary" : "text-muted-foreground"}`} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <h3 className="font-semibold text-sm">{dt.name}</h3>
                            <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{dt.description}</p>
                            <div className="flex flex-wrap gap-1 mt-2">
                              {dt.sections.slice(0, 3).map((s) => (
                                <Badge key={s} variant="secondary" className="text-[10px] px-1.5 py-0">
                                  {s}
                                </Badge>
                              ))}
                              {dt.sections.length > 3 && (
                                <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                                  +{dt.sections.length - 3}
                                </Badge>
                              )}
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
          </div>

          {selectedType && (
            <Card data-testid="card-generation-options">
              <CardContent className="p-4 space-y-4">
                <div>
                  <Label htmlFor="custom-instructions" className="text-sm font-medium">
                    Custom Instructions (optional)
                  </Label>
                  <Textarea
                    id="custom-instructions"
                    placeholder="e.g., Focus on Series A readiness, emphasize unit economics improvement..."
                    value={customInstructions}
                    onChange={(e) => setCustomInstructions(e.target.value)}
                    className="mt-1.5 min-h-[80px]"
                    data-testid="input-custom-instructions"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Switch
                      id="web-research"
                      checked={includeWebResearch}
                      onCheckedChange={setIncludeWebResearch}
                      data-testid="switch-web-research"
                    />
                    <Label htmlFor="web-research" className="text-sm cursor-pointer flex items-center gap-1.5">
                      <Globe className="h-3.5 w-3.5" />
                      Include web research for market data
                    </Label>
                  </div>
                  <Button
                    onClick={handleGenerate}
                    disabled={generateMutation.isPending}
                    className="gap-2"
                    data-testid="button-generate-doc"
                  >
                    {generateMutation.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-4 w-4" />
                        Generate Document
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {generateMutation.isPending && (
        <Card>
          <CardContent className="p-8 text-center space-y-4">
            <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
            <div>
              <p className="font-medium">Generating your document...</p>
              <p className="text-sm text-muted-foreground mt-1">
                AI is analyzing your company data and writing each section with the optimal model.
              </p>
            </div>
            <div className="flex justify-center gap-2">
              <Badge variant="secondary" className="text-xs">GPT-4o for financials</Badge>
              <Badge variant="secondary" className="text-xs">Claude for strategy</Badge>
              {includeWebResearch && (
                <Badge variant="secondary" className="text-xs">Perplexity for research</Badge>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {generatedDoc && !generateMutation.isPending && (
        <div className="space-y-4">
          <Card data-testid="card-generated-doc-header">
            <CardContent className="p-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-bold" data-testid="text-doc-title">{generatedDoc.doc_type.name}</h2>
                  <p className="text-sm text-muted-foreground">
                    {generatedDoc.company.name} &middot; {new Date(generatedDoc.generated_at).toLocaleString()}
                  </p>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {modelsUsed.map((m) => (
                      <Badge key={m.label} variant="secondary" className={`text-[10px] ${m.bg} ${m.text} border-0`}>
                        {m.label}
                      </Badge>
                    ))}
                    {generatedDoc.sections.some((s) => s.has_web_research) && (
                      <Badge variant="secondary" className="text-[10px] bg-blue-500/10 text-blue-600 dark:text-blue-400 border-0">
                        <Globe className="h-2.5 w-2.5 mr-1" />
                        Web Research
                      </Badge>
                    )}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={handleCopyAll} className="gap-1.5" data-testid="button-copy-all">
                    <Copy className="h-3.5 w-3.5" />
                    Copy All
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleDownloadMarkdown} className="gap-1.5" data-testid="button-download-md">
                    <Download className="h-3.5 w-3.5" />
                    Download .md
                  </Button>
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => {
                      setGeneratedDoc(null);
                      setSelectedType(null);
                      setCustomInstructions("");
                    }}
                    className="gap-1.5"
                    data-testid="button-new-doc"
                  >
                    <FileStack className="h-3.5 w-3.5" />
                    New
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {generatedDoc.sections.map((section, i) => {
            const badge = getModelBadge(section.model_used);
            const isExpanded = expandedSections.has(i);
            return (
              <Card key={i} data-testid={`card-section-${i}`}>
                <CardHeader
                  className="p-4 pb-0 cursor-pointer"
                  onClick={() => toggleSection(i)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CardTitle className="text-base">{section.title}</CardTitle>
                      <Badge variant="secondary" className={`text-[10px] ${badge.bg} ${badge.text} border-0`}>
                        {badge.label}
                      </Badge>
                      {section.has_web_research && (
                        <Badge variant="secondary" className="text-[10px] bg-blue-500/10 text-blue-600 dark:text-blue-400 border-0">
                          <Globe className="h-2.5 w-2.5 mr-0.5" />
                          Web
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCopySection(i, section.content);
                        }}
                        data-testid={`button-copy-section-${i}`}
                      >
                        {copiedSection === i ? (
                          <Check className="h-3.5 w-3.5 text-emerald-500" />
                        ) : (
                          <Copy className="h-3.5 w-3.5" />
                        )}
                      </Button>
                      {isExpanded ? (
                        <ChevronUp className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-muted-foreground" />
                      )}
                    </div>
                  </div>
                </CardHeader>
                {isExpanded && (
                  <CardContent className="p-4 pt-3">
                    <div className="prose prose-sm dark:prose-invert max-w-none text-sm leading-relaxed whitespace-pre-wrap" data-testid={`text-section-content-${i}`}>
                      {section.content}
                    </div>
                  </CardContent>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
