import { useState, useEffect, useCallback, useMemo } from 'react';
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
import {
  Loader2,
  Download,
  ImageIcon,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Target,
  DollarSign,
  Activity,
  Zap,
  Shield,
  FileDown,
  ChevronDown,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
  RadialBarChart,
  RadialBar,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { apiRequest } from '@/lib/queryClient';
import { getTemplateById } from './templates';
import { generatePDF, downloadAsHTML, type SlideData, type ChartPoint, type ScenarioItem } from './pdfGenerator';

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

function getModelColor(model: string): string {
  const lower = (model || '').toLowerCase();
  if (lower.includes('claude')) return '#d97706';
  if (lower.includes('gpt')) return '#10b981';
  if (lower.includes('gemini')) return '#6366f1';
  return '#94a3b8';
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

interface FinancialRecord {
  period_start?: string;
  revenue: number;
  mrr?: number;
  net_burn?: number;
  cash_balance?: number;
  customers?: number;
  mom_growth?: number;
}

const CHART_COLORS = ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

function formatShortDate(dateStr?: string): string {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
  } catch {
    return dateStr.slice(0, 7);
  }
}

function fmtCurrency(n: number): string {
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

function getSlideIcon(type: string, title: string) {
  const t = title.toLowerCase();
  if (t.includes('revenue') || t.includes('growth') || t.includes('trajectory')) return <TrendingUp className="h-4 w-4" />;
  if (t.includes('burn') || t.includes('runway')) return <Activity className="h-4 w-4" />;
  if (t.includes('unit economics') || t.includes('efficiency')) return <Target className="h-4 w-4" />;
  if (t.includes('metric') || t.includes('traction')) return <BarChart3 className="h-4 w-4" />;
  if (t.includes('simulation') || t.includes('monte carlo') || t.includes('projection')) return <Zap className="h-4 w-4" />;
  if (t.includes('risk') || t.includes('mitigation')) return <Shield className="h-4 w-4" />;
  if (t.includes('fund') || t.includes('financial')) return <DollarSign className="h-4 w-4" />;
  if (type === 'chart') return <BarChart3 className="h-4 w-4" />;
  if (type === 'simulation') return <Zap className="h-4 w-4" />;
  if (type === 'comparison') return <Target className="h-4 w-4" />;
  return <Activity className="h-4 w-4" />;
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
  const companyName = (exportData as any)?.company?.name || (narratives as any)?.company?.name || 'Company';

  const financialRecords: FinancialRecord[] = useMemo(() => {
    const raw = (exportData as any)?.financial_records || [];
    return [...raw].sort((a: any, b: any) => (a.period_start || '').localeCompare(b.period_start || ''));
  }, [exportData]);

  const chartData = useMemo(() => {
    if (!financialRecords.length) return null;
    const revenue: ChartPoint[] = [];
    const mrr: ChartPoint[] = [];
    const burn: ChartPoint[] = [];
    const cash: ChartPoint[] = [];

    financialRecords.forEach((fr) => {
      const label = formatShortDate(fr.period_start);
      if (fr.revenue != null) revenue.push({ label, value: fr.revenue });
      if (fr.mrr != null) mrr.push({ label, value: fr.mrr });
      if (fr.net_burn != null) burn.push({ label, value: Math.abs(fr.net_burn) });
      if (fr.cash_balance != null) cash.push({ label, value: fr.cash_balance });
    });

    return { revenue, mrr, burn, cash };
  }, [financialRecords]);

  const scenarioItems: ScenarioItem[] = useMemo(() => {
    const raw = (exportData as any)?.scenarios || [];
    return raw.map((s: any) => {
      const sim = s.latest_simulation || {};
      const runway = sim.runway || {};
      const survival = sim.survival || {};
      return {
        name: s.name || 'Unnamed',
        runwayP50: runway.p50 ?? null,
        survival18m: typeof survival === 'object' ? survival['18m'] ?? null : null,
        description: s.description,
      };
    });
  }, [exportData]);

  const simulationData = useMemo(() => {
    const sim = (exportData as any)?.simulation || {};
    const runway = sim.runway || {};
    const survival = sim.survivalProbability || sim.survival || {};
    return {
      runwayP10: runway.p10 ?? null,
      runwayP50: runway.p50 ?? null,
      runwayP90: runway.p90 ?? null,
      survival12m: typeof survival === 'object' ? survival['12m'] ?? null : null,
      survival18m: typeof survival === 'object' ? survival['18m'] ?? null : null,
    };
  }, [exportData]);

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

  const buildSlides = useCallback((): SlideData[] => {
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
            { label: 'CAC', value: formatVal(m.cac, 'currency'), color: '#ef4444' },
            { label: 'LTV', value: formatVal(m.ltv, 'currency'), color: '#10b981' },
            { label: 'LTV:CAC', value: formatVal(m.ltv_cac_ratio, 'ratio'), color: '#6366f1' },
            { label: 'Payback Period', value: formatVal(m.payback_months, 'months'), color: '#f59e0b' },
          ];
        } else {
          slide.metrics = [
            { label: 'MRR', value: formatVal(m.mrr, 'currency'), color: '#6366f1' },
            { label: 'ARR', value: formatVal(m.arr, 'currency'), color: '#06b6d4' },
            { label: 'Net Burn', value: formatVal(m.net_burn, 'currency'), color: '#ef4444' },
            { label: 'Runway', value: formatVal(m.runway_months, 'months'), color: '#10b981' },
            { label: 'Gross Margin', value: formatVal(m.gross_margin, 'percent'), color: '#f59e0b' },
            { label: 'Revenue Growth', value: formatVal(m.revenue_growth, 'percent'), color: '#8b5cf6' },
          ];
        }
      }

      if (section.type === 'chart') {
        slide.chartData = chartData || undefined;
      }

      if (section.type === 'comparison') {
        slide.scenarios = scenarioItems;
        if (scenarioItems.length) {
          slide.content = scenarioItems
            .map(s => `${s.name}: Runway P50 ${s.runwayP50 != null ? s.runwayP50.toFixed(1) : 'N/A'}mo, Survival 18m ${s.survival18m != null ? s.survival18m.toFixed(0) : 'N/A'}%`)
            .join('\n');
        }
      }

      if (section.type === 'simulation') {
        slide.simulationData = simulationData;
        const sim = simulationData;
        slide.metrics = [
          { label: 'Runway P10', value: sim.runwayP10 != null ? `${sim.runwayP10.toFixed(1)} mo` : 'N/A', color: '#ef4444' },
          { label: 'Runway P50', value: sim.runwayP50 != null ? `${sim.runwayP50.toFixed(1)} mo` : 'N/A', color: '#6366f1' },
          { label: 'Runway P90', value: sim.runwayP90 != null ? `${sim.runwayP90.toFixed(1)} mo` : 'N/A', color: '#10b981' },
          { label: '12m Survival', value: sim.survival12m != null ? `${sim.survival12m.toFixed(0)}%` : 'N/A', color: '#06b6d4' },
          { label: '18m Survival', value: sim.survival18m != null ? `${sim.survival18m.toFixed(0)}%` : 'N/A', color: '#f59e0b' },
        ];
      }

      const narrativeText = backendSection?.narrative || narr[section.dataSource];
      if (section.aiNarrative && narrativeText) {
        slide.narrativeHtml = sanitizeText(narrativeText).replace(/\n/g, '<br/>');
        slide.content = narrativeText;
      }

      return slide;
    });
  }, [template, exportData, narratives, sections, slideImages, chartData, scenarioItems, simulationData]);

  const handleDownloadPdf = () => {
    setIsGeneratingPdf(true);
    try {
      const slides = buildSlides();
      generatePDF(slides, companyName);
    } finally {
      setIsGeneratingPdf(false);
    }
  };

  const handleDownloadHtml = () => {
    const slides = buildSlides();
    downloadAsHTML(slides, companyName);
  };

  const rechartsData = useMemo(() => {
    return financialRecords.map(fr => ({
      month: formatShortDate(fr.period_start),
      revenue: fr.revenue || 0,
      mrr: fr.mrr || 0,
      burn: Math.abs(fr.net_burn || 0),
      cash: fr.cash_balance || 0,
    }));
  }, [financialRecords]);

  const slides = useMemo(() => buildSlides(), [buildSlides]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto" data-testid="dialog-board-export-preview">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold" data-testid="text-export-title">
            {template?.name || 'Board Deck'} Preview
          </DialogTitle>
          <DialogDescription data-testid="text-export-description">
            {template?.description || 'Preview your board deck before downloading'}
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="space-y-4" data-testid="loading-export-preview">
            <div className="flex items-center gap-3 text-muted-foreground py-4">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <div>
                <div className="font-medium text-foreground">Generating board deck...</div>
                <div className="text-sm">AI is analyzing your data and crafting narratives</div>
              </div>
            </div>
            {Array.from({ length: 3 }).map((_, i) => (
              <Card key={i} className="overflow-hidden">
                <div className="h-1 bg-gradient-to-r from-primary/40 to-cyan-500/40" />
                <CardHeader>
                  <Skeleton className="h-5 w-48" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-32 w-full rounded-lg" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge className="bg-primary/10 text-primary border-primary/20" data-testid="badge-template-name">
                  {template?.name}
                </Badge>
                <Badge variant="outline" data-testid="badge-slide-count">
                  {slides.length} slides
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onOpenChange(false)}
                  data-testid="button-close-preview"
                >
                  Close
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      size="sm"
                      disabled={isGeneratingPdf}
                      className="bg-gradient-to-r from-primary to-cyan-600 hover:from-primary/90 hover:to-cyan-600/90 text-white shadow-md"
                      data-testid="button-download-pdf"
                    >
                      {isGeneratingPdf ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <Download className="h-4 w-4 mr-2" />
                      )}
                      Export
                      <ChevronDown className="h-3 w-3 ml-1" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" data-testid="menu-export-options">
                    <DropdownMenuItem onClick={handleDownloadPdf} data-testid="menu-item-export-pdf">
                      <Download className="h-4 w-4 mr-2" />
                      <div>
                        <div className="font-medium">Download as PDF</div>
                        <div className="text-xs text-muted-foreground">Print-optimized format</div>
                      </div>
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={handleDownloadHtml} data-testid="menu-item-export-html">
                      <FileDown className="h-4 w-4 mr-2" />
                      <div>
                        <div className="font-medium">Download as HTML</div>
                        <div className="text-xs text-muted-foreground">Import into Google Slides or PowerPoint</div>
                      </div>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>

            {slides.map((slide, idx) => {
              const modelName = getModelDisplayName(slide.modelUsed || '');
              const modelColor = getModelColor(slide.modelUsed || '');
              const isGeneratingThisImage = generatingImageIdx === idx;

              return (
                <Card key={idx} className="overflow-hidden border-border/60 shadow-sm" data-testid={`card-slide-${idx}`}>
                  <div className="h-1" style={{ background: `linear-gradient(90deg, ${CHART_COLORS[idx % CHART_COLORS.length]}, ${CHART_COLORS[(idx + 1) % CHART_COLORS.length]})` }} />
                  <CardHeader className="pb-3 pt-4">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <div className="flex items-center gap-3">
                        <div className="p-1.5 rounded-lg bg-muted/60 text-muted-foreground">
                          {getSlideIcon(slide.type, slide.title)}
                        </div>
                        <CardTitle className="text-base font-bold" data-testid={`text-slide-title-${idx}`}>
                          {slide.title}
                        </CardTitle>
                        {modelName && (
                          <Badge
                            className="text-xs font-semibold"
                            style={{ backgroundColor: `${modelColor}15`, color: modelColor, borderColor: `${modelColor}30` }}
                            data-testid={`badge-model-${idx}`}
                          >
                            {modelName}
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge variant="outline" className="text-xs capitalize" data-testid={`badge-slide-type-${idx}`}>
                          {slide.type}
                        </Badge>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleGenerateGraphic(idx, slide.title)}
                          disabled={isGeneratingThisImage}
                          className="text-xs"
                          data-testid={`button-generate-graphic-${idx}`}
                        >
                          {isGeneratingThisImage ? (
                            <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                          ) : (
                            <ImageIcon className="h-3.5 w-3.5 mr-1" />
                          )}
                          {isGeneratingThisImage ? 'Generating...' : 'AI Graphic'}
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4 pb-5">
                    {slide.type === 'metrics' && slide.metrics && slide.metrics.length > 0 && (
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                        {slide.metrics.map((m, mIdx) => (
                          <div
                            key={mIdx}
                            className="rounded-xl p-4 text-center border border-border/50 bg-gradient-to-b from-muted/30 to-transparent"
                            style={{ borderTopColor: m.color || CHART_COLORS[mIdx % CHART_COLORS.length], borderTopWidth: '3px' }}
                            data-testid={`metric-${idx}-${mIdx}`}
                          >
                            <div className="text-[11px] text-muted-foreground uppercase tracking-wide font-medium mb-1">{m.label}</div>
                            <div className="text-2xl font-extrabold tracking-tight">{m.value}</div>
                            {m.delta && (
                              <div className={`text-xs font-semibold mt-1 flex items-center justify-center gap-0.5 ${m.delta.startsWith('-') ? 'text-red-500' : 'text-emerald-500'}`}>
                                {m.delta.startsWith('-') ? <TrendingDown className="h-3 w-3" /> : <TrendingUp className="h-3 w-3" />}
                                {m.delta}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {slide.type === 'chart' && rechartsData.length > 0 && (
                      <div className="space-y-4">
                        <div className="rounded-xl border border-border/50 bg-card p-4">
                          <div className="text-sm font-semibold text-muted-foreground mb-3 flex items-center gap-2">
                            <TrendingUp className="h-4 w-4 text-primary" />
                            Revenue & MRR Trend
                          </div>
                          <ResponsiveContainer width="100%" height={200}>
                            <AreaChart data={rechartsData}>
                              <defs>
                                <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.2}/>
                                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                                </linearGradient>
                                <linearGradient id="mrrGrad" x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.2}/>
                                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
                                </linearGradient>
                              </defs>
                              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                              <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                              <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} tickFormatter={(v) => fmtCurrency(v)} width={60} />
                              <Tooltip formatter={(v: number) => fmtCurrency(v)} />
                              <Area type="monotone" dataKey="revenue" stroke="#6366f1" strokeWidth={2.5} fill="url(#revGrad)" name="Revenue" />
                              <Area type="monotone" dataKey="mrr" stroke="#06b6d4" strokeWidth={2.5} fill="url(#mrrGrad)" name="MRR" />
                            </AreaChart>
                          </ResponsiveContainer>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="rounded-xl border border-border/50 bg-card p-4">
                            <div className="text-sm font-semibold text-muted-foreground mb-3 flex items-center gap-2">
                              <Activity className="h-4 w-4 text-red-500" />
                              Monthly Burn
                            </div>
                            <ResponsiveContainer width="100%" height={150}>
                              <BarChart data={rechartsData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#94a3b8' }} />
                                <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} tickFormatter={(v) => fmtCurrency(v)} width={55} />
                                <Tooltip formatter={(v: number) => fmtCurrency(v)} />
                                <Bar dataKey="burn" fill="#ef4444" radius={[4, 4, 0, 0]} name="Burn Rate" opacity={0.8} />
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                          <div className="rounded-xl border border-border/50 bg-card p-4">
                            <div className="text-sm font-semibold text-muted-foreground mb-3 flex items-center gap-2">
                              <DollarSign className="h-4 w-4 text-emerald-500" />
                              Cash Balance
                            </div>
                            <ResponsiveContainer width="100%" height={150}>
                              <AreaChart data={rechartsData}>
                                <defs>
                                  <linearGradient id="cashGrad" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.2}/>
                                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                                  </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#94a3b8' }} />
                                <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} tickFormatter={(v) => fmtCurrency(v)} width={55} />
                                <Tooltip formatter={(v: number) => fmtCurrency(v)} />
                                <Area type="monotone" dataKey="cash" stroke="#10b981" strokeWidth={2} fill="url(#cashGrad)" name="Cash" />
                              </AreaChart>
                            </ResponsiveContainer>
                          </div>
                        </div>
                      </div>
                    )}

                    {slide.type === 'simulation' && simulationData && (
                      <div className="space-y-4">
                        <div className="grid grid-cols-3 gap-3">
                          {[
                            { label: 'P10 (Bear)', value: simulationData.runwayP10, color: '#ef4444' },
                            { label: 'P50 (Base)', value: simulationData.runwayP50, color: '#6366f1' },
                            { label: 'P90 (Bull)', value: simulationData.runwayP90, color: '#10b981' },
                          ].map((item, i) => (
                            <div key={i} className="rounded-xl border border-border/50 bg-card p-4 text-center">
                              <div className="text-[11px] text-muted-foreground uppercase tracking-wide font-medium mb-2">{item.label}</div>
                              <div className="relative w-20 h-20 mx-auto mb-2">
                                <svg viewBox="0 0 80 80" className="w-full h-full -rotate-90">
                                  <circle cx="40" cy="40" r="32" fill="none" stroke="currentColor" strokeWidth="8" className="text-muted/20" />
                                  <circle cx="40" cy="40" r="32" fill="none" stroke={item.color} strokeWidth="8"
                                    strokeDasharray={`${((item.value ?? 0) / 36) * 201} 201`}
                                    strokeLinecap="round" />
                                </svg>
                                <div className="absolute inset-0 flex items-center justify-center">
                                  <span className="text-lg font-bold">{item.value != null ? item.value.toFixed(0) : '—'}</span>
                                </div>
                              </div>
                              <div className="text-xs text-muted-foreground">months</div>
                            </div>
                          ))}
                        </div>
                        {(simulationData.survival12m != null || simulationData.survival18m != null) && (
                          <div className="grid grid-cols-2 gap-3">
                            {[
                              { label: '12-Month Survival', value: simulationData.survival12m, color: '#6366f1' },
                              { label: '18-Month Survival', value: simulationData.survival18m, color: '#06b6d4' },
                            ].map((item, i) => item.value != null && (
                              <div key={i} className="rounded-xl border border-border/50 bg-card p-4 flex items-center gap-4">
                                <div className="relative w-16 h-16 flex-shrink-0">
                                  <svg viewBox="0 0 64 64" className="w-full h-full -rotate-90">
                                    <circle cx="32" cy="32" r="26" fill="none" stroke="currentColor" strokeWidth="6" className="text-muted/20" />
                                    <circle cx="32" cy="32" r="26" fill="none" stroke={item.color} strokeWidth="6"
                                      strokeDasharray={`${(item.value / 100) * 163.4} 163.4`}
                                      strokeLinecap="round" />
                                  </svg>
                                  <div className="absolute inset-0 flex items-center justify-center">
                                    <span className="text-sm font-bold">{item.value.toFixed(0)}%</span>
                                  </div>
                                </div>
                                <div>
                                  <div className="text-sm font-semibold">{item.label}</div>
                                  <div className="text-xs text-muted-foreground">probability</div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {slide.type === 'comparison' && scenarioItems.length > 0 && (
                      <div className="space-y-3">
                        {scenarioItems.map((s, sIdx) => {
                          const barPct = s.runwayP50 != null ? Math.min((s.runwayP50 / 36) * 100, 100) : 0;
                          return (
                            <div key={sIdx} className="rounded-xl border border-border/50 bg-card p-4" style={{ borderLeftWidth: '4px', borderLeftColor: CHART_COLORS[sIdx % CHART_COLORS.length] }}>
                              <div className="flex items-center justify-between mb-2">
                                <div className="font-semibold text-sm">{s.name}</div>
                                <div className="flex items-center gap-4 text-sm">
                                  <span className="text-muted-foreground">P50: <strong className="text-foreground">{s.runwayP50 != null ? `${s.runwayP50.toFixed(1)}mo` : 'N/A'}</strong></span>
                                  <span className="text-muted-foreground">Surv: <strong className="text-foreground">{s.survival18m != null ? `${s.survival18m.toFixed(0)}%` : 'N/A'}</strong></span>
                                </div>
                              </div>
                              {s.description && <div className="text-xs text-muted-foreground mb-2">{s.description}</div>}
                              <div className="h-2 bg-muted/40 rounded-full overflow-hidden">
                                <div className="h-full rounded-full transition-all" style={{ width: `${barPct}%`, backgroundColor: CHART_COLORS[sIdx % CHART_COLORS.length] }} />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {slide.narrativeHtml && (
                      <div
                        className="text-sm text-muted-foreground leading-relaxed rounded-xl bg-muted/30 p-4 border-l-4 border-primary/40"
                        dangerouslySetInnerHTML={{ __html: slide.narrativeHtml }}
                        data-testid={`narrative-${idx}`}
                      />
                    )}
                    {slide.content && !slide.narrativeHtml && slide.type === 'narrative' && (
                      <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed" data-testid={`content-${idx}`}>
                        {slide.content}
                      </p>
                    )}
                    {slide.type === 'narrative' && (!slide.metrics || slide.metrics.length === 0) && !slide.narrativeHtml && !slide.content && (
                      <p className="text-sm text-muted-foreground italic" data-testid={`empty-${idx}`}>
                        No data available for this section
                      </p>
                    )}
                    {slide.imageBase64 && (
                      <div className="mt-3 rounded-xl overflow-hidden border border-border/50" data-testid={`image-container-${idx}`}>
                        <img
                          src={`data:image/png;base64,${slide.imageBase64}`}
                          alt={`Generated graphic for ${slide.title}`}
                          className="w-full max-h-64 object-contain"
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
                data-testid="button-close-preview-bottom"
              >
                Close
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    disabled={isGeneratingPdf}
                    className="bg-gradient-to-r from-primary to-cyan-600 hover:from-primary/90 hover:to-cyan-600/90 text-white shadow-md"
                    data-testid="button-download-pdf-bottom"
                  >
                    {isGeneratingPdf ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Download className="h-4 w-4 mr-2" />
                    )}
                    Export
                    <ChevronDown className="h-3 w-3 ml-1" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={handleDownloadPdf} data-testid="menu-item-export-pdf-bottom">
                    <Download className="h-4 w-4 mr-2" />
                    <div>
                      <div className="font-medium">Download as PDF</div>
                      <div className="text-xs text-muted-foreground">Print-optimized format</div>
                    </div>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={handleDownloadHtml} data-testid="menu-item-export-html-bottom">
                    <FileDown className="h-4 w-4 mr-2" />
                    <div>
                      <div className="font-medium">Download as HTML</div>
                      <div className="text-xs text-muted-foreground">Import into Google Slides or PowerPoint</div>
                    </div>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
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
