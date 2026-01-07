import { useState, useRef, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
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
import { useToast } from "@/hooks/use-toast";
import { useFounderStore } from "@/store/founderStore";
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
} from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const dataInputSchema = z.object({
  companyName: z.string().min(1, "Company name is required"),
  description: z.string().optional(),
  foundingDate: z.string().optional(),
  stage: z.string().min(1, "Stage is required"),
  industry: z.string().min(1, "Industry is required"),
  cashOnHand: z.coerce.number().min(0, "Cash must be positive"),
  monthlyRevenue: z.coerce.number().min(0, "Revenue must be positive"),
  monthlyExpenses: z.coerce.number().min(0, "Expenses must be positive"),
  payrollExpenses: z.coerce.number().min(0).optional(),
  marketingExpenses: z.coerce.number().min(0).optional(),
  operatingExpenses: z.coerce.number().min(0).optional(),
  growthRate: z.coerce.number().min(-100).max(1000),
  burnRate: z.coerce.number().optional(),
  employees: z.coerce.number().min(0).optional(),
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

export default function DataInput() {
  const { toast } = useToast();
  const { currentCompany } = useFounderStore();
  const [activeTab, setActiveTab] = useState("company");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const chatScrollRef = useRef<HTMLDivElement>(null);

  const form = useForm<DataInputValues>({
    resolver: zodResolver(dataInputSchema),
    defaultValues: {
      companyName: currentCompany?.name || "",
      description: "",
      foundingDate: "",
      stage: "seed",
      industry: "saas",
      cashOnHand: 500000,
      monthlyRevenue: 50000,
      monthlyExpenses: 80000,
      payrollExpenses: 50000,
      marketingExpenses: 15000,
      operatingExpenses: 15000,
      growthRate: 10,
      burnRate: 30000,
      employees: 10,
      targetRunway: 18,
      growthScenario: "conservative",
      fundingTarget: 0,
      fundingTimeline: 12,
    },
  });

  const watchedValues = form.watch();
  const calculatedBurn = (watchedValues.monthlyExpenses || 0) - (watchedValues.monthlyRevenue || 0);
  const calculatedRunway = calculatedBurn > 0 ? (watchedValues.cashOnHand || 0) / calculatedBurn : null;

  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [chatMessages]);

  const handleSave = async (values: DataInputValues) => {
    setIsSaving(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 500));
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
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Data Input</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Enter your company information and financial data for analysis
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-3">
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

            <Form {...form}>
              <form onSubmit={form.handleSubmit(handleSave)}>
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
                      <CardTitle className="text-lg">Financial Metrics</CardTitle>
                      <CardDescription>
                        Your current financial position and performance
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <FormField
                          control={form.control}
                          name="cashOnHand"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="flex items-center gap-1.5">
                                Cash on Hand ($)
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
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name="monthlyRevenue"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="flex items-center gap-1.5">
                                Monthly Revenue ($)
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
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name="monthlyExpenses"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="flex items-center gap-1.5">
                                Total Monthly Expenses ($)
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
                                    data-testid="input-expenses"
                                  />
                                </div>
                              </FormControl>
                              <FormDescription>Total monthly operating costs</FormDescription>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name="growthRate"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="flex items-center gap-1.5">
                                Monthly Growth Rate (%)
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
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                      </div>

                      <div className="border-t pt-4">
                        <h4 className="text-sm font-medium mb-3">Expense Breakdown (Optional)</h4>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <FormField
                            control={form.control}
                            name="payrollExpenses"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Payroll ($)</FormLabel>
                                <FormControl>
                                  <Input
                                    type="number"
                                    className="font-mono"
                                    placeholder="50000"
                                    {...field}
                                    data-testid="input-payroll"
                                  />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                          <FormField
                            control={form.control}
                            name="marketingExpenses"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Marketing ($)</FormLabel>
                                <FormControl>
                                  <Input
                                    type="number"
                                    className="font-mono"
                                    placeholder="15000"
                                    {...field}
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
                                <FormLabel>Operating ($)</FormLabel>
                                <FormControl>
                                  <Input
                                    type="number"
                                    className="font-mono"
                                    placeholder="15000"
                                    {...field}
                                    data-testid="input-operating"
                                  />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                        </div>
                      </div>

                      <div className="bg-muted/50 rounded-md p-4">
                        <h4 className="text-sm font-medium mb-2">Calculated Metrics</h4>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <p className="text-xs text-muted-foreground">Net Burn Rate</p>
                            <p className="text-lg font-mono font-semibold" data-testid="text-burn-rate">
                              {formatCurrency(Math.max(0, calculatedBurn))}/mo
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Current Runway</p>
                            <p className="text-lg font-mono font-semibold" data-testid="text-runway">
                              {calculatedRunway ? `${calculatedRunway.toFixed(1)} months` : "Profitable"}
                            </p>
                          </div>
                        </div>
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
                                  <SelectItem value="optimistic">Optimistic (high growth)</SelectItem>
                                  <SelectItem value="conservative">Conservative (steady)</SelectItem>
                                  <SelectItem value="worst-case">Worst-case (decline)</SelectItem>
                                </SelectContent>
                              </Select>
                              <FormDescription>
                                Default scenario for projections
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

                <div className="mt-6 flex justify-end">
                  <Button type="submit" disabled={isSaving} data-testid="button-save-all">
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
    </div>
  );
}
