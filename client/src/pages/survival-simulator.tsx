import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useRoute, useLocation } from "wouter";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Separator } from "@/components/ui/separator";
import {
  Rocket, TrendingUp, DollarSign, Users, AlertTriangle,
  Share2, ArrowRight, BarChart3, Shield, Target, ChevronDown,
  Zap, CheckCircle, UserPlus, Clock, Copy, Twitter, Linkedin,
  Gauge, ArrowLeft
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from "recharts";
import { Helmet } from "react-helmet";
import { useToast } from "@/hooks/use-toast";

const STORAGE_KEY = "fc_survival_sim_count";

function getSimCount(): number {
  try {
    return parseInt(localStorage.getItem(STORAGE_KEY) || "0", 10);
  } catch {
    return 0;
  }
}

function incrementSimCount(): number {
  const count = getSimCount() + 1;
  try {
    localStorage.setItem(STORAGE_KEY, String(count));
  } catch {}
  return count;
}

const formatCurrency = (val: number) => {
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`;
  if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`;
  return `$${val.toFixed(0)}`;
};

const gradeColors: Record<string, string> = {
  emerald: "from-emerald-500 to-emerald-600",
  yellow: "from-yellow-500 to-yellow-600",
  orange: "from-orange-500 to-orange-600",
  red: "from-red-500 to-red-600",
};

const gradeBorders: Record<string, string> = {
  emerald: "border-emerald-500/30",
  yellow: "border-yellow-500/30",
  orange: "border-orange-500/30",
  red: "border-red-500/30",
};

const gradeTextColors: Record<string, string> = {
  emerald: "text-emerald-400",
  yellow: "text-yellow-400",
  orange: "text-orange-400",
  red: "text-red-400",
};

interface SimInputs {
  cash_on_hand: number;
  monthly_revenue: number;
  monthly_expenses: number;
  growth_rate: number;
  monthly_churn: number;
  planned_hires: number;
  avg_hire_cost: number;
  fundraising_month: number | null;
  fundraising_amount: number;
}

interface SimResults {
  simulation_id: string;
  inputs: SimInputs;
  runway: { p10: number; p50: number; p90: number; simple: number };
  survival: { "6m": number; "12m": number; "18m": number; "24m": number; curve: { month: number; survival_rate: number }[] };
  grade: { letter: string; label: string; color: string };
  histogram: { range_start: number; range_end: number; count: number }[];
  burn_trajectory: { month: number; p10: number; p50: number; p90: number }[];
  cash_trajectory: { month: number; p10: number; p50: number; p90: number }[];
  revenue_trajectory: { month: number; p10: number; p50: number; p90: number }[];
  recommendations: { priority: string; title: string; description: string; icon: string }[];
  n_simulations: number;
  created_at: string;
}

const defaultInputs: SimInputs = {
  cash_on_hand: 500000,
  monthly_revenue: 25000,
  monthly_expenses: 45000,
  growth_rate: 8,
  monthly_churn: 3,
  planned_hires: 2,
  avg_hire_cost: 8000,
  fundraising_month: null,
  fundraising_amount: 0,
};

function SimulatorInputForm({ onSubmit, isLoading, gated }: {
  onSubmit: (inputs: SimInputs) => void;
  isLoading: boolean;
  gated: boolean;
}) {
  const [inputs, setInputs] = useState<SimInputs>(defaultInputs);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const set = (key: keyof SimInputs, val: number | null) =>
    setInputs(prev => ({ ...prev, [key]: val }));

  return (
    <Card className="border-zinc-800 bg-zinc-900/80 backdrop-blur" data-testid="simulator-input-form">
      <CardHeader className="pb-4">
        <CardTitle className="text-xl flex items-center gap-2">
          <Target className="h-5 w-5 text-primary" />
          Your Startup's Financials
        </CardTitle>
        <p className="text-sm text-muted-foreground">Enter your current numbers to simulate 1,000 possible futures</p>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor="cash" className="text-sm font-medium">Cash on Hand</Label>
            <div className="relative">
              <DollarSign className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                id="cash"
                data-testid="input-cash-on-hand"
                type="number"
                value={inputs.cash_on_hand}
                onChange={e => set("cash_on_hand", Number(e.target.value))}
                className="pl-9 bg-zinc-800 border-zinc-700"
                placeholder="500000"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="revenue" className="text-sm font-medium">Monthly Revenue</Label>
            <div className="relative">
              <TrendingUp className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                id="revenue"
                data-testid="input-monthly-revenue"
                type="number"
                value={inputs.monthly_revenue}
                onChange={e => set("monthly_revenue", Number(e.target.value))}
                className="pl-9 bg-zinc-800 border-zinc-700"
                placeholder="25000"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="expenses" className="text-sm font-medium">Monthly Expenses</Label>
            <div className="relative">
              <BarChart3 className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                id="expenses"
                data-testid="input-monthly-expenses"
                type="number"
                value={inputs.monthly_expenses}
                onChange={e => set("monthly_expenses", Number(e.target.value))}
                className="pl-9 bg-zinc-800 border-zinc-700"
                placeholder="45000"
              />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <Label className="text-sm font-medium">Growth Rate</Label>
              <span className="text-sm text-primary font-mono">{inputs.growth_rate}% /mo</span>
            </div>
            <Slider
              data-testid="slider-growth-rate"
              value={[inputs.growth_rate]}
              onValueChange={([v]) => set("growth_rate", v)}
              min={-20}
              max={50}
              step={1}
              className="py-1"
            />
          </div>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <Label className="text-sm font-medium">Monthly Churn</Label>
              <span className="text-sm text-orange-400 font-mono">{inputs.monthly_churn}%</span>
            </div>
            <Slider
              data-testid="slider-churn"
              value={[inputs.monthly_churn]}
              onValueChange={([v]) => set("monthly_churn", v)}
              min={0}
              max={20}
              step={0.5}
              className="py-1"
            />
          </div>
        </div>

        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
          data-testid="toggle-advanced"
        >
          <ChevronDown className={`h-4 w-4 transition-transform ${showAdvanced ? "rotate-180" : ""}`} />
          {showAdvanced ? "Hide" : "Show"} Advanced Options
        </button>

        {showAdvanced && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 animate-in fade-in duration-200">
            <div className="space-y-2">
              <Label className="text-sm">Planned Hires (next 12 months)</Label>
              <Input
                data-testid="input-planned-hires"
                type="number"
                value={inputs.planned_hires}
                onChange={e => set("planned_hires", Number(e.target.value))}
                className="bg-zinc-800 border-zinc-700"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm">Avg Monthly Cost per Hire</Label>
              <Input
                data-testid="input-avg-hire-cost"
                type="number"
                value={inputs.avg_hire_cost}
                onChange={e => set("avg_hire_cost", Number(e.target.value))}
                className="bg-zinc-800 border-zinc-700"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm">Fundraising Month (1-24)</Label>
              <Input
                data-testid="input-fundraising-month"
                type="number"
                value={inputs.fundraising_month ?? ""}
                onChange={e => set("fundraising_month", e.target.value ? Number(e.target.value) : null)}
                className="bg-zinc-800 border-zinc-700"
                placeholder="Leave blank if not raising"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm">Fundraising Amount</Label>
              <Input
                data-testid="input-fundraising-amount"
                type="number"
                value={inputs.fundraising_amount}
                onChange={e => set("fundraising_amount", Number(e.target.value))}
                className="bg-zinc-800 border-zinc-700"
                placeholder="0"
              />
            </div>
          </div>
        )}

        <Button
          onClick={() => onSubmit(inputs)}
          disabled={isLoading || gated}
          className="w-full h-12 text-base font-semibold bg-gradient-to-r from-primary to-violet-600 hover:from-primary/90 hover:to-violet-600/90"
          data-testid="button-run-simulation"
        >
          {isLoading ? (
            <span className="flex items-center gap-2">
              <span className="animate-spin h-4 w-4 border-2 border-white/30 border-t-white rounded-full" />
              Running 1,000 Simulations...
            </span>
          ) : gated ? (
            "Create Free Account to Continue"
          ) : (
            <span className="flex items-center gap-2">
              <Rocket className="h-4 w-4" />
              Simulate My Startup's Survival
            </span>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}

function SurvivalGauge({ probability, label }: { probability: number; label: string }) {
  const angle = (probability / 100) * 180 - 90;
  const color = probability >= 80 ? "#10b981" : probability >= 60 ? "#eab308" : probability >= 40 ? "#f97316" : "#ef4444";

  return (
    <div className="flex flex-col items-center" data-testid={`gauge-${label.toLowerCase().replace(/\s/g, '-')}`}>
      <div className="relative w-32 h-16 overflow-hidden">
        <svg viewBox="0 0 100 50" className="w-full h-full">
          <path d="M 5 50 A 45 45 0 0 1 95 50" fill="none" stroke="#27272a" strokeWidth="8" strokeLinecap="round" />
          <path
            d="M 5 50 A 45 45 0 0 1 95 50"
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={`${(probability / 100) * 141.37} 141.37`}
            className="transition-all duration-1000"
          />
          <line
            x1="50" y1="50"
            x2={50 + 35 * Math.cos((angle * Math.PI) / 180)}
            y2={50 - 35 * Math.sin((-angle * Math.PI) / 180)}
            stroke={color}
            strokeWidth="2"
            strokeLinecap="round"
            className="transition-all duration-1000"
          />
        </svg>
      </div>
      <span className="text-2xl font-bold mt-1" style={{ color }}>{probability}%</span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  );
}

function RunwayDistributionChart({ histogram }: { histogram: SimResults["histogram"] }) {
  return (
    <Card className="border-zinc-800 bg-zinc-900/80" data-testid="chart-runway-distribution">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Runway Distribution (1,000 simulations)</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={histogram} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
            <XAxis
              dataKey="range_start"
              tickFormatter={v => `${v}m`}
              tick={{ fill: "#a1a1aa", fontSize: 11 }}
              stroke="#3f3f46"
            />
            <YAxis tick={{ fill: "#a1a1aa", fontSize: 11 }} stroke="#3f3f46" />
            <Tooltip
              contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: "8px" }}
              labelFormatter={v => `${v}-${Number(v) + 3} months`}
              formatter={(value: number) => [`${value} simulations`, "Count"]}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {histogram.map((entry, idx) => (
                <Cell
                  key={idx}
                  fill={entry.range_start < 12 ? "#ef4444" : entry.range_start < 18 ? "#f97316" : entry.range_start < 24 ? "#eab308" : "#10b981"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="flex justify-center gap-4 mt-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" />{"<12m Critical"}</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500" />12-18m Risk</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-500" />18-24m Caution</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" />{">24m Healthy"}</span>
        </div>
      </CardContent>
    </Card>
  );
}

function CashTrajectoryChart({ data }: { data: SimResults["cash_trajectory"] }) {
  return (
    <Card className="border-zinc-800 bg-zinc-900/80" data-testid="chart-cash-trajectory">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Cash Trajectory (P10 / P50 / P90)</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
            <XAxis dataKey="month" tickFormatter={v => `M${v}`} tick={{ fill: "#a1a1aa", fontSize: 11 }} stroke="#3f3f46" />
            <YAxis tickFormatter={v => formatCurrency(v)} tick={{ fill: "#a1a1aa", fontSize: 11 }} stroke="#3f3f46" />
            <Tooltip
              contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: "8px" }}
              labelFormatter={v => `Month ${v}`}
              formatter={(value: number) => [formatCurrency(value)]}
            />
            <Area type="monotone" dataKey="p90" stroke="none" fill="#10b981" fillOpacity={0.1} name="Best Case (P90)" />
            <Area type="monotone" dataKey="p50" stroke="#10b981" fill="#10b981" fillOpacity={0.2} strokeWidth={2} name="Median (P50)" />
            <Area type="monotone" dataKey="p10" stroke="#ef4444" fill="#ef4444" fillOpacity={0.1} strokeWidth={1.5} strokeDasharray="4 4" name="Worst Case (P10)" />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function SimulationResultsCard({ results }: { results: SimResults }) {
  const { grade, runway, survival } = results;

  return (
    <Card className={`border-2 ${gradeBorders[grade.color]} bg-zinc-900/80 backdrop-blur`} data-testid="results-card">
      <CardContent className="pt-6">
        <div className="flex flex-col md:flex-row items-center gap-6 mb-6">
          <div className={`flex flex-col items-center justify-center w-24 h-24 rounded-2xl bg-gradient-to-br ${gradeColors[grade.color]} shadow-lg`}>
            <span className="text-4xl font-black text-white">{grade.letter}</span>
            <span className="text-xs font-medium text-white/80">{grade.label}</span>
          </div>
          <div className="flex-1 text-center md:text-left">
            <h3 className="text-2xl font-bold mb-1">
              Your startup has a <span className={gradeTextColors[grade.color]}>{survival["12m"]}%</span> chance of surviving 12 months
            </h3>
            <p className="text-muted-foreground">
              Median runway: <span className="text-white font-semibold">{runway.p50} months</span>
              {" "}(range: {runway.p10} – {runway.p90} months)
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <SurvivalGauge probability={survival["6m"]} label="6 Months" />
          <SurvivalGauge probability={survival["12m"]} label="12 Months" />
          <SurvivalGauge probability={survival["18m"]} label="18 Months" />
          <SurvivalGauge probability={survival["24m"]} label="24 Months" />
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
            <p className="text-xs text-muted-foreground mb-1">Pessimistic</p>
            <p className="text-lg font-bold text-red-400">{runway.p10}mo</p>
            <p className="text-xs text-muted-foreground">P10 Runway</p>
          </div>
          <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
            <p className="text-xs text-muted-foreground mb-1">Most Likely</p>
            <p className="text-lg font-bold text-white">{runway.p50}mo</p>
            <p className="text-xs text-muted-foreground">P50 Runway</p>
          </div>
          <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
            <p className="text-xs text-muted-foreground mb-1">Optimistic</p>
            <p className="text-lg font-bold text-emerald-400">{runway.p90}mo</p>
            <p className="text-xs text-muted-foreground">P90 Runway</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function RecommendationsPanel({ recommendations }: { recommendations: SimResults["recommendations"] }) {
  const iconMap: Record<string, React.ReactNode> = {
    "alert-triangle": <AlertTriangle className="h-5 w-5" />,
    "trending-up": <TrendingUp className="h-5 w-5" />,
    "users": <Users className="h-5 w-5" />,
    "user-plus": <UserPlus className="h-5 w-5" />,
    "dollar-sign": <DollarSign className="h-5 w-5" />,
    "rocket": <Rocket className="h-5 w-5" />,
    "check-circle": <CheckCircle className="h-5 w-5" />,
  };

  const priorityColors: Record<string, string> = {
    critical: "border-red-500/30 bg-red-500/5",
    high: "border-orange-500/30 bg-orange-500/5",
    medium: "border-yellow-500/30 bg-yellow-500/5",
    low: "border-emerald-500/30 bg-emerald-500/5",
    info: "border-blue-500/30 bg-blue-500/5",
  };

  const priorityIconColors: Record<string, string> = {
    critical: "text-red-400",
    high: "text-orange-400",
    medium: "text-yellow-400",
    low: "text-emerald-400",
    info: "text-blue-400",
  };

  return (
    <Card className="border-zinc-800 bg-zinc-900/80" data-testid="recommendations-panel">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Zap className="h-4 w-4 text-primary" />
          Strategic Recommendations
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {recommendations.map((rec, i) => (
          <div key={i} className={`rounded-lg border p-3 ${priorityColors[rec.priority]}`}>
            <div className="flex items-start gap-3">
              <div className={`mt-0.5 ${priorityIconColors[rec.priority]}`}>
                {iconMap[rec.icon] || <Shield className="h-5 w-5" />}
              </div>
              <div>
                <p className="font-medium text-sm">{rec.title}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{rec.description}</p>
              </div>
              <Badge variant="outline" className="ml-auto shrink-0 text-xs capitalize">
                {rec.priority}
              </Badge>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function ShareResultPanel({ results }: { results: SimResults }) {
  const { toast } = useToast();
  const shareUrl = `${window.location.origin}/survival/${results.simulation_id}`;
  const shareText = `My startup has a ${results.survival["12m"]}% chance of surviving 12 months (median runway: ${results.runway.p50}mo). Check yours:`;

  const copyLink = () => {
    navigator.clipboard.writeText(shareUrl);
    toast({ title: "Link copied!" });
  };

  const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(shareUrl)}`;
  const linkedinUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`;

  return (
    <Card className="border-zinc-800 bg-zinc-900/80" data-testid="share-panel">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Share2 className="h-4 w-4 text-primary" />
          Share Your Results
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <Input
            value={shareUrl}
            readOnly
            className="bg-zinc-800 border-zinc-700 text-sm"
            data-testid="input-share-url"
          />
          <Button variant="outline" size="sm" onClick={copyLink} data-testid="button-copy-link">
            <Copy className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => window.open(twitterUrl, "_blank")}
            data-testid="button-share-twitter"
          >
            <Twitter className="h-4 w-4 mr-2" /> Twitter
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => window.open(linkedinUrl, "_blank")}
            data-testid="button-share-linkedin"
          >
            <Linkedin className="h-4 w-4 mr-2" /> LinkedIn
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function GrowthGate() {
  const [, navigate] = useLocation();
  return (
    <Card className="border-primary/30 bg-gradient-to-br from-primary/5 to-violet-600/5" data-testid="growth-gate">
      <CardContent className="pt-6 text-center space-y-4">
        <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
          <Rocket className="h-8 w-8 text-primary" />
        </div>
        <h3 className="text-xl font-bold">Want Unlimited Simulations?</h3>
        <p className="text-muted-foreground max-w-md mx-auto">
          Create a free FounderConsole account to run unlimited simulations, save scenarios,
          get AI-powered recommendations, and access your full financial dashboard.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button
            className="bg-gradient-to-r from-primary to-violet-600"
            onClick={() => navigate("/login")}
            data-testid="button-create-account"
          >
            Create Free Account <ArrowRight className="h-4 w-4 ml-2" />
          </Button>
          <Button variant="outline" onClick={() => navigate("/login")} data-testid="button-login">
            Already have an account? Log in
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function ExportButton({ results }: { results: SimResults }) {
  const handleExport = () => {
    const doc = window.open("", "_blank");
    if (!doc) return;
    const { runway, survival, grade, inputs, recommendations } = results;
    doc.document.write(`<!DOCTYPE html>
<html><head><title>Startup Survival Report</title>
<style>
  body { font-family: 'Inter', -apple-system, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; color: #1a1a1a; }
  h1 { font-size: 28px; margin-bottom: 8px; }
  .subtitle { color: #666; margin-bottom: 32px; }
  .grade-box { display: inline-flex; align-items: center; gap: 12px; padding: 16px 24px; border-radius: 12px; background: #f5f5f5; margin-bottom: 24px; }
  .grade-letter { font-size: 48px; font-weight: 900; }
  .metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 32px; }
  .metric { background: #f9fafb; border-radius: 8px; padding: 16px; text-align: center; }
  .metric-value { font-size: 24px; font-weight: 700; }
  .metric-label { font-size: 12px; color: #666; margin-top: 4px; }
  .survival { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 32px; }
  .survival-item { text-align: center; padding: 12px; background: #f9fafb; border-radius: 8px; }
  .rec { padding: 12px 16px; margin-bottom: 8px; border-left: 3px solid #6366f1; background: #f9fafb; border-radius: 0 8px 8px 0; }
  .rec-title { font-weight: 600; font-size: 14px; }
  .rec-desc { font-size: 13px; color: #666; margin-top: 4px; }
  .footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #e5e5e5; color: #999; font-size: 12px; }
  @media print { body { margin: 20px; } }
</style></head><body>
<h1>Startup Survival Report</h1>
<p class="subtitle">Generated by FounderConsole.ai | ${new Date().toLocaleDateString()}</p>
<div class="grade-box">
  <span class="grade-letter">${grade.letter}</span>
  <div><strong>${grade.label}</strong><br/><span style="color:#666">${survival["12m"]}% survival at 12 months</span></div>
</div>
<h2>Runway Projections</h2>
<div class="metrics">
  <div class="metric"><div class="metric-value" style="color:#ef4444">${runway.p10}mo</div><div class="metric-label">Pessimistic (P10)</div></div>
  <div class="metric"><div class="metric-value">${runway.p50}mo</div><div class="metric-label">Most Likely (P50)</div></div>
  <div class="metric"><div class="metric-value" style="color:#10b981">${runway.p90}mo</div><div class="metric-label">Optimistic (P90)</div></div>
</div>
<h2>Survival Probability</h2>
<div class="survival">
  <div class="survival-item"><div class="metric-value">${survival["6m"]}%</div><div class="metric-label">6 Months</div></div>
  <div class="survival-item"><div class="metric-value">${survival["12m"]}%</div><div class="metric-label">12 Months</div></div>
  <div class="survival-item"><div class="metric-value">${survival["18m"]}%</div><div class="metric-label">18 Months</div></div>
  <div class="survival-item"><div class="metric-value">${survival["24m"]}%</div><div class="metric-label">24 Months</div></div>
</div>
<h2>Input Assumptions</h2>
<div class="metrics">
  <div class="metric"><div class="metric-value">${formatCurrency(inputs.cash_on_hand)}</div><div class="metric-label">Cash on Hand</div></div>
  <div class="metric"><div class="metric-value">${formatCurrency(inputs.monthly_revenue)}</div><div class="metric-label">Monthly Revenue</div></div>
  <div class="metric"><div class="metric-value">${formatCurrency(inputs.monthly_expenses)}</div><div class="metric-label">Monthly Expenses</div></div>
</div>
<h2>Recommendations</h2>
${recommendations.map(r => `<div class="rec"><div class="rec-title">${r.title}</div><div class="rec-desc">${r.description}</div></div>`).join("")}
<div class="footer">
  <p>Based on 1,000 Monte Carlo simulations | FounderConsole.ai</p>
  <p>This report is for informational purposes only and should not be considered financial advice.</p>
</div>
</body></html>`);
    doc.document.close();
    setTimeout(() => doc.print(), 500);
  };

  return (
    <Button variant="outline" onClick={handleExport} className="gap-2" data-testid="button-export-report">
      <BarChart3 className="h-4 w-4" />
      Export Investor Report
    </Button>
  );
}

export default function SurvivalSimulatorPage() {
  const [, navigate] = useLocation();
  const { toast } = useToast();
  const [results, setResults] = useState<SimResults | null>(null);
  const [gated, setGated] = useState(false);

  const [matchShared, paramsShared] = useRoute("/survival/:simId");
  const sharedId = matchShared ? paramsShared?.simId : null;

  const { data: sharedResults, isLoading: sharedLoading } = useQuery<SimResults>({
    queryKey: ["/api/survival-sim/results", sharedId],
    queryFn: async () => {
      const res = await fetch(`/api/survival-sim/results/${sharedId}`);
      if (!res.ok) throw new Error("Not found");
      return res.json();
    },
    enabled: !!sharedId,
  });

  useEffect(() => {
    if (sharedResults) setResults(sharedResults);
  }, [sharedResults]);

  const simulation = useMutation({
    mutationFn: async (inputs: SimInputs) => {
      const res = await fetch("/api/survival-sim/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(inputs),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Simulation failed");
      }
      return res.json() as Promise<SimResults>;
    },
    onSuccess: (data) => {
      setResults(data);
      const count = incrementSimCount();
      if (count >= 2) setGated(true);
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    onError: (err: Error) => {
      toast({ title: "Simulation failed", description: err.message, variant: "destructive" });
    },
  });

  useEffect(() => {
    if (getSimCount() >= 2) setGated(true);
  }, []);

  if (sharedId && sharedLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <>
      <Helmet>
        <title>Startup Survival Simulator – Calculate Your Startup's Probability of Survival | FounderConsole</title>
        <meta name="description" content="Free Monte Carlo simulation tool. Calculate your startup's survival probability, runway projections, and get AI-powered strategic recommendations. Run 1,000 simulations in seconds." />
        <meta name="keywords" content="startup runway calculator, startup survival simulator, burn rate calculator, startup financial model, monte carlo simulation startup, runway projection tool" />
        <meta property="og:title" content="Startup Survival Simulator – How Long Will Your Startup Survive?" />
        <meta property="og:description" content="Run 1,000 Monte Carlo simulations to calculate your startup's probability of survival. Free tool by FounderConsole." />
        <meta property="og:type" content="website" />
        <meta property="og:url" content={`${window.location.origin}/survival-simulator`} />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="Startup Survival Simulator" />
        <meta name="twitter:description" content="Calculate your startup's probability of survival with 1,000 Monte Carlo simulations." />
      </Helmet>

      <div className="min-h-screen bg-background">
        <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-md sticky top-0 z-50">
          <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button onClick={() => navigate("/")} className="flex items-center gap-2 hover:opacity-80 transition-opacity" data-testid="link-home">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-violet-600 flex items-center justify-center">
                  <Rocket className="h-4 w-4 text-white" />
                </div>
                <span className="font-bold text-lg hidden sm:inline">FounderConsole</span>
              </button>
              <Separator orientation="vertical" className="h-6 hidden sm:block" />
              <span className="text-sm text-muted-foreground hidden sm:inline">Survival Simulator</span>
            </div>
            <div className="flex items-center gap-2">
              {results && <ExportButton results={results} />}
              <Button variant="ghost" size="sm" onClick={() => navigate("/login")} data-testid="button-header-login">
                Log in
              </Button>
              <Button size="sm" onClick={() => navigate("/login")} className="bg-primary" data-testid="button-header-signup">
                Sign up free
              </Button>
            </div>
          </div>
        </header>

        <main className="max-w-5xl mx-auto px-4 py-8 space-y-8">
          {!results && (
            <div className="text-center space-y-3 mb-8">
              <Badge variant="outline" className="text-primary border-primary/30">
                <Zap className="h-3 w-3 mr-1" /> Free Tool — No Login Required
              </Badge>
              <h1 className="text-4xl md:text-5xl font-black tracking-tight" data-testid="text-hero-title">
                Startup Survival
                <span className="bg-gradient-to-r from-primary to-violet-500 text-transparent bg-clip-text"> Simulator</span>
              </h1>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Run 1,000 Monte Carlo simulations to calculate your startup's probability of survival.
                Get AI-powered recommendations in seconds.
              </p>
              <div className="flex items-center justify-center gap-6 text-sm text-muted-foreground pt-2">
                <span className="flex items-center gap-1"><Shield className="h-4 w-4 text-emerald-500" /> No data stored</span>
                <span className="flex items-center gap-1"><Clock className="h-4 w-4 text-blue-500" /> Results in 3 seconds</span>
                <span className="flex items-center gap-1"><BarChart3 className="h-4 w-4 text-primary" /> 1,000 simulations</span>
              </div>
            </div>
          )}

          {results && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <button
                  onClick={() => { setResults(null); if (sharedId) navigate("/survival-simulator"); }}
                  className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
                  data-testid="button-back"
                >
                  <ArrowLeft className="h-4 w-4" /> Run New Simulation
                </button>
                <Badge variant="outline" className="text-xs">
                  Simulation ID: {results.simulation_id}
                </Badge>
              </div>

              <SimulationResultsCard results={results} />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <RunwayDistributionChart histogram={results.histogram} />
                <CashTrajectoryChart data={results.cash_trajectory} />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <RecommendationsPanel recommendations={results.recommendations} />
                <ShareResultPanel results={results} />
              </div>

              {gated && <GrowthGate />}
            </div>
          )}

          {!results && (
            <>
              <SimulatorInputForm
                onSubmit={(inputs) => simulation.mutate(inputs)}
                isLoading={simulation.isPending}
                gated={gated}
              />
              {gated && <GrowthGate />}
            </>
          )}

          {!results && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
              <Card className="border-zinc-800 bg-zinc-900/50">
                <CardContent className="pt-6 text-center space-y-2">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mx-auto">
                    <Gauge className="h-5 w-5 text-primary" />
                  </div>
                  <h3 className="font-semibold">Monte Carlo Engine</h3>
                  <p className="text-xs text-muted-foreground">1,000 probabilistic simulations model uncertainty in growth, margins, and costs</p>
                </CardContent>
              </Card>
              <Card className="border-zinc-800 bg-zinc-900/50">
                <CardContent className="pt-6 text-center space-y-2">
                  <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center mx-auto">
                    <Shield className="h-5 w-5 text-emerald-500" />
                  </div>
                  <h3 className="font-semibold">Survival Probability</h3>
                  <p className="text-xs text-muted-foreground">See your odds of survival at 6, 12, 18, and 24 months with confidence intervals</p>
                </CardContent>
              </Card>
              <Card className="border-zinc-800 bg-zinc-900/50">
                <CardContent className="pt-6 text-center space-y-2">
                  <div className="w-10 h-10 rounded-lg bg-violet-500/10 flex items-center justify-center mx-auto">
                    <Zap className="h-5 w-5 text-violet-500" />
                  </div>
                  <h3 className="font-semibold">AI Recommendations</h3>
                  <p className="text-xs text-muted-foreground">Get strategic recommendations based on your specific financial trajectory</p>
                </CardContent>
              </Card>
            </div>
          )}
        </main>

        <footer className="border-t border-zinc-800 mt-16">
          <div className="max-w-5xl mx-auto px-4 py-8 text-center text-sm text-muted-foreground space-y-2">
            <p>Built by <a href="/" className="text-primary hover:underline">FounderConsole.ai</a> — The Flight Simulator for Founders</p>
            <p className="text-xs">This tool provides estimates based on probabilistic modeling and should not be considered financial advice.</p>
          </div>
        </footer>
      </div>
    </>
  );
}
