import { useState, useRef, useEffect } from "react";
import { useLocation } from "wouter";
import { useForm } from "react-hook-form";
import { useQuery } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { useFounderStore, FinancialBaseline, ExtractionResult } from "@/store/founderStore";
import {
  Building2,
  DollarSign,
  TrendingUp,
  Target,
  Sparkles,
  Send,
  Check,
  AlertCircle,
  Users,
  Calendar,
  Briefcase,
  Loader2,
  Info,
  FileText,
  FileSpreadsheet,
  FileUp,
  Eye,
  AlertTriangle,
  X,
  Download,
  HelpCircle,
  PieChart,
  Trash2,
  RefreshCw,
} from "lucide-react";
import { queryClient } from "@/lib/queryClient";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const dataInputSchema = z.object({
  companyName: z.string().min(1, "Company name is required"),
  description: z.string().optional(),
  foundingDate: z.string().optional().refine((val) => {
    if (!val) return true;
    const date = new Date(val);
    const today = new Date();
    today.setHours(23, 59, 59, 999);
    return date <= today;
  }, { message: "Founding date cannot be in the future" }),
  stage: z.string().min(1, "Stage is required"),
  industry: z.string().min(1, "Industry is required"),
  cashOnHand: z.coerce.number().min(0, "Cash must be positive"),
  monthlyRevenue: z.coerce.number().min(0, "Revenue must be positive"),
  monthlyExpenses: z.coerce.number().min(0, "Expenses must be positive"),
  payrollExpenses: z.coerce.number().min(0).optional(),
  marketingExpenses: z.coerce.number().min(0).optional(),
  operatingExpenses: z.coerce.number().min(0).optional(),
  cogsExpenses: z.coerce.number().min(0).optional(),
  otherOpexExpenses: z.coerce.number().min(0).optional(),
  growthRate: z.coerce.number().min(-100).max(1000),
  burnRate: z.coerce.number().optional(),
  employees: z.coerce.number().min(1, "Employee count must be at least 1").optional(),
  targetRunway: z.coerce.number().min(1).max(60).default(18),
  growthScenario: z.enum(["optimistic", "conservative", "worst-case"]).default("conservative"),
  fundingTarget: z.coerce.number().min(0).optional(),
  fundingTimeline: z.coerce.number().min(1).max(24).optional(),
});

type DataInputValues = z.infer<typeof dataInputSchema>;

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface FieldConfidence {
  value: number | string | null;
  confidence: number;
  evidence: string | null;
}

const SAMPLE_PROMPTS = [
  "What is our current runway given our burn rate?",
  "How should we adjust expenses to extend runway to 18 months?",
  "What growth rate do we need to reach profitability?",
  "Compare our metrics to typical Series A companies",
  "What are the biggest risks to our financial health?",
];

const STAGES = [
  { value: "pre-seed", label: "Pre-Seed" },
  { value: "seed", label: "Seed" },
  { value: "series-a", label: "Series A" },
  { value: "series-b", label: "Series B" },
  { value: "series-c", label: "Series C+" },
  { value: "growth", label: "Growth" },
];

const INDUSTRIES = [
  { value: "saas", label: "SaaS / Software" },
  { value: "fintech", label: "Fintech" },
  { value: "healthcare", label: "Healthcare / Biotech" },
  { value: "ecommerce", label: "E-commerce / Retail" },
  { value: "marketplace", label: "Marketplace" },
  { value: "ai-ml", label: "AI / Machine Learning" },
  { value: "consumer", label: "Consumer" },
  { value: "enterprise", label: "Enterprise" },
  { value: "other", label: "Other" },
];

const CONFIDENCE_THRESHOLD = 0.60;

interface FinancialBaselineResponse {
  hasBaseline: boolean;
  baseline: {
    cashOnHand: number;
    monthlyRevenue: number;
    totalMonthlyExpenses: number;
    monthlyGrowthRate: number;
    expenseBreakdown: {
      payroll: number;
      marketing: number;
      operating: number;
      cogs: number;
      otherOpex: number;
    };
    currency: string;
    asOfDate: string | null;
  } | null;
  extendedMetrics?: {
    headcount?: number;
    customers?: number;
    runwayMonths?: number;
  };
  company?: {
    name: string;
    industry: string;
  };
}

export default function DataInput() {
  const { toast } = useToast();
  const { 
    currentCompany, 
    token,
    financialBaseline,
    lastExtraction,
    extractionInProgress,
    setFinancialBaseline,
    setLastExtraction,
    setExtractionInProgress,
    clearFinancialBaseline,
  } = useFounderStore();
  const [activeTab, setActiveTab] = useState("company");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showExtractionDetails, setShowExtractionDetails] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploadType, setUploadType] = useState<'pdf' | 'excel'>('pdf');
  const [useVerificationFlow, setUseVerificationFlow] = useState(true);
  const [hasManualExpenseOverride, setHasManualExpenseOverride] = useState(false);
  const [hasLoadedFromBackend, setHasLoadedFromBackend] = useState(false);
  const [lastLoadedCompanyId, setLastLoadedCompanyId] = useState<number | null>(null);
  const [, navigate] = useLocation();
  const chatScrollRef = useRef<HTMLDivElement>(null);
  const pdfInputRef = useRef<HTMLInputElement>(null);
  const excelInputRef = useRef<HTMLInputElement>(null);

  const { data: backendBaseline, isLoading: isLoadingBaseline } = useQuery<FinancialBaselineResponse>({
    queryKey: ['/api/companies', currentCompany?.id, 'financials/baseline'],
    enabled: !!currentCompany?.id,
  });

  const form = useForm<DataInputValues>({
    resolver: zodResolver(dataInputSchema),
    defaultValues: {
      companyName: currentCompany?.name || "",
      description: "",
      foundingDate: "",
      stage: currentCompany?.stage || "seed",
      industry: currentCompany?.industry || "saas",
      cashOnHand: 0,
      monthlyRevenue: 0,
      monthlyExpenses: 0,
      payrollExpenses: 0,
      marketingExpenses: 0,
      operatingExpenses: 0,
      cogsExpenses: 0,
      otherOpexExpenses: 0,
      growthRate: 10,
      burnRate: 0,
      employees: 1,
      targetRunway: 18,
      growthScenario: "conservative",
      fundingTarget: 0,
      fundingTimeline: 12,
    },
  });

  useEffect(() => {
    if (currentCompany?.id && currentCompany.id !== lastLoadedCompanyId) {
      setHasLoadedFromBackend(false);
      setLastLoadedCompanyId(currentCompany.id);
    }
    if (currentCompany?.name) {
      form.setValue('companyName', currentCompany.name);
    }
    if (currentCompany?.stage) {
      form.setValue('stage', currentCompany.stage);
    }
    if (currentCompany?.industry) {
      form.setValue('industry', currentCompany.industry);
    }
  }, [currentCompany?.id, currentCompany?.name, currentCompany?.stage, currentCompany?.industry, lastLoadedCompanyId, form]);

  const watchedValues = form.watch();
  
  // Helper to safely parse numeric values (handles both number and string inputs)
  const parseNum = (val: unknown): number => {
    if (typeof val === 'number') return isNaN(val) ? 0 : val;
    if (typeof val === 'string') {
      const parsed = parseFloat(val.replace(/,/g, ''));
      return isNaN(parsed) ? 0 : parsed;
    }
    return 0;
  };
  
  const summedExpenses = parseNum(watchedValues.payrollExpenses) + 
                         parseNum(watchedValues.marketingExpenses) + 
                         parseNum(watchedValues.operatingExpenses) +
                         parseNum(watchedValues.cogsExpenses) +
                         parseNum(watchedValues.otherOpexExpenses);
  
  const effectiveExpenses = hasManualExpenseOverride 
    ? parseNum(watchedValues.monthlyExpenses)
    : (summedExpenses > 0 ? summedExpenses : parseNum(watchedValues.monthlyExpenses));
  
  const calculatedBurn = effectiveExpenses - parseNum(watchedValues.monthlyRevenue);
  const isProfitable = calculatedBurn < 0;
  const isSustainable = calculatedBurn <= 0;
  const calculatedRunway = calculatedBurn > 0 ? parseNum(watchedValues.cashOnHand) / calculatedBurn : null;

  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [chatMessages]);

  // Load financial data from backend when available (priority source of truth)
  useEffect(() => {
    if (backendBaseline?.hasBaseline && backendBaseline.baseline && !hasLoadedFromBackend) {
      const b = backendBaseline.baseline;
      form.setValue('cashOnHand', b.cashOnHand || 0);
      form.setValue('monthlyRevenue', b.monthlyRevenue || 0);
      form.setValue('monthlyExpenses', b.totalMonthlyExpenses || 0);
      form.setValue('growthRate', b.monthlyGrowthRate || 10);
      
      if (b.expenseBreakdown) {
        form.setValue('payrollExpenses', b.expenseBreakdown.payroll || 0);
        form.setValue('marketingExpenses', b.expenseBreakdown.marketing || 0);
        form.setValue('operatingExpenses', b.expenseBreakdown.operating || 0);
        form.setValue('cogsExpenses', b.expenseBreakdown.cogs || 0);
        form.setValue('otherOpexExpenses', b.expenseBreakdown.otherOpex || 0);
      }
      
      // Load headcount from extended metrics if available
      if (backendBaseline.extendedMetrics?.headcount) {
        form.setValue('employees', backendBaseline.extendedMetrics.headcount);
      }
      
      // Update company info if available
      if (backendBaseline.company?.industry) {
        form.setValue('industry', backendBaseline.company.industry);
      }
      
      setHasLoadedFromBackend(true);
      
      if (currentCompany?.name) {
        form.setValue('companyName', currentCompany.name);
      }
      if (currentCompany?.stage) {
        form.setValue('stage', currentCompany.stage);
      }
      
      setFinancialBaseline({
        cashOnHand: b.cashOnHand || 0,
        monthlyRevenue: b.monthlyRevenue || 0,
        totalMonthlyExpenses: b.totalMonthlyExpenses || 0,
        monthlyGrowthRate: b.monthlyGrowthRate || 0,
        expenseBreakdown: b.expenseBreakdown || {
          payroll: 0,
          marketing: 0,
          operating: 0,
          cogs: 0,
          otherOpex: 0,
        },
        hasManualExpenseOverride: false,
      });
    }
  }, [backendBaseline, hasLoadedFromBackend, form, setFinancialBaseline]);

  // Fallback: Load from local store if no backend data
  useEffect(() => {
    if (financialBaseline && !hasLoadedFromBackend && !backendBaseline?.hasBaseline) {
      if (financialBaseline.cashOnHand !== null) {
        form.setValue('cashOnHand', financialBaseline.cashOnHand);
      }
      if (financialBaseline.monthlyRevenue !== null) {
        form.setValue('monthlyRevenue', financialBaseline.monthlyRevenue);
      }
      if (financialBaseline.totalMonthlyExpenses !== null) {
        form.setValue('monthlyExpenses', financialBaseline.totalMonthlyExpenses);
      }
      if (financialBaseline.monthlyGrowthRate !== null) {
        form.setValue('growthRate', financialBaseline.monthlyGrowthRate);
      }
      if (financialBaseline.expenseBreakdown) {
        if (financialBaseline.expenseBreakdown.payroll !== null) {
          form.setValue('payrollExpenses', financialBaseline.expenseBreakdown.payroll);
        }
        if (financialBaseline.expenseBreakdown.marketing !== null) {
          form.setValue('marketingExpenses', financialBaseline.expenseBreakdown.marketing);
        }
        if (financialBaseline.expenseBreakdown.operating !== null) {
          form.setValue('operatingExpenses', financialBaseline.expenseBreakdown.operating);
        }
        if (financialBaseline.expenseBreakdown.cogs !== null) {
          form.setValue('cogsExpenses', financialBaseline.expenseBreakdown.cogs);
        }
        if (financialBaseline.expenseBreakdown.otherOpex !== null) {
          form.setValue('otherOpexExpenses', financialBaseline.expenseBreakdown.otherOpex);
        }
      }
      if (financialBaseline.hasManualExpenseOverride !== undefined) {
        setHasManualExpenseOverride(financialBaseline.hasManualExpenseOverride);
      }
    }
  }, [financialBaseline, form, hasLoadedFromBackend, backendBaseline]);

  const handleFileUpload = async (file: File, type: 'pdf' | 'excel') => {
    if (!currentCompany || !token) {
      toast({
        title: "Please select a company",
        description: "You need to select a company before uploading files",
        variant: "destructive",
      });
      return;
    }

    setExtractionInProgress(true);
    setUploadProgress(10);

    try {
      if (useVerificationFlow) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('company_id', currentCompany.id.toString());

        setUploadProgress(30);

        const endpoint = type === 'pdf' ? '/api/imports/pdf' : '/api/imports/excel';
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
          body: formData,
        });

        setUploadProgress(70);

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || 'Failed to process file');
        }

        const result = await response.json();
        setUploadProgress(100);

        toast({
          title: "File processed",
          description: "Redirecting to verification screen...",
        });

        navigate(`/data/verify/${result.id}`);
        return;
      }

      const formData = new FormData();
      formData.append('file', file);
      formData.append('fileType', type);
      formData.append('companyId', currentCompany.id.toString());

      setUploadProgress(30);

      const response = await fetch('/api/ingest/financials', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      setUploadProgress(70);

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to process file');
      }

      const result = await response.json();
      setUploadProgress(100);

      const normalized = result.normalized;
      const confidence = result.confidence || {};
      const missingFields = result.missingFields || [];

      const baseline: FinancialBaseline = {
        cashOnHand: normalized.cashOnHand,
        monthlyRevenue: normalized.monthlyRevenue,
        totalMonthlyExpenses: normalized.totalMonthlyExpenses,
        monthlyGrowthRate: normalized.monthlyGrowthRate,
        expenseBreakdown: {
          payroll: normalized.expenseBreakdown?.payroll ?? null,
          marketing: normalized.expenseBreakdown?.marketing || null,
          operating: normalized.expenseBreakdown?.operating || null,
          cogs: normalized.expenseBreakdown?.cogs || null,
          otherOpex: normalized.expenseBreakdown?.otherOpex || null,
        },
        currency: normalized.currency || 'USD',
        asOfDate: normalized.asOfDate,
        validationWarnings: result.validationWarnings || [],
        validationErrors: result.validationErrors || [],
        sources: result.sources || {},
      };

      setFinancialBaseline(baseline);

      const extraction: ExtractionResult = {
        extracted: result.extracted,
        normalized: baseline,
        missingFields,
        confidence,
        source: type,
        fileName: file.name,
        uploadId: result.uploadId,
      };
      setLastExtraction(extraction);

      applyExtractionToForm(baseline, confidence);

      if (missingFields.length > 0) {
        toast({
          title: "Partial extraction",
          description: `Some fields could not be detected: ${missingFields.join(', ')}. Please fill them manually.`,
          variant: "default",
        });
      } else {
        toast({
          title: "Extraction successful",
          description: `Financial metrics imported from ${type.toUpperCase()}`,
        });
      }

      setActiveTab('financials');
      setSelectedFile(null);

    } catch (error: any) {
      toast({
        title: "Extraction failed",
        description: error.message || "Failed to process the file",
        variant: "destructive",
      });
    } finally {
      setExtractionInProgress(false);
      setUploadProgress(0);
    }
  };

  const applyExtractionToForm = (baseline: FinancialBaseline, confidence: Record<string, number>) => {
    const applyValue = (field: keyof DataInputValues, value: number | null, confKey: string) => {
      if (value !== null && value !== undefined) {
        const conf = confidence[confKey] || 0;
        const currentValue = form.getValues(field);
        
        if (conf >= CONFIDENCE_THRESHOLD || !currentValue) {
          form.setValue(field, value as any);
        }
      }
    };

    applyValue('cashOnHand', baseline.cashOnHand, 'cashOnHand');
    applyValue('monthlyRevenue', baseline.monthlyRevenue, 'monthlyRevenue');
    applyValue('monthlyExpenses', baseline.totalMonthlyExpenses, 'totalMonthlyExpenses');
    applyValue('growthRate', baseline.monthlyGrowthRate, 'monthlyGrowthRate');
    
    if (baseline.expenseBreakdown) {
      applyValue('payrollExpenses', baseline.expenseBreakdown.payroll, 'payroll');
      applyValue('marketingExpenses', baseline.expenseBreakdown.marketing, 'marketing');
      applyValue('operatingExpenses', baseline.expenseBreakdown.operating, 'operating');
      applyValue('cogsExpenses', baseline.expenseBreakdown.cogs, 'cogs');
      applyValue('otherOpexExpenses', baseline.expenseBreakdown.otherOpex, 'otherOpex');
    }
  };

  const handleDrop = (e: React.DragEvent, type: 'pdf' | 'excel') => {
    e.preventDefault();
    setDragActive(false);
    
    const file = e.dataTransfer.files?.[0];
    if (file) {
      const ext = file.name.toLowerCase().split('.').pop();
      if (type === 'pdf' && ext === 'pdf') {
        handleFileUpload(file, 'pdf');
      } else if (type === 'excel' && (ext === 'xlsx' || ext === 'xls')) {
        handleFileUpload(file, 'excel');
      } else {
        toast({
          title: "Invalid file type",
          description: type === 'pdf' ? "Please upload a PDF file" : "Please upload an Excel file (.xlsx or .xls)",
          variant: "destructive",
        });
      }
    }
  };

  const handleSave = async (values: DataInputValues) => {
    if (!currentCompany || !token) {
      toast({
        title: "Please select a company",
        description: "You need to select a company before saving",
        variant: "destructive",
      });
      return;
    }

    setIsSaving(true);
    try {
      const breakdownSum = (values.payrollExpenses || 0) + 
                           (values.marketingExpenses || 0) + 
                           (values.operatingExpenses || 0) +
                           (values.cogsExpenses || 0) +
                           (values.otherOpexExpenses || 0);
      
      const totalExpenses = hasManualExpenseOverride 
        ? (values.monthlyExpenses || 0)
        : (breakdownSum > 0 ? breakdownSum : (values.monthlyExpenses || 0));
      
      const baseline = {
        cashOnHand: values.cashOnHand,
        monthlyRevenue: values.monthlyRevenue,
        totalMonthlyExpenses: totalExpenses,
        monthlyGrowthRate: values.growthRate,
        expenseBreakdown: {
          payroll: values.payrollExpenses || null,
          marketing: values.marketingExpenses || null,
          operating: values.operatingExpenses || null,
          cogs: values.cogsExpenses || null,
          otherOpex: values.otherOpexExpenses || null,
        },
        hasManualExpenseOverride: hasManualExpenseOverride,
        currency: 'USD',
        asOfDate: new Date().toISOString().split('T')[0],
      };

      const response = await fetch(`/api/companies/${currentCompany.id}/financials/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(baseline),
      });

      if (!response.ok) {
        throw new Error('Failed to save');
      }

      setFinancialBaseline(baseline);

      toast({
        title: "Data saved",
        description: "Your company and financial data has been saved successfully",
      });
    } catch (error) {
      toast({
        title: "Failed to save",
        description: "There was an error saving your data",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const sendMessage = async (message: string) => {
    if (!message.trim() || isStreaming) return;

    const userMessage: ChatMessage = { role: "user", content: message };
    setChatMessages((prev) => [...prev, userMessage]);
    setChatInput("");
    setIsStreaming(true);

    const assistantMessage: ChatMessage = { role: "assistant", content: "" };
    setChatMessages((prev) => [...prev, assistantMessage]);

    try {
      const response = await fetch("/api/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [...chatMessages, userMessage].map((m) => ({
            role: m.role,
            content: m.content,
          })),
          context: {
            companyName: watchedValues.companyName,
            industry: watchedValues.industry,
            stage: watchedValues.stage,
            cashOnHand: watchedValues.cashOnHand,
            monthlyRevenue: watchedValues.monthlyRevenue,
            monthlyExpenses: watchedValues.monthlyExpenses,
            growthRate: watchedValues.growthRate,
            employees: watchedValues.employees,
            targetRunway: watchedValues.targetRunway,
          },
        }),
      });

      if (!response.ok) throw new Error("Failed to get response");

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split("\n");

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.content) {
                  setChatMessages((prev) => {
                    const updated = [...prev];
                    const lastMsg = updated[updated.length - 1];
                    if (lastMsg && lastMsg.role === "assistant") {
                      lastMsg.content += data.content;
                    }
                    return updated;
                  });
                }
              } catch {}
            }
          }
        }
      }
    } catch (error) {
      setChatMessages((prev) => {
        const updated = [...prev];
        const lastMsg = updated[updated.length - 1];
        if (lastMsg && lastMsg.role === "assistant") {
          lastMsg.content = "Sorry, I couldn't process your request. Please try again.";
        }
        return updated;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  const formatCurrency = (value: number) => {
    if (value === null || value === undefined || isNaN(value)) return 'N/A';
    
    const absValue = Math.abs(value);
    const sign = value < 0 ? '-' : '';
    
    if (absValue >= 1_000_000_000) {
      const billions = absValue / 1_000_000_000;
      return `${sign}$${billions.toFixed(1)}B`;
    } else if (absValue >= 1_000_000) {
      const millions = absValue / 1_000_000;
      return `${sign}$${millions.toFixed(1)}M`;
    } else if (absValue >= 1_000) {
      const thousands = absValue / 1_000;
      return `${sign}$${thousands.toFixed(1)}K`;
    } else if (absValue > 0) {
      return `${sign}$${absValue.toFixed(0)}`;
    }
    return '$0';
  };

  const getConfidenceBadge = (fieldKey: string) => {
    if (!lastExtraction) return null;
    const conf = lastExtraction.confidence[fieldKey];
    if (conf === undefined) return null;
    
    if (conf < CONFIDENCE_THRESHOLD) {
      return (
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge variant="outline" className="ml-2 text-amber-500 border-amber-500">
              <AlertTriangle className="h-3 w-3 mr-1" />
              Low confidence
            </Badge>
          </TooltipTrigger>
          <TooltipContent>
            <p>This value was extracted with {Math.round(conf * 100)}% confidence. Please verify.</p>
          </TooltipContent>
        </Tooltip>
      );
    }
    return null;
  };

  const getMissingFieldHint = (fieldKey: string) => {
    if (!lastExtraction) return null;
    if (lastExtraction.missingFields.includes(fieldKey)) {
      return (
        <p className="text-xs text-amber-500 mt-1">Not detected from file - please fill manually</p>
      );
    }
    return null;
  };

  const getIndustryEstimateSuggestion = (fieldKey: string) => {
    const revenue = watchedValues.monthlyRevenue || 0;
    const expenses = watchedValues.monthlyExpenses || 0;
    const operating = watchedValues.operatingExpenses;
    
    let suggestedValue: number | null = null;
    let explanation = "";
    let currentValue: number | undefined;
    let fieldName: keyof DataInputValues;

    switch (fieldKey) {
      case 'payrollExpenses':
        fieldName = 'payrollExpenses';
        currentValue = watchedValues.payrollExpenses;
        if (operating && operating > 0) {
          suggestedValue = Math.round(operating * 0.5);
          explanation = "~50% of operating expenses (industry standard)";
        } else if (expenses > 0) {
          suggestedValue = Math.round(expenses * 0.5);
          explanation = "~50% of total expenses (industry standard)";
        }
        break;
      case 'operatingExpenses':
        fieldName = 'operatingExpenses';
        currentValue = watchedValues.operatingExpenses;
        if (revenue > 0) {
          suggestedValue = Math.round(revenue * 0.3);
          explanation = "~30% of revenue (industry standard)";
        } else if (expenses > 0) {
          suggestedValue = Math.round(expenses * 0.3);
          explanation = "~30% of total expenses (industry standard)";
        }
        break;
      case 'cashOnHand':
        fieldName = 'cashOnHand';
        currentValue = watchedValues.cashOnHand;
        if (expenses > 0 && (!currentValue || currentValue === 0)) {
          suggestedValue = expenses * 6;
          explanation = "6 months of expenses (healthy runway)";
        }
        break;
      case 'growthRate':
        fieldName = 'growthRate';
        currentValue = watchedValues.growthRate;
        if (!currentValue || currentValue === 0) {
          suggestedValue = 5;
          explanation = "5% MoM (conservative SaaS benchmark)";
        }
        break;
      default:
        return null;
    }

    if (suggestedValue === null || (currentValue && currentValue > 0)) {
      return null;
    }

    return (
      <div className="flex items-center gap-2 mt-1">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-auto py-0.5 px-2 text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
          onClick={() => form.setValue(fieldName, suggestedValue as any)}
          data-testid={`button-suggest-${fieldKey}`}
        >
          <Sparkles className="h-3 w-3 mr-1" />
          Use {fieldKey === 'growthRate' ? `${suggestedValue}%` : formatCurrency(suggestedValue!)}
        </Button>
        <span className="text-xs text-muted-foreground">{explanation}</span>
      </div>
    );
  };

  const renderFileUploadZone = (type: 'pdf' | 'excel') => {
    const accept = type === 'pdf' ? '.pdf' : '.xlsx,.xls';
    const icon = type === 'pdf' ? <FileText className="h-12 w-12 text-muted-foreground" /> : <FileSpreadsheet className="h-12 w-12 text-muted-foreground" />;
    const label = type === 'pdf' ? 'PDF Report' : 'Excel Spreadsheet';
    const inputRef = type === 'pdf' ? pdfInputRef : excelInputRef;

    return (
      <Card className="overflow-visible">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            {type === 'pdf' ? <FileText className="h-5 w-5" /> : <FileSpreadsheet className="h-5 w-5" />}
            Upload {label}
          </CardTitle>
          <CardDescription>
            Upload a Termina {type === 'pdf' ? 'PDF report' : 'Excel export'} to auto-populate financial metrics
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'
            } ${extractionInProgress ? 'opacity-50 pointer-events-none' : ''}`}
            onDrop={(e) => handleDrop(e, type)}
            onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={() => setDragActive(false)}
          >
            <input
              ref={inputRef}
              type="file"
              accept={accept}
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFileUpload(file, type);
              }}
              disabled={extractionInProgress}
              data-testid={`input-file-${type}`}
            />
            
            {extractionInProgress ? (
              <div className="space-y-4">
                <Loader2 className="h-12 w-12 text-primary mx-auto animate-spin" />
                <p className="text-sm font-medium">Extracting metrics...</p>
                <Progress value={uploadProgress} className="w-48 mx-auto" />
              </div>
            ) : (
              <>
                {icon}
                <p className="mt-4 text-sm text-muted-foreground">
                  Drag and drop your {label.toLowerCase()} here, or
                </p>
                <Button
                  type="button"
                  variant="outline"
                  className="mt-2"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    inputRef.current?.click();
                  }}
                  data-testid={`button-browse-${type}`}
                >
                  <FileUp className="h-4 w-4 mr-2" />
                  Browse Files
                </Button>
                <p className="mt-2 text-xs text-muted-foreground">
                  {type === 'pdf' ? 'PDF files up to 10MB' : 'Excel files (.xlsx, .xls) up to 20MB'}
                </p>
                <div className="mt-4 pt-3 border-t border-dashed">
                  <p className="text-xs text-muted-foreground mb-2">Need a sample file?</p>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="text-xs gap-1"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          toast({
                            title: type === 'pdf' ? "Sample PDF Format" : "Sample Excel Format",
                            description: type === 'pdf' 
                              ? "PDF should contain: Company summary, Cash position, Monthly P&L, Revenue breakdown, and Expense categories. Termina-style reports work best."
                              : "Excel should have columns: Date, Category (Revenue/Expense), Amount, Description. Include sheets for P&L and Balance Sheet.",
                          });
                        }}
                        data-testid={`button-sample-${type}`}
                      >
                        <Download className="h-3 w-3" />
                        View {type === 'pdf' ? 'PDF' : 'Excel'} Format Guide
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p>{type === 'pdf' 
                        ? "Click to see the expected PDF format for financial reports"
                        : "Click to see the expected Excel spreadsheet structure"
                      }</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
              </>
            )}
          </div>

          {lastExtraction && lastExtraction.source === type && (
            <div className="mt-4 p-4 rounded-lg bg-muted/50">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-green-500" />
                  <span className="text-sm font-medium">Last extraction: {lastExtraction.fileName}</span>
                </div>
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={() => setShowExtractionDetails(true)}
                  data-testid="button-view-extraction"
                >
                  <Eye className="h-4 w-4 mr-1" />
                  View Details
                </Button>
              </div>
              {lastExtraction.missingFields.length > 0 && (
                <p className="text-xs text-amber-500">
                  <AlertTriangle className="h-3 w-3 inline mr-1" />
                  Missing fields: {lastExtraction.missingFields.join(', ')}
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  const handleClearCache = () => {
    // Clear React Query cache
    queryClient.clear();
    
    // Clear Zustand persisted state for financial data
    clearFinancialBaseline();
    setLastExtraction(null);
    
    // Clear localStorage founder-storage
    localStorage.removeItem('founder-storage');
    
    toast({
      title: "Cache Cleared",
      description: "All cached data has been cleared. Please re-upload your files.",
    });
    
    // Force reload to ensure fresh state
    window.location.reload();
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Data Input</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Enter your company information and financial data for analysis
          </p>
        </div>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleClearCache}
              data-testid="button-clear-cache"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Clear Cache
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>Clear all cached extraction data and reload</p>
          </TooltipContent>
        </Tooltip>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-6">
              <TabsTrigger value="csv-upload" data-testid="tab-csv-upload">
                <FileUp className="h-4 w-4 mr-2" />
                CSV
              </TabsTrigger>
              <TabsTrigger value="pdf-upload" data-testid="tab-pdf-upload">
                <FileText className="h-4 w-4 mr-2" />
                PDF
              </TabsTrigger>
              <TabsTrigger value="excel-upload" data-testid="tab-excel-upload">
                <FileSpreadsheet className="h-4 w-4 mr-2" />
                Excel
              </TabsTrigger>
              <TabsTrigger value="company" data-testid="tab-company">
                <Building2 className="h-4 w-4 mr-2" />
                Company
              </TabsTrigger>
              <TabsTrigger value="financials" data-testid="tab-financials">
                <DollarSign className="h-4 w-4 mr-2" />
                Financials
              </TabsTrigger>
              <TabsTrigger value="goals" data-testid="tab-goals">
                <Target className="h-4 w-4 mr-2" />
                Goals
              </TabsTrigger>
            </TabsList>

            <TabsContent value="csv-upload" className="mt-6">
              {currentCompany ? (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <FileUp className="h-5 w-5 text-primary" />
                      Import CSV Data
                    </CardTitle>
                    <CardDescription>
                      Upload a CSV file with your financial data. We'll automatically detect columns and validate the data.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <Card className="border-dashed hover-elevate cursor-pointer" onClick={() => document.getElementById('csv-financial-input')?.click()}>
                        <CardContent className="p-4 text-center">
                          <DollarSign className="h-8 w-8 mx-auto mb-2 text-emerald-500" />
                          <p className="font-medium">Financial Data</p>
                          <p className="text-xs text-muted-foreground mt-1">Revenue, expenses, P&L</p>
                          <input
                            id="csv-financial-input"
                            type="file"
                            accept=".csv"
                            className="hidden"
                            onChange={async (e) => {
                              const file = e.target.files?.[0];
                              if (file && currentCompany && token) {
                                const formData = new FormData();
                                formData.append('file', file);
                                try {
                                  const res = await fetch(`/api/companies/${currentCompany.id}/datasets/upload?dataset_type=financial`, {
                                    method: 'POST',
                                    headers: { 'Authorization': `Bearer ${token}` },
                                    body: formData
                                  });
                                  if (res.ok) {
                                    const data = await res.json();
                                    toast({ title: 'CSV imported successfully', description: `${data.row_count} records processed` });
                                    queryClient.invalidateQueries({ queryKey: ['truth', currentCompany.id] });
                                  } else {
                                    const err = await res.json();
                                    toast({ title: 'Import failed', description: err.detail || 'Check file format', variant: 'destructive' });
                                  }
                                } catch {
                                  toast({ title: 'Import failed', description: 'Network error', variant: 'destructive' });
                                }
                              }
                            }}
                            data-testid="input-csv-financial"
                          />
                        </CardContent>
                      </Card>
                      <Card className="border-dashed hover-elevate cursor-pointer" onClick={() => document.getElementById('csv-transactions-input')?.click()}>
                        <CardContent className="p-4 text-center">
                          <TrendingUp className="h-8 w-8 mx-auto mb-2 text-blue-500" />
                          <p className="font-medium">Transactions</p>
                          <p className="text-xs text-muted-foreground mt-1">Customer payments, invoices</p>
                          <input
                            id="csv-transactions-input"
                            type="file"
                            accept=".csv"
                            className="hidden"
                            onChange={async (e) => {
                              const file = e.target.files?.[0];
                              if (file && currentCompany && token) {
                                const formData = new FormData();
                                formData.append('file', file);
                                try {
                                  const res = await fetch(`/api/companies/${currentCompany.id}/datasets/upload?dataset_type=transactions`, {
                                    method: 'POST',
                                    headers: { 'Authorization': `Bearer ${token}` },
                                    body: formData
                                  });
                                  if (res.ok) {
                                    const data = await res.json();
                                    toast({ title: 'Transactions imported', description: `${data.row_count} records processed` });
                                  } else {
                                    const err = await res.json();
                                    toast({ title: 'Import failed', description: err.detail || 'Check file format', variant: 'destructive' });
                                  }
                                } catch {
                                  toast({ title: 'Import failed', description: 'Network error', variant: 'destructive' });
                                }
                              }
                            }}
                            data-testid="input-csv-transactions"
                          />
                        </CardContent>
                      </Card>
                      <Card className="border-dashed hover-elevate cursor-pointer" onClick={() => document.getElementById('csv-customers-input')?.click()}>
                        <CardContent className="p-4 text-center">
                          <Users className="h-8 w-8 mx-auto mb-2 text-purple-500" />
                          <p className="font-medium">Customers</p>
                          <p className="text-xs text-muted-foreground mt-1">Customer list, segments</p>
                          <input
                            id="csv-customers-input"
                            type="file"
                            accept=".csv"
                            className="hidden"
                            onChange={async (e) => {
                              const file = e.target.files?.[0];
                              if (file && currentCompany && token) {
                                const formData = new FormData();
                                formData.append('file', file);
                                try {
                                  const res = await fetch(`/api/companies/${currentCompany.id}/datasets/upload?dataset_type=customers`, {
                                    method: 'POST',
                                    headers: { 'Authorization': `Bearer ${token}` },
                                    body: formData
                                  });
                                  if (res.ok) {
                                    const data = await res.json();
                                    toast({ title: 'Customers imported', description: `${data.row_count} records processed` });
                                  } else {
                                    const err = await res.json();
                                    toast({ title: 'Import failed', description: err.detail || 'Check file format', variant: 'destructive' });
                                  }
                                } catch {
                                  toast({ title: 'Import failed', description: 'Network error', variant: 'destructive' });
                                }
                              }
                            }}
                            data-testid="input-csv-customers"
                          />
                        </CardContent>
                      </Card>
                    </div>
                    <div className="bg-muted/30 rounded-lg p-4 mt-4">
                      <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                        <Info className="h-4 w-4" />
                        CSV Format Requirements
                      </h4>
                      <ul className="text-xs text-muted-foreground space-y-1">
                        <li><strong>Financial:</strong> period_start, period_end, revenue, cogs, opex, payroll, cash_balance</li>
                        <li><strong>Transactions:</strong> date, customer_id, amount, description, type</li>
                        <li><strong>Customers:</strong> customer_id, name, segment, start_date, mrr</li>
                      </ul>
                      <Button variant="ghost" size="sm" className="px-0 mt-2 text-xs h-auto" onClick={() => {
                        toast({ title: 'Sample CSV templates', description: 'Download sample CSVs from the Help section' });
                      }}>
                        <Download className="h-3 w-3 mr-1" />
                        Download sample templates
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardContent className="py-8 text-center text-muted-foreground">
                    Please select a company first to import CSV data
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="pdf-upload" className="mt-6">
              {currentCompany ? renderFileUploadZone('pdf') : (
                <Card>
                  <CardContent className="py-8 text-center text-muted-foreground">
                    Please select a company first to upload a PDF report
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="excel-upload" className="mt-6">
              {currentCompany ? renderFileUploadZone('excel') : (
                <Card>
                  <CardContent className="py-8 text-center text-muted-foreground">
                    Please select a company first to upload an Excel file
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <Form {...form}>
              <form onSubmit={form.handleSubmit(handleSave, (errors) => {
                const errorFields = Object.keys(errors);
                if (errorFields.length > 0) {
                  const firstError = errors[errorFields[0] as keyof DataInputValues];
                  toast({
                    title: "Please fix form errors",
                    description: firstError?.message || `${errorFields.length} field(s) need attention`,
                    variant: "destructive",
                  });
                }
              })}>
                <TabsContent value="company" className="mt-6">
                  <Card className="overflow-visible">
                    <CardHeader>
                      <CardTitle className="text-lg">Company Information</CardTitle>
                      <CardDescription>
                        Basic details about your company
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <FormField
                          control={form.control}
                          name="companyName"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>Company Name</FormLabel>
                              <FormControl>
                                <div className="relative">
                                  <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                  <Input
                                    className="pl-9"
                                    placeholder="Acme Inc."
                                    {...field}
                                    data-testid="input-company-name"
                                  />
                                </div>
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name="foundingDate"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>Founding Date</FormLabel>
                              <FormControl>
                                <div className="relative">
                                  <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                  <Input
                                    type="date"
                                    className="pl-9"
                                    {...field}
                                    data-testid="input-founding-date"
                                  />
                                </div>
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name="stage"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>Stage</FormLabel>
                              <Select onValueChange={field.onChange} defaultValue={field.value}>
                                <FormControl>
                                  <SelectTrigger data-testid="select-stage">
                                    <Briefcase className="h-4 w-4 mr-2 text-muted-foreground" />
                                    <SelectValue placeholder="Select stage" />
                                  </SelectTrigger>
                                </FormControl>
                                <SelectContent>
                                  {STAGES.map((stage) => (
                                    <SelectItem key={stage.value} value={stage.value}>
                                      {stage.label}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name="industry"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>Industry</FormLabel>
                              <Select onValueChange={field.onChange} defaultValue={field.value}>
                                <FormControl>
                                  <SelectTrigger data-testid="select-industry">
                                    <SelectValue placeholder="Select industry" />
                                  </SelectTrigger>
                                </FormControl>
                                <SelectContent>
                                  {INDUSTRIES.map((industry) => (
                                    <SelectItem key={industry.value} value={industry.value}>
                                      {industry.label}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                      </div>
                      <FormField
                        control={form.control}
                        name="description"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Description</FormLabel>
                            <FormControl>
                              <Textarea
                                placeholder="Brief description of what your company does..."
                                className="resize-none"
                                rows={3}
                                {...field}
                                data-testid="input-description"
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name="employees"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="flex items-center gap-1.5">
                              Number of Employees
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <button type="button" className="inline-flex">
                                    <Info className="h-3.5 w-3.5 text-muted-foreground" />
                                  </button>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>Full-time equivalent employees</p>
                                </TooltipContent>
                              </Tooltip>
                            </FormLabel>
                            <FormControl>
                              <div className="relative">
                                <Users className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                  type="number"
                                  className="pl-9"
                                  placeholder="10"
                                  {...field}
                                  data-testid="input-employees"
                                />
                              </div>
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="financials" className="mt-6">
                  <Card className="overflow-visible">
                    <CardHeader>
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <div>
                          <CardTitle className="text-lg">Financial Metrics</CardTitle>
                          <CardDescription>
                            Your current financial position and performance
                          </CardDescription>
                        </div>
                        {lastExtraction && (
                          <Badge variant="secondary" className="gap-1">
                            <FileUp className="h-3 w-3" />
                            Imported from {lastExtraction.source.toUpperCase()}
                          </Badge>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <FormField
                          control={form.control}
                          name="cashOnHand"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="flex items-center gap-1.5 flex-wrap">
                                Cash on Hand ($)
                                {getConfidenceBadge('cashOnHand')}
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <button type="button" className="inline-flex">
                                      <Info className="h-3.5 w-3.5 text-muted-foreground" />
                                    </button>
                                  </TooltipTrigger>
                                  <TooltipContent className="max-w-xs">
                                    <p>Total liquid cash available in bank accounts</p>
                                  </TooltipContent>
                                </Tooltip>
                              </FormLabel>
                              <FormControl>
                                <div className="relative">
                                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                  <Input
                                    type="number"
                                    className="pl-9 font-mono"
                                    placeholder="500000"
                                    {...field}
                                    data-testid="input-cash"
                                  />
                                </div>
                              </FormControl>
                              <FormDescription>Current bank balance</FormDescription>
                              {getIndustryEstimateSuggestion('cashOnHand')}
                              {getMissingFieldHint('cashOnHand')}
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name="monthlyRevenue"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="flex items-center gap-1.5 flex-wrap">
                                Monthly Revenue ($)
                                {getConfidenceBadge('monthlyRevenue')}
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <button type="button" className="inline-flex">
                                      <Info className="h-3.5 w-3.5 text-muted-foreground" />
                                    </button>
                                  </TooltipTrigger>
                                  <TooltipContent className="max-w-xs">
                                    <p>Average monthly recurring revenue (MRR)</p>
                                  </TooltipContent>
                                </Tooltip>
                              </FormLabel>
                              <FormControl>
                                <div className="relative">
                                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                  <Input
                                    type="number"
                                    className="pl-9 font-mono"
                                    placeholder="50000"
                                    {...field}
                                    data-testid="input-revenue"
                                  />
                                </div>
                              </FormControl>
                              <FormDescription>Recurring monthly income</FormDescription>
                              {getMissingFieldHint('monthlyRevenue')}
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name="monthlyExpenses"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="flex items-center gap-1.5 flex-wrap">
                                Total Monthly Expenses ($)
                                {getConfidenceBadge('totalMonthlyExpenses')}
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <button type="button" className="inline-flex">
                                      <Info className="h-3.5 w-3.5 text-muted-foreground" />
                                    </button>
                                  </TooltipTrigger>
                                  <TooltipContent className="max-w-xs">
                                    <p>All monthly operating costs combined</p>
                                  </TooltipContent>
                                </Tooltip>
                              </FormLabel>
                              <FormControl>
                                <div className="relative">
                                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                  <Input
                                    type="number"
                                    className="pl-9 font-mono"
                                    placeholder="80000"
                                    {...field}
                                    onChange={(e) => {
                                      field.onChange(e);
                                      setHasManualExpenseOverride(true);
                                    }}
                                    data-testid="input-expenses"
                                  />
                                </div>
                              </FormControl>
                              <FormDescription>
                                {hasManualExpenseOverride 
                                  ? "Manual override active" 
                                  : summedExpenses > 0 
                                    ? `Computed from breakdown: ${formatCurrency(summedExpenses)}`
                                    : "Total monthly operating costs"}
                              </FormDescription>
                              {getMissingFieldHint('totalMonthlyExpenses')}
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name="growthRate"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="flex items-center gap-1.5 flex-wrap">
                                Monthly Growth Rate (%)
                                {getConfidenceBadge('monthlyGrowthRate')}
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <button type="button" className="inline-flex">
                                      <Info className="h-3.5 w-3.5 text-muted-foreground" />
                                    </button>
                                  </TooltipTrigger>
                                  <TooltipContent className="max-w-xs">
                                    <p>Month-over-month revenue growth percentage</p>
                                  </TooltipContent>
                                </Tooltip>
                              </FormLabel>
                              <FormControl>
                                <div className="relative">
                                  <TrendingUp className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                  <Input
                                    type="number"
                                    className="pl-9 font-mono"
                                    placeholder="10"
                                    {...field}
                                    data-testid="input-growth"
                                  />
                                </div>
                              </FormControl>
                              <FormDescription>MoM revenue growth</FormDescription>
                              {getIndustryEstimateSuggestion('growthRate')}
                              {getMissingFieldHint('monthlyGrowthRate')}
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                      </div>

                      <div className="border-t pt-4">
                        <h4 className="text-sm font-medium mb-3">Expense Breakdown (Optional)</h4>
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                          <FormField
                            control={form.control}
                            name="payrollExpenses"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className="flex items-center gap-1.5 flex-wrap">
                                  Payroll ($)
                                  {getConfidenceBadge('payroll')}
                                </FormLabel>
                                <FormControl>
                                  <Input
                                    type="number"
                                    className="font-mono"
                                    placeholder="50000"
                                    {...field}
                                    onChange={(e) => {
                                      field.onChange(e);
                                      setHasManualExpenseOverride(false);
                                    }}
                                    data-testid="input-payroll"
                                  />
                                </FormControl>
                                {getIndustryEstimateSuggestion('payrollExpenses')}
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                          <FormField
                            control={form.control}
                            name="marketingExpenses"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className="flex items-center gap-1.5 flex-wrap">
                                  Marketing ($)
                                  {getConfidenceBadge('marketing')}
                                </FormLabel>
                                <FormControl>
                                  <Input
                                    type="number"
                                    className="font-mono"
                                    placeholder="15000"
                                    {...field}
                                    onChange={(e) => {
                                      field.onChange(e);
                                      setHasManualExpenseOverride(false);
                                    }}
                                    data-testid="input-marketing"
                                  />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                          <FormField
                            control={form.control}
                            name="operatingExpenses"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className="flex items-center gap-1.5 flex-wrap">
                                  Operating ($)
                                  {getConfidenceBadge('operating')}
                                </FormLabel>
                                <FormControl>
                                  <Input
                                    type="number"
                                    className="font-mono"
                                    placeholder="15000"
                                    {...field}
                                    onChange={(e) => {
                                      field.onChange(e);
                                      setHasManualExpenseOverride(false);
                                    }}
                                    data-testid="input-operating"
                                  />
                                </FormControl>
                                {getIndustryEstimateSuggestion('operatingExpenses')}
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                          <FormField
                            control={form.control}
                            name="cogsExpenses"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className="flex items-center gap-1.5 flex-wrap">
                                  COGS ($)
                                  {getConfidenceBadge('cogs')}
                                </FormLabel>
                                <FormControl>
                                  <Input
                                    type="number"
                                    className="font-mono"
                                    placeholder="0"
                                    {...field}
                                    onChange={(e) => {
                                      field.onChange(e);
                                      setHasManualExpenseOverride(false);
                                    }}
                                    data-testid="input-cogs"
                                  />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                          <FormField
                            control={form.control}
                            name="otherOpexExpenses"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className="flex items-center gap-1.5 flex-wrap">
                                  Other ($)
                                  {getConfidenceBadge('otherOpex')}
                                </FormLabel>
                                <FormControl>
                                  <Input
                                    type="number"
                                    className="font-mono"
                                    placeholder="0"
                                    {...field}
                                    onChange={(e) => {
                                      field.onChange(e);
                                      setHasManualExpenseOverride(false);
                                    }}
                                    data-testid="input-other-opex"
                                  />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                        </div>
                      </div>

                      <div className="bg-muted/50 rounded-md p-4 space-y-4">
                        <h4 className="text-sm font-medium flex items-center gap-2">
                          <PieChart className="h-4 w-4 text-primary" />
                          Real-Time Financial Summary
                        </h4>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <div className="flex items-center gap-1">
                              <p className="text-xs text-muted-foreground">Net Burn Rate</p>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <button type="button" className="inline-flex">
                                    <HelpCircle className="h-3 w-3 text-muted-foreground" />
                                  </button>
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs">
                                  <p><strong>Net Burn Rate</strong> = Monthly Expenses - Monthly Revenue</p>
                                  <p className="mt-1 text-xs">This is how much cash you consume each month after accounting for revenue. A negative burn means you're profitable.</p>
                                </TooltipContent>
                              </Tooltip>
                            </div>
                            <p className="text-lg font-mono font-semibold" data-testid="text-burn-rate">
                              {calculatedBurn > 0 ? (
                                <span className="text-amber-500">{formatCurrency(calculatedBurn)}/mo</span>
                              ) : calculatedBurn < 0 ? (
                                <span className="text-emerald-500">+{formatCurrency(Math.abs(calculatedBurn))}/mo (Net positive)</span>
                              ) : (
                                <>$0/mo (Break-even)</>
                              )}
                            </p>
                          </div>
                          <div>
                            <div className="flex items-center gap-1">
                              <p className="text-xs text-muted-foreground">Current Runway</p>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <button type="button" className="inline-flex">
                                    <HelpCircle className="h-3 w-3 text-muted-foreground" />
                                  </button>
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs">
                                  <p><strong>Runway</strong> = Cash on Hand ÷ Net Burn Rate</p>
                                  <p className="mt-1 text-xs">The number of months your company can operate before running out of cash at the current burn rate.</p>
                                </TooltipContent>
                              </Tooltip>
                            </div>
                            <p className="text-lg font-mono font-semibold" data-testid="text-runway">
                              {calculatedBurn > 0 && watchedValues.cashOnHand ? (
                                <span className={calculatedRunway && calculatedRunway < 12 ? "text-red-500" : calculatedRunway && calculatedRunway < 18 ? "text-amber-500" : "text-emerald-500"}>
                                  {calculatedRunway?.toFixed(1)} months
                                </span>
                              ) : calculatedBurn <= 0 ? (
                                <span className="text-emerald-500">Profitable / Sustainable</span>
                              ) : (
                                "N/A"
                              )}
                            </p>
                          </div>
                        </div>
                        
                        {summedExpenses > 0 && (
                          <div className="pt-3 border-t">
                            <div className="flex items-center gap-1 mb-2">
                              <p className="text-xs text-muted-foreground">Expense Breakdown</p>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <button type="button" className="inline-flex">
                                    <HelpCircle className="h-3 w-3 text-muted-foreground" />
                                  </button>
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs">
                                  <p>Visual breakdown of your monthly expenses by category. Larger bars indicate higher spending.</p>
                                </TooltipContent>
                              </Tooltip>
                            </div>
                            <div className="space-y-2">
                              {[
                                { label: "Payroll", value: watchedValues.payrollExpenses || 0, color: "bg-blue-500" },
                                { label: "Marketing", value: watchedValues.marketingExpenses || 0, color: "bg-purple-500" },
                                { label: "Operating", value: watchedValues.operatingExpenses || 0, color: "bg-teal-500" },
                                { label: "COGS", value: watchedValues.cogsExpenses || 0, color: "bg-orange-500" },
                                { label: "Other", value: watchedValues.otherOpexExpenses || 0, color: "bg-gray-500" },
                              ].filter(item => item.value > 0).map(item => (
                                <div key={item.label} className="flex items-center gap-2">
                                  <span className="text-xs w-16 text-muted-foreground">{item.label}</span>
                                  <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                                    <div 
                                      className={`h-full ${item.color} transition-all duration-300`}
                                      style={{ width: `${Math.min((item.value / summedExpenses) * 100, 100)}%` }}
                                    />
                                  </div>
                                  <span className="text-xs font-mono w-16 text-right">{formatCurrency(item.value)}</span>
                                  <span className="text-xs text-muted-foreground w-10 text-right">
                                    {((item.value / summedExpenses) * 100).toFixed(0)}%
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {financialBaseline?.validationWarnings && financialBaseline.validationWarnings.length > 0 && (
                          <div className="mt-4 pt-4 border-t">
                            <div className="flex items-center gap-2 mb-3">
                              <AlertTriangle className="h-4 w-4 text-amber-500" />
                              <h4 className="text-sm font-medium">Data Quality Warnings</h4>
                            </div>
                            <div className="space-y-2">
                              {financialBaseline.validationWarnings.map((warning, idx) => (
                                <div 
                                  key={idx} 
                                  className={`p-3 rounded-md text-sm ${
                                    warning.severity === 'error' 
                                      ? 'bg-red-500/10 text-red-600 dark:text-red-400' 
                                      : warning.severity === 'warn'
                                      ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                                      : 'bg-blue-500/10 text-blue-600 dark:text-blue-400'
                                  }`}
                                  data-testid={`warning-${warning.code}`}
                                >
                                  <div className="flex items-start gap-2">
                                    {warning.severity === 'error' ? (
                                      <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                                    ) : (
                                      <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
                                    )}
                                    <div>
                                      <p className="font-medium">{warning.code.replace(/_/g, ' ')}</p>
                                      <p className="text-xs mt-0.5 opacity-80">{warning.message}</p>
                                      {warning.code === 'PAYROLL_NOT_FOUND' && (
                                        <Button
                                          type="button"
                                          variant="ghost"
                                          size="sm"
                                          className="p-0 h-auto text-xs mt-1 underline"
                                          onClick={() => {
                                            setActiveTab('financials');
                                          }}
                                          data-testid="button-add-payroll"
                                        >
                                          Add payroll manually
                                        </Button>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="goals" className="mt-6">
                  <Card className="overflow-visible">
                    <CardHeader>
                      <CardTitle className="text-lg">Goals and Assumptions</CardTitle>
                      <CardDescription>
                        Set your targets and scenario planning parameters
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <FormField
                          control={form.control}
                          name="targetRunway"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>Target Runway (months)</FormLabel>
                              <FormControl>
                                <Input
                                  type="number"
                                  className="font-mono"
                                  placeholder="18"
                                  {...field}
                                  data-testid="input-target-runway"
                                />
                              </FormControl>
                              <FormDescription>
                                How many months of runway you want to maintain
                              </FormDescription>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name="growthScenario"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>Growth Scenario</FormLabel>
                              <Select onValueChange={field.onChange} defaultValue={field.value}>
                                <FormControl>
                                  <SelectTrigger data-testid="select-scenario">
                                    <SelectValue placeholder="Select scenario" />
                                  </SelectTrigger>
                                </FormControl>
                                <SelectContent>
                                  <SelectItem value="optimistic">
                                    <div className="flex flex-col">
                                      <span>Optimistic (Aggressive Growth)</span>
                                    </div>
                                  </SelectItem>
                                  <SelectItem value="conservative">
                                    <div className="flex flex-col">
                                      <span>Conservative (Moderate Growth)</span>
                                    </div>
                                  </SelectItem>
                                  <SelectItem value="worst-case">
                                    <div className="flex flex-col">
                                      <span>Worst-case (Defensive)</span>
                                    </div>
                                  </SelectItem>
                                </SelectContent>
                              </Select>
                              <div className="mt-2 p-3 rounded-md bg-muted/50 text-xs text-muted-foreground">
                                {field.value === "optimistic" && (
                                  <p><strong className="text-foreground">Aggressive Growth:</strong> Assumes high revenue growth (15-25% MoM), accelerated hiring, and increased marketing spend. Best for companies with strong product-market fit and funding runway.</p>
                                )}
                                {field.value === "conservative" && (
                                  <p><strong className="text-foreground">Moderate Growth:</strong> Assumes steady revenue growth (5-10% MoM), controlled hiring, and balanced expense management. Recommended for most early-stage companies.</p>
                                )}
                                {field.value === "worst-case" && (
                                  <p><strong className="text-foreground">Defensive:</strong> Assumes flat or declining revenue, expense cuts, and focus on extending runway. Use this for stress-testing or during market downturns.</p>
                                )}
                              </div>
                              <FormDescription>
                                Select the scenario that best matches your growth strategy
                              </FormDescription>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name="fundingTarget"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>Funding Target ($)</FormLabel>
                              <FormControl>
                                <div className="relative">
                                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                  <Input
                                    type="number"
                                    className="pl-9 font-mono"
                                    placeholder="2000000"
                                    {...field}
                                    data-testid="input-funding-target"
                                  />
                                </div>
                              </FormControl>
                              <FormDescription>
                                Amount you plan to raise (if applicable)
                              </FormDescription>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name="fundingTimeline"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>Funding Timeline (months)</FormLabel>
                              <FormControl>
                                <Input
                                  type="number"
                                  className="font-mono"
                                  placeholder="12"
                                  {...field}
                                  data-testid="input-funding-timeline"
                                />
                              </FormControl>
                              <FormDescription>
                                When you plan to close the round
                              </FormDescription>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                      </div>

                      {calculatedRunway && watchedValues.targetRunway && calculatedRunway < watchedValues.targetRunway && (
                        <div className="flex items-start gap-2 p-3 rounded-md bg-amber-500/10 text-amber-600 dark:text-amber-400">
                          <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                          <p className="text-sm">
                            Your current runway ({calculatedRunway.toFixed(1)} months) is below your target ({watchedValues.targetRunway} months). 
                            Consider reducing expenses or securing funding.
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                <div className="mt-6 flex justify-end gap-2">
                  {!form.formState.isValid && form.formState.isDirty && (
                    <p className="text-xs text-amber-500 self-center">
                      <AlertCircle className="h-3 w-3 inline mr-1" />
                      Please fix validation errors before saving
                    </p>
                  )}
                  <Button 
                    type="submit" 
                    disabled={isSaving || (!form.formState.isValid && form.formState.isDirty)} 
                    data-testid="button-save-all"
                  >
                    {isSaving ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Check className="h-4 w-4 mr-2" />
                        Save All Data
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </Form>
          </Tabs>
        </div>

        <div className="lg:col-span-1">
          <Card className="h-[calc(100vh-12rem)] flex flex-col overflow-visible">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                AI Assistant
              </CardTitle>
              <CardDescription>
                Ask questions about your financial data
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col min-h-0">
              <ScrollArea className="flex-1 pr-4" ref={chatScrollRef}>
                <div className="space-y-4">
                  {chatMessages.length === 0 && (
                    <div className="space-y-3">
                      <p className="text-sm text-muted-foreground">Try asking:</p>
                      {SAMPLE_PROMPTS.map((prompt, i) => (
                        <Button
                          key={i}
                          variant="outline"
                          size="sm"
                          className="w-full justify-start text-left h-auto py-2 px-3"
                          onClick={() => sendMessage(prompt)}
                          data-testid={`button-prompt-${i}`}
                        >
                          <span className="text-xs">{prompt}</span>
                        </Button>
                      ))}
                    </div>
                  )}
                  {chatMessages.map((msg, i) => (
                    <div
                      key={i}
                      className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`max-w-[90%] rounded-lg px-3 py-2 text-sm ${
                          msg.role === "user"
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted"
                        }`}
                        data-testid={`chat-message-${i}`}
                      >
                        {msg.content || (
                          <div className="flex items-center gap-2">
                            <Loader2 className="h-3 w-3 animate-spin" />
                            <span>Thinking...</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>

              <div className="mt-4 flex gap-2">
                <Input
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      sendMessage(chatInput);
                    }
                  }}
                  placeholder="Ask about your finances..."
                  disabled={isStreaming}
                  data-testid="input-chat"
                />
                <Button
                  size="icon"
                  onClick={() => sendMessage(chatInput)}
                  disabled={!chatInput.trim() || isStreaming}
                  data-testid="button-send-chat"
                >
                  {isStreaming ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <Dialog open={showExtractionDetails} onOpenChange={setShowExtractionDetails}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5" />
              Extraction Details
            </DialogTitle>
          </DialogHeader>
          {lastExtraction && (
            <div className="space-y-4">
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                <span>Source: <Badge variant="outline">{lastExtraction.source.toUpperCase()}</Badge></span>
                <span>File: {lastExtraction.fileName}</span>
              </div>
              
              <div className="space-y-3">
                <h4 className="font-medium">Extracted Fields</h4>
                <div className="grid gap-2">
                  {Object.entries(lastExtraction.extracted).map(([key, field]) => (
                    <div key={key} className="flex items-center justify-between p-2 rounded-md bg-muted/50">
                      <div>
                        <span className="font-medium text-sm">{key}</span>
                        {field.evidence && (
                          <p className="text-xs text-muted-foreground mt-0.5">{field.evidence}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm">
                          {field.value !== null ? (
                            typeof field.value === 'number' ? 
                              formatCurrency(field.value) : 
                              field.value
                          ) : 'Not found'}
                        </span>
                        <Badge 
                          variant={field.confidence >= CONFIDENCE_THRESHOLD ? "default" : "outline"}
                          className={field.confidence < CONFIDENCE_THRESHOLD ? "text-amber-500 border-amber-500" : ""}
                        >
                          {Math.round(field.confidence * 100)}%
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {lastExtraction.missingFields.length > 0 && (
                <div className="p-3 rounded-md bg-amber-500/10">
                  <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400">
                    <AlertTriangle className="h-4 w-4" />
                    <span className="font-medium text-sm">Missing Fields</span>
                  </div>
                  <p className="text-sm mt-1 text-muted-foreground">
                    {lastExtraction.missingFields.join(', ')}
                  </p>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
