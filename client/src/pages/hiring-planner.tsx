import { useState, useMemo } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useFounderStore } from "@/store/founderStore";
import { useToast } from "@/hooks/use-toast";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Users,
  Plus,
  Trash2,
  Play,
  Zap,
  DollarSign,
  TrendingDown,
  Calendar,
  Loader2,
  ArrowRight,
  Ban,
} from "lucide-react";

interface RoleDefinition {
  id: string;
  title: string;
  department: string;
  salaryMin: number;
  salaryMax: number;
}

const ROLE_LIBRARY: RoleDefinition[] = [
  { id: "senior-engineer", title: "Senior Engineer", department: "Engineering", salaryMin: 150000, salaryMax: 200000 },
  { id: "staff-engineer", title: "Staff Engineer", department: "Engineering", salaryMin: 180000, salaryMax: 250000 },
  { id: "engineering-manager", title: "Engineering Manager", department: "Engineering", salaryMin: 170000, salaryMax: 230000 },
  { id: "cto", title: "CTO", department: "Engineering", salaryMin: 200000, salaryMax: 300000 },
  { id: "sdr", title: "SDR", department: "Sales", salaryMin: 50000, salaryMax: 70000 },
  { id: "ae", title: "Account Executive", department: "Sales", salaryMin: 80000, salaryMax: 120000 },
  { id: "sales-manager", title: "Sales Manager", department: "Sales", salaryMin: 120000, salaryMax: 160000 },
  { id: "vp-sales", title: "VP Sales", department: "Sales", salaryMin: 180000, salaryMax: 250000 },
  { id: "marketing-manager", title: "Marketing Manager", department: "Marketing", salaryMin: 90000, salaryMax: 130000 },
  { id: "content-marketer", title: "Content Marketer", department: "Marketing", salaryMin: 60000, salaryMax: 90000 },
  { id: "growth-marketer", title: "Growth Marketer", department: "Marketing", salaryMin: 80000, salaryMax: 120000 },
  { id: "pm", title: "Product Manager", department: "Product", salaryMin: 120000, salaryMax: 170000 },
  { id: "product-designer", title: "Product Designer", department: "Product", salaryMin: 100000, salaryMax: 150000 },
  { id: "office-manager", title: "Office Manager", department: "Operations", salaryMin: 50000, salaryMax: 70000 },
  { id: "hr-manager", title: "HR Manager", department: "Operations", salaryMin: 80000, salaryMax: 120000 },
  { id: "finance-manager", title: "Finance Manager", department: "Operations", salaryMin: 100000, salaryMax: 150000 },
  { id: "csm", title: "Customer Success Manager", department: "Customer Success", salaryMin: 60000, salaryMax: 90000 },
  { id: "support-rep", title: "Support Rep", department: "Customer Success", salaryMin: 40000, salaryMax: 60000 },
  { id: "vp-cs", title: "VP Customer Success", department: "Customer Success", salaryMin: 150000, salaryMax: 200000 },
  { id: "head-of-ops", title: "Head of Ops", department: "Customer Success", salaryMin: 130000, salaryMax: 180000 },
];

const LOCATIONS = [
  { id: "sf", label: "San Francisco", multiplier: 1.0 },
  { id: "ny", label: "New York", multiplier: 0.95 },
  { id: "remote-us", label: "Remote US", multiplier: 0.85 },
  { id: "international", label: "International", multiplier: 0.7 },
];

const MONTHS = Array.from({ length: 12 }, (_, i) => ({
  value: String(i + 1),
  label: `Month ${i + 1}`,
}));

interface PlannedHire {
  id: string;
  roleId: string;
  roleTitle: string;
  department: string;
  count: number;
  startMonth: number;
  location: string;
  monthlySalary: number;
}

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

export default function HiringPlannerPage() {
  const { currentCompany } = useFounderStore();
  const { toast } = useToast();
  const companyId = currentCompany?.id;

  const [hires, setHires] = useState<PlannedHire[]>([]);
  const [selectedRole, setSelectedRole] = useState("");
  const [hireCount, setHireCount] = useState("1");
  const [startMonth, setStartMonth] = useState("1");
  const [location, setLocation] = useState("sf");
  const [savedPlanId, setSavedPlanId] = useState<string | null>(null);
  const [simResults, setSimResults] = useState<any>(null);

  const { data: truthScan, isLoading: truthScanLoading } = useQuery<any>({
    queryKey: ["/api/companies", companyId, "truth-scan", "latest"],
    enabled: !!companyId,
  });

  const { data: plansData } = useQuery<any>({
    queryKey: ["/api/companies", companyId, "hiring-plans"],
    enabled: !!companyId,
  });

  const savePlanMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        name: `Hiring Plan ${new Date().toLocaleDateString()}`,
        hires: hires.map((h) => ({
          role_id: h.roleId,
          role_title: h.roleTitle,
          department: h.department,
          count: h.count,
          start_month: h.startMonth,
          monthly_salary: h.monthlySalary,
          location: h.location,
        })),
      };
      const res = await apiRequest("POST", `/api/companies/${companyId}/hiring-plans`, payload);
      return res.json();
    },
    onSuccess: (data) => {
      setSavedPlanId(data.id);
      queryClient.invalidateQueries({ queryKey: ["/api/companies", companyId, "hiring-plans"] });
      toast({ title: "Plan saved", description: "Your hiring plan has been saved." });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to save hiring plan.", variant: "destructive" });
    },
  });

  const simulateMutation = useMutation({
    mutationFn: async (planId: string) => {
      const res = await apiRequest("POST", `/api/companies/${companyId}/hiring-plans/${planId}/simulate`);
      return res.json();
    },
    onSuccess: (data) => {
      setSimResults(data);
      toast({ title: "Simulation complete", description: "Monte Carlo simulation results are ready." });
    },
    onError: () => {
      toast({ title: "Error", description: "Simulation failed.", variant: "destructive" });
    },
  });

  const addHire = () => {
    if (!selectedRole) return;
    const role = ROLE_LIBRARY.find((r) => r.id === selectedRole);
    if (!role) return;
    const loc = LOCATIONS.find((l) => l.id === location);
    const multiplier = loc?.multiplier ?? 1.0;
    const avgSalary = (role.salaryMin + role.salaryMax) / 2;
    const monthlySalary = Math.round((avgSalary * multiplier) / 12);

    const newHire: PlannedHire = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      roleId: role.id,
      roleTitle: role.title,
      department: role.department,
      count: parseInt(hireCount) || 1,
      startMonth: parseInt(startMonth),
      location: location,
      monthlySalary,
    };
    setHires((prev) => [...prev, newHire]);
    setSelectedRole("");
    setHireCount("1");
  };

  const removeHire = (id: string) => {
    setHires((prev) => prev.filter((h) => h.id !== id));
  };

  const costSummary = useMemo(() => {
    const totalMonthly = hires.reduce((sum, h) => sum + h.monthlySalary * h.count, 0);
    const totalAnnual = totalMonthly * 12;
    const totalHeadcount = hires.reduce((sum, h) => sum + h.count, 0);
    const oneTimeCosts = totalHeadcount * 3000;
    return { totalMonthly, totalAnnual, totalHeadcount, oneTimeCosts };
  }, [hires]);

  const currentRunway = useMemo(() => {
    if (!truthScan?.metrics) return null;
    const m = truthScan.metrics;
    return m.runway_months ?? m.cash_runway_months ?? null;
  }, [truthScan]);

  const afterPlanRunway = useMemo(() => {
    if (currentRunway === null || !truthScan?.metrics) return null;
    const m = truthScan.metrics;
    const currentBurn = m.net_burn ?? m.monthly_burn ?? m.total_monthly_expenses ?? 0;
    const cash = m.cash_on_hand ?? m.cash_balance ?? 0;
    if (currentBurn <= 0 || cash <= 0) return null;
    const newBurn = currentBurn + costSummary.totalMonthly;
    if (newBurn <= 0) return null;
    return Math.round((cash / newBurn) * 10) / 10;
  }, [currentRunway, truthScan, costSummary.totalMonthly]);

  const handleQuickAction = (action: "engineers" | "sales" | "freeze") => {
    if (action === "freeze") {
      setHires([]);
      setSimResults(null);
      return;
    }

    const newHires: PlannedHire[] = [];
    if (action === "engineers") {
      const role = ROLE_LIBRARY.find((r) => r.id === "senior-engineer")!;
      const avgSalary = (role.salaryMin + role.salaryMax) / 2;
      newHires.push({
        id: `${Date.now()}-eng`,
        roleId: role.id,
        roleTitle: role.title,
        department: role.department,
        count: 3,
        startMonth: 4,
        location: "sf",
        monthlySalary: Math.round(avgSalary / 12),
      });
    } else if (action === "sales") {
      const sdr = ROLE_LIBRARY.find((r) => r.id === "sdr")!;
      const ae = ROLE_LIBRARY.find((r) => r.id === "ae")!;
      newHires.push({
        id: `${Date.now()}-sdr`,
        roleId: sdr.id,
        roleTitle: sdr.title,
        department: sdr.department,
        count: 2,
        startMonth: 2,
        location: "sf",
        monthlySalary: Math.round(((sdr.salaryMin + sdr.salaryMax) / 2) / 12),
      });
      newHires.push({
        id: `${Date.now()}-ae`,
        roleId: ae.id,
        roleTitle: ae.title,
        department: ae.department,
        count: 2,
        startMonth: 2,
        location: "sf",
        monthlySalary: Math.round(((ae.salaryMin + ae.salaryMax) / 2) / 12),
      });
    }
    setHires((prev) => [...prev, ...newHires]);
  };

  const handleRunSimulation = async () => {
    if (hires.length === 0) {
      toast({ title: "No hires", description: "Add hires before running a simulation.", variant: "destructive" });
      return;
    }
    if (!savedPlanId) {
      savePlanMutation.mutate(undefined, {
        onSuccess: (data) => {
          simulateMutation.mutate(data.id);
        },
      });
    } else {
      simulateMutation.mutate(savedPlanId);
    }
  };

  const departments = Array.from(new Set(ROLE_LIBRARY.map((r) => r.department)));

  return (
    <div className="p-4 md:p-6 space-y-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold" data-testid="text-page-title">Hiring Planner</h1>
        <p className="text-sm text-muted-foreground mt-1" data-testid="text-page-subtitle">
          Plan your team growth and see the impact on runway and burn rate.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => handleQuickAction("engineers")}
          data-testid="button-quick-engineers"
        >
          <Zap className="h-4 w-4 mr-1" />
          Hire 3 Engineers in Q2
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => handleQuickAction("sales")}
          data-testid="button-quick-sales"
        >
          <Zap className="h-4 w-4 mr-1" />
          Double Sales Team
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => handleQuickAction("freeze")}
          data-testid="button-quick-freeze"
        >
          <Ban className="h-4 w-4 mr-1" />
          Hiring Freeze
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-base">Add Role</CardTitle>
              <CardDescription>Select a role from the library and configure details.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Role</label>
                <Select value={selectedRole} onValueChange={setSelectedRole}>
                  <SelectTrigger data-testid="select-role">
                    <SelectValue placeholder="Select a role" />
                  </SelectTrigger>
                  <SelectContent>
                    {departments.map((dept) => (
                      <div key={dept}>
                        <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">{dept}</div>
                        {ROLE_LIBRARY.filter((r) => r.department === dept).map((role) => (
                          <SelectItem key={role.id} value={role.id} data-testid={`select-role-${role.id}`}>
                            {role.title} ({formatCurrency(role.salaryMin)}-{formatCurrency(role.salaryMax)}/yr)
                          </SelectItem>
                        ))}
                      </div>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Count</label>
                  <Input
                    type="number"
                    min="1"
                    max="50"
                    value={hireCount}
                    onChange={(e) => setHireCount(e.target.value)}
                    data-testid="input-hire-count"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Start Month</label>
                  <Select value={startMonth} onValueChange={setStartMonth}>
                    <SelectTrigger data-testid="select-start-month">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {MONTHS.map((m) => (
                        <SelectItem key={m.value} value={m.value}>
                          {m.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Location</label>
                  <Select value={location} onValueChange={setLocation}>
                    <SelectTrigger data-testid="select-location">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {LOCATIONS.map((loc) => (
                        <SelectItem key={loc.id} value={loc.id}>
                          {loc.label} ({(loc.multiplier * 100).toFixed(0)}%)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Button
                onClick={addHire}
                disabled={!selectedRole}
                className="w-full"
                data-testid="button-add-hire"
              >
                <Plus className="h-4 w-4 mr-1" />
                Add to Plan
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-base flex items-center gap-2">
                Planned Hires
                {hires.length > 0 && (
                  <Badge variant="secondary" className="no-default-hover-elevate">{hires.length}</Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {hires.length === 0 ? (
                <div className="text-center py-8 text-sm text-muted-foreground" data-testid="text-no-hires">
                  No hires planned yet. Add roles above or use a quick action.
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Role</TableHead>
                      <TableHead className="text-center">Count</TableHead>
                      <TableHead className="text-center">Month</TableHead>
                      <TableHead className="text-right">Monthly Cost</TableHead>
                      <TableHead className="w-10"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {hires.map((hire) => (
                      <TableRow key={hire.id} data-testid={`row-hire-${hire.id}`}>
                        <TableCell>
                          <div>
                            <span className="font-medium" data-testid={`text-hire-title-${hire.id}`}>{hire.roleTitle}</span>
                            <div className="text-xs text-muted-foreground">{hire.department}</div>
                          </div>
                        </TableCell>
                        <TableCell className="text-center" data-testid={`text-hire-count-${hire.id}`}>
                          {hire.count}
                        </TableCell>
                        <TableCell className="text-center" data-testid={`text-hire-month-${hire.id}`}>
                          M{hire.startMonth}
                        </TableCell>
                        <TableCell className="text-right font-mono" data-testid={`text-hire-cost-${hire.id}`}>
                          {formatCurrency(hire.monthlySalary * hire.count)}
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => removeHire(hire.id)}
                            data-testid={`button-remove-hire-${hire.id}`}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-base flex items-center gap-2">
                <DollarSign className="h-4 w-4" />
                Cost Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground">Total Headcount</span>
                  <p className="text-xl font-bold font-mono" data-testid="text-total-headcount">
                    {costSummary.totalHeadcount}
                  </p>
                </div>
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground">Monthly Cost Increase</span>
                  <p className="text-xl font-bold font-mono" data-testid="text-monthly-cost">
                    {formatCurrency(costSummary.totalMonthly)}
                  </p>
                </div>
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground">Annual Cost</span>
                  <p className="text-xl font-bold font-mono" data-testid="text-annual-cost">
                    {formatCurrency(costSummary.totalAnnual)}
                  </p>
                </div>
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground">One-Time Costs</span>
                  <p className="text-xl font-bold font-mono" data-testid="text-onetime-cost">
                    {formatCurrency(costSummary.oneTimeCosts)}
                  </p>
                  <p className="text-[10px] text-muted-foreground">Equipment $2K + Onboarding $1K per hire</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-base flex items-center gap-2">
                <TrendingDown className="h-4 w-4" />
                Runway Impact
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {truthScanLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-6 w-full" />
                  <Skeleton className="h-6 w-full" />
                </div>
              ) : currentRunway !== null ? (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between gap-2 text-sm">
                      <span className="text-muted-foreground">Current Runway</span>
                      <span className="font-bold font-mono" data-testid="text-current-runway">
                        {currentRunway} months
                      </span>
                    </div>
                    <div className="h-3 rounded-md bg-muted overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 rounded-md transition-all"
                        style={{ width: `${Math.min((currentRunway / 36) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                  {afterPlanRunway !== null && hires.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between gap-2 text-sm">
                        <span className="text-muted-foreground">After Plan Runway</span>
                        <span className="font-bold font-mono" data-testid="text-after-runway">
                          {afterPlanRunway} months
                        </span>
                      </div>
                      <div className="h-3 rounded-md bg-muted overflow-hidden">
                        <div
                          className={`h-full rounded-md transition-all ${afterPlanRunway < 12 ? "bg-red-500" : afterPlanRunway < 18 ? "bg-amber-500" : "bg-emerald-500"}`}
                          style={{ width: `${Math.min((afterPlanRunway / 36) * 100, 100)}%` }}
                        />
                      </div>
                    </div>
                  )}
                  {afterPlanRunway !== null && hires.length > 0 && (
                    <div className="flex items-center gap-2 text-sm">
                      <ArrowRight className="h-4 w-4" />
                      <span
                        className={`font-bold ${(afterPlanRunway - currentRunway) < 0 ? "text-red-500" : "text-emerald-500"}`}
                        data-testid="text-runway-delta"
                      >
                        {(afterPlanRunway - currentRunway) > 0 ? "+" : ""}
                        {(afterPlanRunway - currentRunway).toFixed(1)} months
                      </span>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">
                  Run a Health Check first to see runway impact.
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-base flex items-center gap-2">
                <Play className="h-4 w-4" />
                Monte Carlo Simulation
              </CardTitle>
              <CardDescription>Run a simulation to see P10/P50/P90 outcomes.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button
                onClick={handleRunSimulation}
                disabled={hires.length === 0 || savePlanMutation.isPending || simulateMutation.isPending}
                className="w-full"
                data-testid="button-run-simulation"
              >
                {(savePlanMutation.isPending || simulateMutation.isPending) ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1" />
                ) : (
                  <Play className="h-4 w-4 mr-1" />
                )}
                Run Simulation
              </Button>

              {simResults && (
                <div className="space-y-3 pt-2" data-testid="card-sim-results">
                  <div className="grid grid-cols-3 gap-3">
                    <div className="text-center space-y-1 p-3 rounded-md bg-muted/50">
                      <span className="text-xs text-muted-foreground">P10 (Bear)</span>
                      <p className="text-lg font-bold font-mono text-red-500" data-testid="text-sim-p10">
                        {simResults.p10_runway ?? simResults.runway_p10 ?? "N/A"}
                      </p>
                      <span className="text-[10px] text-muted-foreground">months</span>
                    </div>
                    <div className="text-center space-y-1 p-3 rounded-md bg-muted/50">
                      <span className="text-xs text-muted-foreground">P50 (Base)</span>
                      <p className="text-lg font-bold font-mono text-amber-500" data-testid="text-sim-p50">
                        {simResults.p50_runway ?? simResults.runway_p50 ?? "N/A"}
                      </p>
                      <span className="text-[10px] text-muted-foreground">months</span>
                    </div>
                    <div className="text-center space-y-1 p-3 rounded-md bg-muted/50">
                      <span className="text-xs text-muted-foreground">P90 (Bull)</span>
                      <p className="text-lg font-bold font-mono text-emerald-500" data-testid="text-sim-p90">
                        {simResults.p90_runway ?? simResults.runway_p90 ?? "N/A"}
                      </p>
                      <span className="text-[10px] text-muted-foreground">months</span>
                    </div>
                  </div>
                  {simResults.survival_probability != null && (
                    <div className="flex items-center justify-between gap-2 text-sm px-1">
                      <span className="text-muted-foreground">12-Month Survival</span>
                      <span className="font-bold font-mono" data-testid="text-sim-survival">
                        {typeof simResults.survival_probability === "number"
                          ? `${(simResults.survival_probability * 100).toFixed(0)}%`
                          : simResults.survival_probability}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
