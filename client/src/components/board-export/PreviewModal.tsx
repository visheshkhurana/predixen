import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Loader2, Download, ImageIcon } from 'lucide-react';
import { apiRequest } from '@/lib/queryClient';
import { getTemplateById } from './templates';
import { generatePDF, type SlideData } from './pdfGenerator';

function sanitizeText(text: string): string {
  return text.replace(/[<>&"']/g, (c) => {
    const map: Record<string, string> = { '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&#39;' };
    return map[c] || c;
  });
}

function getModelDisplayName(model: string): string {
  if (!model || model === 'unknown' || model === 'fallback') return '';
  const lower = model.toLowerCase();
  if (lower.includes('claude')) return 'Claude';
  if (lower.includes('gpt-4o')) return 'GPT-4o';
  if (lower.includes('gpt-4')) return 'GPT-4';
  if (lower.includes('gemini')) return 'Gemini';
  if (lower.includes('gpt-3')) return 'GPT-3.5';
  return model;
}

function getModelBadgeVariant(model: string): 'default' | 'secondary' | 'outline' {
  const lower = (model || '').toLowerCase();
  if (lower.includes('claude')) return 'default';
  if (lower.includes('gpt')) return 'secondary';
  return 'outline';
}

interface PreviewModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  companyId: number;
  templateId: string;
}

interface SectionData {
  type: string;
  title: string;
  dataSource: string;
  narrative?: string;
  data?: any;
  model_used?: string;
  provider_used?: string;
}

export function PreviewModal({ open, onOpenChange, companyId, templateId }: PreviewModalProps) {
  const template = getTemplateById(templateId);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const [slideImages, setSlideImages] = useState<Record<number, string>>({});
  const [generatingImageIdx, setGeneratingImageIdx] = useState<number | null>(null);

  const { data: exportData, isLoading: dataLoading } = useQuery({
    queryKey: ['/api/companies', companyId, 'board-export', 'data'],
    enabled: open,
  });

  const narrativeMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest('POST', `/api/companies/${companyId}/board-export/generate`, {
        templateId,
      });
      return res.json();
    },
  });

  useEffect(() => {
    if (open && template && !narrativeMutation.data && !narrativeMutation.isPending) {
      narrativeMutation.mutate();
    }
  }, [open, template]);

  useEffect(() => {
    if (!open) {
      setSlideImages({});
      setGeneratingImageIdx(null);
    }
  }, [open]);

  const narratives = narrativeMutation.data;
  const isLoading = dataLoading || narrativeMutation.isPending;
  const sections: SectionData[] = (narratives as any)?.sections || [];

  const companyName = (exportData as any)?.company_name || (narratives as any)?.company?.name || 'Company';

  const handleGenerateGraphic = useCallback(async (slideIdx: number, sectionTitle: string) => {
    setGeneratingImageIdx(slideIdx);
    try {
      const res = await apiRequest('POST', `/api/companies/${companyId}/board-export/generate-graphic`, {
        prompt: `Create a professional business graphic for: ${sectionTitle}`,
        style: 'professional',
        aspect_ratio: '16:9',
        section_context: sectionTitle,
      });
      const result = await res.json();
      if (result.image_base64) {
        setSlideImages(prev => ({ ...prev, [slideIdx]: result.image_base64 }));
      }
    } catch {
    } finally {
      setGeneratingImageIdx(null);
    }
  }, [companyId]);

  const buildSlides = (): SlideData[] => {
    if (!template || !exportData) return [];
    const data = exportData as any;
    const narr = (narratives as any)?.narratives || {};

    return template.sections.map((section, idx) => {
      const backendSection = sections[idx];

      const slide: SlideData = {
        title: section.title,
        type: section.type,
        content: '',
        modelUsed: backendSection?.model_used,
        providerUsed: backendSection?.provider_used,
      };

      if (slideImages[idx]) {
        slide.imageBase64 = slideImages[idx];
      }

      if (section.type === 'metrics' && data.metrics) {
        const m = data.metrics;
        if (section.dataSource === 'unit_economics') {
          slide.metrics = [
            { label: 'CAC', value: formatVal(m.cac, 'currency') },
            { label: 'LTV', value: formatVal(m.ltv, 'currency') },
            { label: 'LTV:CAC', value: formatVal(m.ltv_cac_ratio, 'ratio') },
            { label: 'Payback Period', value: formatVal(m.payback_months, 'months') },
          ];
        } else {
          slide.metrics = [
            { label: 'MRR', value: formatVal(m.mrr, 'currency') },
            { label: 'ARR', value: formatVal(m.arr, 'currency') },
            { label: 'Net Burn', value: formatVal(m.net_burn, 'currency') },
            { label: 'Runway', value: formatVal(m.runway_months, 'months') },
            { label: 'Gross Margin', value: formatVal(m.gross_margin, 'percent') },
            { label: 'Revenue Growth', value: formatVal(m.revenue_growth, 'percent') },
          ];
        }
      }

      if (section.type === 'comparison' && data.scenarios) {
        const scenarioList = data.scenarios as any[];
        slide.content = scenarioList
          .map((s: any) => `${s.name}: Runway P50 ${s.runway_p50 ?? 'N/A'}mo, Survival 18m ${s.survival_18m ?? 'N/A'}%`)
          .join('\n');
      }

      if (section.type === 'simulation' && data.simulation) {
        const sim = data.simulation;
        slide.metrics = [
          { label: 'Runway P10', value: `${sim.runway_p10 ?? 'N/A'} mo` },
          { label: 'Runway P50', value: `${sim.runway_p50 ?? 'N/A'} mo` },
          { label: 'Runway P90', value: `${sim.runway_p90 ?? 'N/A'} mo` },
          { label: '12m Survival', value: `${sim.survival_12m ?? 'N/A'}%` },
          { label: '18m Survival', value: `${sim.survival_18m ?? 'N/A'}%` },
        ];
      }

      const narrativeText = backendSection?.narrative || narr[section.dataSource];
      if (section.aiNarrative && narrativeText) {
        slide.narrativeHtml = sanitizeText(narrativeText).replace(/\n/g, '<br/>');
        slide.content = narrativeText;
      }

      if (section.type === 'chart') {
        slide.content = 'Chart data available in the interactive dashboard.';
      }

      return slide;
    });
  };

  const handleDownloadPdf = () => {
    setIsGeneratingPdf(true);
    try {
      const slides = buildSlides();
      generatePDF(slides, companyName);
    } finally {
      setIsGeneratingPdf(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto" data-testid="dialog-board-export-preview">
        <DialogHeader>
          <DialogTitle data-testid="text-export-title">
            {template?.name || 'Board Deck'} Preview
          </DialogTitle>
          <DialogDescription data-testid="text-export-description">
            {template?.description || 'Preview your board deck before downloading'}
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="space-y-4" data-testid="loading-export-preview">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Generating board deck...</span>
            </div>
            {Array.from({ length: 3 }).map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-5 w-48" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-24 w-full" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant="secondary" data-testid="badge-template-name">
                {template?.name}
              </Badge>
              <Badge variant="outline" data-testid="badge-slide-count">
                {template?.sections.length || 0} slides
              </Badge>
            </div>

            {buildSlides().map((slide, idx) => {
              const modelName = getModelDisplayName(slide.modelUsed || '');
              const isGeneratingThisImage = generatingImageIdx === idx;

              return (
                <Card key={idx} data-testid={`card-slide-${idx}`}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <div className="flex items-center gap-2 flex-wrap">
                        <CardTitle className="text-base" data-testid={`text-slide-title-${idx}`}>
                          {slide.title}
                        </CardTitle>
                        {modelName && (
                          <Badge
                            variant={getModelBadgeVariant(slide.modelUsed || '')}
                            className="text-xs"
                            data-testid={`badge-model-${idx}`}
                          >
                            {modelName}
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge variant="outline" className="text-xs" data-testid={`badge-slide-type-${idx}`}>
                          {slide.type}
                        </Badge>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleGenerateGraphic(idx, slide.title)}
                          disabled={isGeneratingThisImage}
                          data-testid={`button-generate-graphic-${idx}`}
                        >
                          {isGeneratingThisImage ? (
                            <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                          ) : (
                            <ImageIcon className="h-4 w-4 mr-1" />
                          )}
                          {isGeneratingThisImage ? 'Generating...' : 'Generate Graphic'}
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {slide.metrics && slide.metrics.length > 0 && (
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                        {slide.metrics.map((m, mIdx) => (
                          <div
                            key={mIdx}
                            className="bg-muted/50 rounded-md p-3 text-center"
                            data-testid={`metric-${idx}-${mIdx}`}
                          >
                            <div className="text-xs text-muted-foreground">{m.label}</div>
                            <div className="text-lg font-bold">{m.value}</div>
                            {m.delta && (
                              <div className={`text-xs ${m.delta.startsWith('-') ? 'text-red-500' : 'text-emerald-500'}`}>
                                {m.delta}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                    {slide.narrativeHtml && (
                      <div
                        className="text-sm text-muted-foreground leading-relaxed"
                        dangerouslySetInnerHTML={{ __html: slide.narrativeHtml }}
                        data-testid={`narrative-${idx}`}
                      />
                    )}
                    {slide.content && !slide.narrativeHtml && (
                      <p className="text-sm text-muted-foreground whitespace-pre-wrap" data-testid={`content-${idx}`}>
                        {slide.content}
                      </p>
                    )}
                    {(!slide.metrics || slide.metrics.length === 0) && !slide.narrativeHtml && !slide.content && (
                      <p className="text-sm text-muted-foreground italic" data-testid={`empty-${idx}`}>
                        No data available for this section
                      </p>
                    )}
                    {slide.imageBase64 && (
                      <div className="mt-4" data-testid={`image-container-${idx}`}>
                        <img
                          src={`data:image/png;base64,${slide.imageBase64}`}
                          alt={`Generated graphic for ${slide.title}`}
                          className="w-full max-h-64 object-contain rounded-md border"
                          data-testid={`image-graphic-${idx}`}
                        />
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}

            <div className="flex items-center justify-end gap-2 pt-2">
              <Button
                variant="outline"
                onClick={() => onOpenChange(false)}
                data-testid="button-close-preview"
              >
                Close
              </Button>
              <Button
                onClick={handleDownloadPdf}
                disabled={isGeneratingPdf}
                data-testid="button-download-pdf"
              >
                {isGeneratingPdf ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Download className="h-4 w-4 mr-2" />
                )}
                Download PDF
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function formatVal(value: any, type: 'currency' | 'percent' | 'ratio' | 'months'): string {
  if (value == null || value === undefined) return 'N/A';
  const num = Number(value);
  if (isNaN(num)) return 'N/A';
  switch (type) {
    case 'currency':
      if (Math.abs(num) >= 1_000_000) return `$${(num / 1_000_000).toFixed(1)}M`;
      if (Math.abs(num) >= 1_000) return `$${(num / 1_000).toFixed(0)}K`;
      return `$${num.toFixed(0)}`;
    case 'percent':
      return `${num.toFixed(1)}%`;
    case 'ratio':
      return `${num.toFixed(1)}x`;
    case 'months':
      return `${num.toFixed(1)} mo`;
    default:
      return String(num);
  }
}
