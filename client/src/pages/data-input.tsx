import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { apiRequest, queryClient } from "@/lib/queryClient";
import {
  Upload,
  FileSpreadsheet,
  FileText,
  Check,
  AlertCircle,
  DollarSign,
  TrendingUp,
} from "lucide-react";

const manualInputSchema = z.object({
  cashOnHand: z.coerce.number().min(0, "Cash must be positive"),
  monthlyRevenue: z.coerce.number().min(0, "Revenue must be positive"),
  monthlyExpenses: z.coerce.number().min(0, "Expenses must be positive"),
  growthRate: z.coerce.number().min(-100).max(1000),
});

type ManualInputValues = z.infer<typeof manualInputSchema>;

interface ParsedData {
  cashOnHand: number;
  monthlyRevenue: number;
  monthlyExpenses: number;
  growthRate: number;
  source: string;
}

export default function DataInput() {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("manual");
  const [parsedData, setParsedData] = useState<ParsedData | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const form = useForm<ManualInputValues>({
    resolver: zodResolver(manualInputSchema),
    defaultValues: {
      cashOnHand: 500000,
      monthlyRevenue: 50000,
      monthlyExpenses: 80000,
      growthRate: 10,
    },
  });

  const saveMutation = useMutation({
    mutationFn: async (values: ManualInputValues) => {
      const response = await apiRequest("POST", "/api/financial-data", values);
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/financial-data"] });
      toast({
        title: "Data saved",
        description: "Your financial data has been saved successfully",
      });
    },
    onError: (error) => {
      toast({
        title: "Failed to save",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        throw new Error("Upload failed");
      }
      return response.json();
    },
    onSuccess: (data) => {
      setParsedData(data);
      setUploadError(null);
      toast({
        title: "File parsed",
        description: "Review the extracted data below",
      });
    },
    onError: (error) => {
      setUploadError(error.message);
      toast({
        title: "Upload failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const handleManualSubmit = (values: ManualInputValues) => {
    saveMutation.mutate(values);
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>, type: "csv" | "pdf") => {
    const file = event.target.files?.[0];
    if (file) {
      uploadMutation.mutate(file);
    }
  };

  const handleConfirmParsedData = () => {
    if (parsedData) {
      form.setValue("cashOnHand", parsedData.cashOnHand);
      form.setValue("monthlyRevenue", parsedData.monthlyRevenue);
      form.setValue("monthlyExpenses", parsedData.monthlyExpenses);
      form.setValue("growthRate", parsedData.growthRate);
      setActiveTab("manual");
      toast({
        title: "Data imported",
        description: "Review and save the imported data",
      });
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
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Data Input</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Enter or upload your financial data
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="manual" data-testid="tab-manual">
            <DollarSign className="h-4 w-4 mr-2" />
            Manual Entry
          </TabsTrigger>
          <TabsTrigger value="csv" data-testid="tab-csv">
            <FileSpreadsheet className="h-4 w-4 mr-2" />
            CSV Upload
          </TabsTrigger>
          <TabsTrigger value="pdf" data-testid="tab-pdf">
            <FileText className="h-4 w-4 mr-2" />
            PDF Upload
          </TabsTrigger>
        </TabsList>

        <TabsContent value="manual" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Current Financial State</CardTitle>
              <CardDescription>
                Enter your current financial metrics to use as a baseline for simulations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(handleManualSubmit)} className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <FormField
                      control={form.control}
                      name="cashOnHand"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Cash on Hand ($)</FormLabel>
                          <FormControl>
                            <div className="relative">
                              <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                              <Input
                                type="number"
                                className="pl-9 font-mono"
                                placeholder="500000"
                                {...field}
                                data-testid="input-data-cash"
                              />
                            </div>
                          </FormControl>
                          <FormDescription>Total cash available</FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="monthlyRevenue"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Monthly Revenue ($)</FormLabel>
                          <FormControl>
                            <div className="relative">
                              <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                              <Input
                                type="number"
                                className="pl-9 font-mono"
                                placeholder="50000"
                                {...field}
                                data-testid="input-data-revenue"
                              />
                            </div>
                          </FormControl>
                          <FormDescription>Current MRR or monthly revenue</FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="monthlyExpenses"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Monthly Expenses ($)</FormLabel>
                          <FormControl>
                            <div className="relative">
                              <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                              <Input
                                type="number"
                                className="pl-9 font-mono"
                                placeholder="80000"
                                {...field}
                                data-testid="input-data-expenses"
                              />
                            </div>
                          </FormControl>
                          <FormDescription>Total monthly operating expenses</FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="growthRate"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Monthly Growth Rate (%)</FormLabel>
                          <FormControl>
                            <div className="relative">
                              <TrendingUp className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                              <Input
                                type="number"
                                className="pl-9 font-mono"
                                placeholder="10"
                                {...field}
                                data-testid="input-data-growth"
                              />
                            </div>
                          </FormControl>
                          <FormDescription>Expected revenue growth per month</FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                  <Button type="submit" disabled={saveMutation.isPending} data-testid="button-save-data">
                    <Check className="h-4 w-4 mr-2" />
                    {saveMutation.isPending ? "Saving..." : "Save Data"}
                  </Button>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="csv" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Upload CSV File</CardTitle>
              <CardDescription>
                Upload a CSV file with your historical financial data
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="border-2 border-dashed rounded-lg p-8 text-center">
                <div className="mx-auto w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4">
                  <FileSpreadsheet className="h-6 w-6 text-muted-foreground" />
                </div>
                <div className="space-y-2">
                  <p className="text-sm font-medium">Drop your CSV file here or click to browse</p>
                  <p className="text-xs text-muted-foreground">
                    Expected columns: date, revenue, expenses, cash_balance
                  </p>
                </div>
                <input
                  type="file"
                  accept=".csv"
                  onChange={(e) => handleFileUpload(e, "csv")}
                  className="hidden"
                  id="csv-upload"
                  data-testid="input-csv-upload"
                />
                <Button variant="outline" className="mt-4" asChild>
                  <label htmlFor="csv-upload" className="cursor-pointer">
                    <Upload className="h-4 w-4 mr-2" />
                    Select File
                  </label>
                </Button>
              </div>

              {uploadError && (
                <div className="mt-4 p-3 rounded-md bg-destructive/10 text-destructive text-sm flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  {uploadError}
                </div>
              )}

              {parsedData && (
                <div className="mt-6 space-y-4">
                  <h4 className="font-medium">Parsed Data</h4>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Field</TableHead>
                        <TableHead className="text-right">Value</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      <TableRow>
                        <TableCell>Cash on Hand</TableCell>
                        <TableCell className="text-right font-mono">
                          {formatCurrency(parsedData.cashOnHand)}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Monthly Revenue</TableCell>
                        <TableCell className="text-right font-mono">
                          {formatCurrency(parsedData.monthlyRevenue)}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Monthly Expenses</TableCell>
                        <TableCell className="text-right font-mono">
                          {formatCurrency(parsedData.monthlyExpenses)}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Growth Rate</TableCell>
                        <TableCell className="text-right font-mono">
                          {parsedData.growthRate}%
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                  <Button onClick={handleConfirmParsedData} data-testid="button-confirm-import">
                    <Check className="h-4 w-4 mr-2" />
                    Use This Data
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="pdf" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Upload PDF Report</CardTitle>
              <CardDescription>
                Upload a financial statement or investor update PDF
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="border-2 border-dashed rounded-lg p-8 text-center">
                <div className="mx-auto w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4">
                  <FileText className="h-6 w-6 text-muted-foreground" />
                </div>
                <div className="space-y-2">
                  <p className="text-sm font-medium">Drop your PDF file here or click to browse</p>
                  <p className="text-xs text-muted-foreground">
                    We'll extract key financial metrics from your document
                  </p>
                </div>
                <input
                  type="file"
                  accept=".pdf"
                  onChange={(e) => handleFileUpload(e, "pdf")}
                  className="hidden"
                  id="pdf-upload"
                  data-testid="input-pdf-upload"
                />
                <Button variant="outline" className="mt-4" asChild>
                  <label htmlFor="pdf-upload" className="cursor-pointer">
                    <Upload className="h-4 w-4 mr-2" />
                    Select File
                  </label>
                </Button>
              </div>

              {uploadError && (
                <div className="mt-4 p-3 rounded-md bg-destructive/10 text-destructive text-sm flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  {uploadError}
                </div>
              )}

              {parsedData && parsedData.source === "pdf" && (
                <div className="mt-6 space-y-4">
                  <h4 className="font-medium">Extracted Data</h4>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Field</TableHead>
                        <TableHead className="text-right">Value</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      <TableRow>
                        <TableCell>Cash on Hand</TableCell>
                        <TableCell className="text-right font-mono">
                          {formatCurrency(parsedData.cashOnHand)}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Monthly Revenue</TableCell>
                        <TableCell className="text-right font-mono">
                          {formatCurrency(parsedData.monthlyRevenue)}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Monthly Expenses</TableCell>
                        <TableCell className="text-right font-mono">
                          {formatCurrency(parsedData.monthlyExpenses)}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Growth Rate</TableCell>
                        <TableCell className="text-right font-mono">
                          {parsedData.growthRate}%
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                  <Button onClick={handleConfirmParsedData} data-testid="button-confirm-pdf-import">
                    <Check className="h-4 w-4 mr-2" />
                    Use This Data
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
