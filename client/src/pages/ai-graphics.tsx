import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { useFounderStore } from "@/store/founderStore";
import { useToast } from "@/hooks/use-toast";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Palette,
  Sparkles,
  Download,
  Loader2,
  Image as ImageIcon,
  Lightbulb,
  Trash2,
  Copy,
} from "lucide-react";

const STYLES = [
  { id: "professional", label: "Professional" },
  { id: "infographic", label: "Infographic" },
  { id: "chart", label: "Chart" },
  { id: "illustration", label: "Illustration" },
  { id: "minimal", label: "Minimal" },
];

const ASPECT_RATIOS = [
  { id: "1:1", label: "1:1 (Square)" },
  { id: "16:9", label: "16:9 (Widescreen)" },
  { id: "4:3", label: "4:3 (Standard)" },
];

interface GeneratedImage {
  id: string;
  prompt: string;
  style: string;
  aspectRatio: string;
  imageBase64: string;
  mimeType: string;
  timestamp: number;
}

export default function AIGraphicsPage() {
  const { currentCompany } = useFounderStore();
  const { toast } = useToast();
  const companyId = currentCompany?.id;

  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState("professional");
  const [aspectRatio, setAspectRatio] = useState("16:9");
  const [isGenerating, setIsGenerating] = useState(false);
  const [gallery, setGallery] = useState<GeneratedImage[]>([]);
  const [selectedImage, setSelectedImage] = useState<GeneratedImage | null>(null);

  const { data: suggestionsData, isLoading: suggestionsLoading } = useQuery<{
    suggestions: Array<{ prompt: string; style: string; category: string }>;
    company_name: string;
  }>({
    queryKey: ["/api/companies", companyId, "ai-graphics", "suggestions"],
    enabled: !!companyId,
  });

  const handleGenerate = useCallback(async () => {
    if (!prompt.trim() || !companyId) return;
    setIsGenerating(true);
    try {
      const res = await apiRequest("POST", `/api/companies/${companyId}/ai-graphics/generate`, {
        prompt: prompt.trim(),
        style,
        aspect_ratio: aspectRatio,
      });
      const data = await res.json();

      if (data.image_base64) {
        const newImage: GeneratedImage = {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          prompt: prompt.trim(),
          style,
          aspectRatio,
          imageBase64: data.image_base64,
          mimeType: data.mime_type || "image/png",
          timestamp: Date.now(),
        };
        setGallery((prev) => [newImage, ...prev]);
        setSelectedImage(newImage);
        toast({ title: "Image generated", description: "Your AI graphic is ready." });
      } else {
        toast({
          title: "Generation failed",
          description: data.error || "Could not generate image. Try a different prompt.",
          variant: "destructive",
        });
      }
    } catch {
      toast({
        title: "Error",
        description: "Failed to generate image. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsGenerating(false);
    }
  }, [prompt, style, aspectRatio, companyId, toast]);

  const handleDownload = useCallback((image: GeneratedImage) => {
    const extension = image.mimeType.includes("png") ? "png" : "jpg";
    const link = document.createElement("a");
    link.href = `data:${image.mimeType};base64,${image.imageBase64}`;
    link.download = `ai-graphic-${image.id}.${extension}`;
    link.click();
  }, []);

  const handleRemoveFromGallery = useCallback((id: string) => {
    setGallery((prev) => prev.filter((img) => img.id !== id));
    if (selectedImage?.id === id) {
      setSelectedImage(null);
    }
  }, [selectedImage]);

  const handleUseSuggestion = useCallback((suggestion: { prompt: string; style: string }) => {
    setPrompt(suggestion.prompt);
    setStyle(suggestion.style);
  }, []);

  return (
    <div className="p-4 md:p-6 space-y-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2" data-testid="text-page-title">
          <Palette className="h-6 w-6" />
          AI Graphics Studio
        </h1>
        <p className="text-sm text-muted-foreground mt-1" data-testid="text-page-subtitle">
          Generate professional AI graphics for board decks, investor presentations, and reports.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-6">
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-base flex items-center gap-2">
                <Sparkles className="h-4 w-4" />
                Generate Graphic
              </CardTitle>
              <CardDescription>Describe the image you want to create.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Prompt</label>
                <Textarea
                  placeholder="Describe your graphic... e.g., 'Growth trajectory chart showing MRR growth for a SaaS startup'"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  className="resize-none text-sm"
                  rows={4}
                  data-testid="input-prompt"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Style</label>
                  <Select value={style} onValueChange={setStyle}>
                    <SelectTrigger data-testid="select-style">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {STYLES.map((s) => (
                        <SelectItem key={s.id} value={s.id} data-testid={`select-style-${s.id}`}>
                          {s.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Aspect Ratio</label>
                  <Select value={aspectRatio} onValueChange={setAspectRatio}>
                    <SelectTrigger data-testid="select-aspect-ratio">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ASPECT_RATIOS.map((ar) => (
                        <SelectItem key={ar.id} value={ar.id} data-testid={`select-aspect-ratio-${ar.id}`}>
                          {ar.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Button
                onClick={handleGenerate}
                disabled={!prompt.trim() || isGenerating || !companyId}
                className="w-full"
                data-testid="button-generate"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Generate Image
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-base flex items-center gap-2">
                <Lightbulb className="h-4 w-4" />
                Suggested Graphics
              </CardTitle>
              <CardDescription>AI-recommended graphics based on your company data.</CardDescription>
            </CardHeader>
            <CardContent>
              {suggestionsLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-16 w-full" />
                  <Skeleton className="h-16 w-full" />
                  <Skeleton className="h-16 w-full" />
                </div>
              ) : suggestionsData?.suggestions && suggestionsData.suggestions.length > 0 ? (
                <div className="space-y-2">
                  {suggestionsData.suggestions.map((suggestion, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-md border hover-elevate cursor-pointer"
                      onClick={() => handleUseSuggestion(suggestion)}
                      data-testid={`suggestion-${idx}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm line-clamp-2" data-testid={`text-suggestion-prompt-${idx}`}>
                            {suggestion.prompt}
                          </p>
                          <div className="flex items-center gap-2 mt-1.5">
                            <Badge variant="secondary" className="text-[10px]">
                              {suggestion.style}
                            </Badge>
                            <Badge variant="outline" className="text-[10px]">
                              {suggestion.category}
                            </Badge>
                          </div>
                        </div>
                        <Copy className="h-3.5 w-3.5 text-muted-foreground shrink-0 mt-0.5" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4" data-testid="text-no-suggestions">
                  No suggestions available. Run a Health Check first to get personalized recommendations.
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-base flex items-center gap-2">
                <ImageIcon className="h-4 w-4" />
                Preview
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isGenerating ? (
                <div className="flex flex-col items-center justify-center py-16 gap-4" data-testid="state-generating">
                  <Loader2 className="h-10 w-10 animate-spin text-primary" />
                  <p className="text-sm text-muted-foreground">Generating your graphic...</p>
                </div>
              ) : selectedImage ? (
                <div className="space-y-4">
                  <div className="rounded-md border overflow-hidden bg-muted/30">
                    <img
                      src={`data:${selectedImage.mimeType};base64,${selectedImage.imageBase64}`}
                      alt={selectedImage.prompt}
                      className="w-full h-auto"
                      data-testid="img-preview"
                    />
                  </div>
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="text-[10px]">
                        {selectedImage.style}
                      </Badge>
                      <Badge variant="outline" className="text-[10px]">
                        {selectedImage.aspectRatio}
                      </Badge>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDownload(selectedImage)}
                      data-testid="button-download"
                    >
                      <Download className="h-4 w-4 mr-1" />
                      Download
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground" data-testid="text-preview-prompt">
                    {selectedImage.prompt}
                  </p>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground" data-testid="state-empty-preview">
                  <ImageIcon className="h-12 w-12 opacity-30" />
                  <p className="text-sm">Generated images will appear here</p>
                  <p className="text-xs">Enter a prompt and click Generate to get started</p>
                </div>
              )}
            </CardContent>
          </Card>

          {gallery.length > 0 && (
            <Card>
              <CardHeader className="pb-4">
                <CardTitle className="text-base flex items-center gap-2">
                  Gallery
                  <Badge variant="secondary" className="no-default-hover-elevate">
                    {gallery.length}
                  </Badge>
                </CardTitle>
                <CardDescription>Images generated during this session.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {gallery.map((image) => (
                    <div
                      key={image.id}
                      className={`group relative rounded-md border overflow-visible cursor-pointer hover-elevate ${
                        selectedImage?.id === image.id ? "ring-2 ring-primary" : ""
                      }`}
                      onClick={() => setSelectedImage(image)}
                      data-testid={`gallery-item-${image.id}`}
                    >
                      <div className="overflow-hidden rounded-md">
                        <img
                          src={`data:${image.mimeType};base64,${image.imageBase64}`}
                          alt={image.prompt}
                          className="w-full h-24 object-cover"
                          data-testid={`img-gallery-${image.id}`}
                        />
                      </div>
                      <div className="p-2">
                        <p className="text-[10px] text-muted-foreground line-clamp-1">
                          {image.prompt}
                        </p>
                      </div>
                      <div className="absolute top-1 right-1 invisible group-hover:visible">
                        <Button
                          variant="secondary"
                          size="icon"
                          className="h-6 w-6"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRemoveFromGallery(image.id);
                          }}
                          data-testid={`button-remove-gallery-${image.id}`}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
