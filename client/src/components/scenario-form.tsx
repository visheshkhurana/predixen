import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import { Slider } from "@/components/ui/slider";
import { formatCurrencyFull } from "@/lib/utils";
import {
  DollarSign,
  Users,
  TrendingUp,
  Scissors,
  Banknote,
  Play,
} from "lucide-react";

const scenarioFormSchema = z.object({
  name: z.string().min(1, "Scenario name is required"),
  description: z.string().optional(),
  cashOnHand: z.coerce.number().min(0, "Cash must be positive"),
  monthlyRevenue: z.coerce.number().min(0, "Revenue must be positive"),
  monthlyExpenses: z.coerce.number().min(0, "Expenses must be positive"),
  growthRate: z.coerce.number().min(-30, "Growth cannot decrease more than 30%").max(50, "Growth capped at 50%"),
  avgCostPerHire: z.coerce.number().min(0).max(1000000, "Cost per hire capped at $1M").default(10000),
  priceChangePercent: z.coerce.number().min(-50, "Price decrease capped at 50%").max(100, "Price increase capped at 100%").default(0),
  newHires: z.coerce.number().min(0, "Hires must be 0 or more").max(500, "Hiring capped at 500 per role").default(0),
  costCutPercent: z.coerce.number().min(0).max(80, "Cost cuts capped at 80%").default(0),
  costCutAmount: z.coerce.number().min(0).default(0),
  newGrowthRate: z.coerce.number().min(-30).max(50).optional(),
  fundingAmount: z.coerce.number().min(0).max(100000000, "Fundraise capped at $100M").default(0),
  fundingMonth: z.coerce.number().min(1).max(24, "Fundraise month must be within 24-month horizon").default(6),
  projectionMonths: z.coerce.number().min(1).max(36).default(18),
});

type ScenarioFormValues = z.infer<typeof scenarioFormSchema>;

interface ScenarioFormProps {
  onSubmit: (values: ScenarioFormValues) => void;
  isLoading?: boolean;
  defaultValues?: Partial<ScenarioFormValues>;
  currency?: string;
}

export function ScenarioForm({ onSubmit, isLoading, defaultValues, currency = 'USD' }: ScenarioFormProps) {
  const form = useForm<ScenarioFormValues>({
    resolver: zodResolver(scenarioFormSchema),
    defaultValues: {
      name: "Base Scenario",
      description: "",
      cashOnHand: 500000,
      monthlyRevenue: 50000,
      monthlyExpenses: 80000,
      growthRate: 0,
      avgCostPerHire: 10000,
      priceChangePercent: 0,
      newHires: 0,
      costCutPercent: 0,
      costCutAmount: 0,
      fundingAmount: 0,
      fundingMonth: 6,
      projectionMonths: 18,
      ...defaultValues,
    },
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="text-lg">Scenario Details</CardTitle>
            <CardDescription>Name and describe your scenario</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Scenario Name</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="e.g., Aggressive Growth"
                      {...field}
                      data-testid="input-scenario-name"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description (Optional)</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Brief description of this scenario"
                      {...field}
                      data-testid="input-scenario-description"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="text-lg">Current Financial State</CardTitle>
            <CardDescription>Enter your current financial metrics</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                        data-testid="input-cash-on-hand"
                      />
                    </div>
                  </FormControl>
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
                        data-testid="input-monthly-revenue"
                      />
                    </div>
                  </FormControl>
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
                        data-testid="input-monthly-expenses"
                      />
                    </div>
                  </FormControl>
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
                        data-testid="input-growth-rate"
                      />
                    </div>
                  </FormControl>
                  <FormDescription>Expected monthly revenue growth</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        <Accordion type="multiple" className="w-full space-y-2" defaultValue={["pricing", "hiring"]}>
          <AccordionItem value="pricing" className="border rounded-lg px-4 bg-card">
            <AccordionTrigger className="py-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-md bg-primary/10">
                  <DollarSign className="h-4 w-4 text-primary" />
                </div>
                <div className="text-left">
                  <div className="font-medium">Pricing Changes</div>
                  <div className="text-xs text-muted-foreground">Adjust revenue per customer</div>
                </div>
              </div>
            </AccordionTrigger>
            <AccordionContent className="pb-4">
              <FormField
                control={form.control}
                name="priceChangePercent"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Price Change (%)</FormLabel>
                    <FormControl>
                      <div className="space-y-3">
                        <Slider
                          min={-50}
                          max={100}
                          step={5}
                          value={[field.value]}
                          onValueChange={(v) => field.onChange(v[0])}
                          data-testid="slider-price-change"
                        />
                        <div className="flex justify-between text-xs text-muted-foreground">
                          <span>-50%</span>
                          <span className="font-mono font-medium text-foreground">
                            {field.value > 0 ? "+" : ""}{field.value}%
                          </span>
                          <span>+100%</span>
                        </div>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="hiring" className="border rounded-lg px-4 bg-card">
            <AccordionTrigger className="py-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-md bg-chart-2/10">
                  <Users className="h-4 w-4 text-chart-2" />
                </div>
                <div className="text-left">
                  <div className="font-medium">Hiring Plan</div>
                  <div className="text-xs text-muted-foreground">Add or reduce headcount</div>
                </div>
              </div>
            </AccordionTrigger>
            <AccordionContent className="pb-4 space-y-4">
              <FormField
                control={form.control}
                name="newHires"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Net Headcount Change</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        placeholder="0"
                        {...field}
                        data-testid="input-new-hires"
                      />
                    </FormControl>
                    <FormDescription>Positive = hires, Negative = layoffs</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="avgCostPerHire"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Avg Monthly Cost per Employee ($)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        className="font-mono"
                        placeholder="10000"
                        {...field}
                        data-testid="input-avg-cost-per-hire"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="costs" className="border rounded-lg px-4 bg-card">
            <AccordionTrigger className="py-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-md bg-chart-4/10">
                  <Scissors className="h-4 w-4 text-chart-4" />
                </div>
                <div className="text-left">
                  <div className="font-medium">Cost Reduction</div>
                  <div className="text-xs text-muted-foreground">Cut expenses to extend runway</div>
                </div>
              </div>
            </AccordionTrigger>
            <AccordionContent className="pb-4 space-y-4">
              <FormField
                control={form.control}
                name="costCutPercent"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Cost Cut (%)</FormLabel>
                    <FormControl>
                      <div className="space-y-3">
                        <Slider
                          min={0}
                          max={50}
                          step={5}
                          value={[field.value]}
                          onValueChange={(v) => field.onChange(v[0])}
                          data-testid="slider-cost-cut"
                        />
                        <div className="flex justify-between text-xs text-muted-foreground">
                          <span>0%</span>
                          <span className="font-mono font-medium text-foreground">{field.value}%</span>
                          <span>50%</span>
                        </div>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="costCutAmount"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Or Fixed Amount Cut ($)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        className="font-mono"
                        placeholder="0"
                        {...field}
                        data-testid="input-cost-cut-amount"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="growth" className="border rounded-lg px-4 bg-card">
            <AccordionTrigger className="py-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-md bg-chart-3/10">
                  <TrendingUp className="h-4 w-4 text-chart-3" />
                </div>
                <div className="text-left">
                  <div className="font-medium">Growth Adjustment</div>
                  <div className="text-xs text-muted-foreground">Change growth assumptions</div>
                </div>
              </div>
            </AccordionTrigger>
            <AccordionContent className="pb-4">
              <FormField
                control={form.control}
                name="newGrowthRate"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>New Growth Rate (%)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        placeholder="Leave empty to keep current"
                        {...field}
                        value={field.value ?? ""}
                        onChange={(e) => field.onChange(e.target.value === "" ? undefined : Number(e.target.value))}
                        data-testid="input-new-growth-rate"
                      />
                    </FormControl>
                    <FormDescription>Override the base growth rate</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="funding" className="border rounded-lg px-4 bg-card">
            <AccordionTrigger className="py-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-md bg-chart-1/10">
                  <Banknote className="h-4 w-4 text-chart-1" />
                </div>
                <div className="text-left">
                  <div className="font-medium">Fundraising</div>
                  <div className="text-xs text-muted-foreground">Plan a funding round</div>
                </div>
              </div>
            </AccordionTrigger>
            <AccordionContent className="pb-4 space-y-4">
              <FormField
                control={form.control}
                name="fundingAmount"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Funding Amount ($)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        className="font-mono"
                        placeholder="1000000"
                        {...field}
                        data-testid="input-funding-amount"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="fundingMonth"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Funding Month</FormLabel>
                    <FormControl>
                      <div className="space-y-3">
                        <Slider
                          min={1}
                          max={18}
                          step={1}
                          value={[field.value]}
                          onValueChange={(v) => field.onChange(v[0])}
                          data-testid="slider-funding-month"
                        />
                        <div className="flex justify-between text-xs text-muted-foreground">
                          <span>Month 1</span>
                          <span className="font-mono font-medium text-foreground">Month {field.value}</span>
                          <span>Month 18</span>
                        </div>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        <Card>
          <CardContent className="p-4">
            <FormField
              control={form.control}
              name="projectionMonths"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Projection Period</FormLabel>
                  <FormControl>
                    <div className="space-y-3">
                      <Slider
                        min={6}
                        max={36}
                        step={6}
                        value={[field.value]}
                        onValueChange={(v) => field.onChange(v[0])}
                        data-testid="slider-projection-months"
                      />
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>6 months</span>
                        <span className="font-mono font-medium text-foreground">{field.value} months</span>
                        <span>36 months</span>
                      </div>
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        <Button type="submit" className="w-full" disabled={isLoading} data-testid="button-run-simulation">
          <Play className="h-4 w-4 mr-2" />
          {isLoading ? "Running Simulation..." : "Run Simulation"}
        </Button>
      </form>
    </Form>
  );
}
