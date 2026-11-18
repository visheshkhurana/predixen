import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Flag, Plus, Target, Trash2 } from "lucide-react";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { getErrorMessage } from "@/lib/errors";
import { formatCurrencyFull } from "@/lib/utils";
import { useFounderStore } from "@/store/founderStore";
import { useToast } from "@/hooks/use-toast";

/**
 * Goals: founder-set targets saved per company (/api/companies/:id/goals).
 *
 * The page used to be an empty state with no create button because there was
 * no goals backend; saving a goal could never work. Goals are now stored
 * server-side (server/api/goals.py) and errors from saving are shown, not
 * swallowed.
 */

type Unit = "currency" | "months" | "percent" | "count" | "none";
type Status = "on_track" | "at_risk" | "off_track" | "done";

interface Goal {
  id: number;
  title: string;
  unit: Unit;
  target_value: number | null;
  current_value: number | null;
  deadline: string | null;
  status: Status;
  notes: string | null;
}

const STATUS_LABEL: Record<Status, string> = {
  on_track: "On track",
  at_risk: "At risk",
  off_track: "Off track",
  done: "Done",
};

const STATUS_CLASS: Record<Status, string> = {
  on_track: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30",
  at_risk: "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/30",
  off_track: "bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/30",
  done: "bg-muted text-muted-foreground",
};

const EMPTY_FORM = { title: "", unit: "currency" as Unit, target_value: "", current_value: "", deadline: "", notes: "" };

function formatValue(value: number | null, unit: Unit, currency: string): string {
  if (value == null) return "—";
  switch (unit) {
    case "currency":
      return formatCurrencyFull(value, currency);
    case "months":
      return `${value} mo`;
    case "percent":
      return `${value}%`;
    default:
      return value.toLocaleString();
  }
}

function toNumber(v: string): number | null {
  if (v.trim() === "") return null;
  const n = Number(v.replace(/,/g, ""));
  return Number.isFinite(n) ? n : null;
}

export default function GoalsPage() {
  const { currentCompany } = useFounderStore();
  const companyId = currentCompany?.id;
  const currency = currentCompany?.currency || "USD";
  const { toast } = useToast();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);

  const queryKey = ["/api/companies", companyId, "goals"];
  const goalsQuery = useQuery<{ goals: Goal[] }>({
    queryKey,
    enabled: !!companyId,
    queryFn: async () => {
      const res = await apiRequest("GET", `/api/companies/${companyId}/goals`);
      return res.json();
    },
  });
  const invalidate = () => queryClient.invalidateQueries({ queryKey });

  const createMut = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", `/api/companies/${companyId}/goals`, {
        title: form.title.trim(),
        unit: form.unit,
        target_value: form.unit === "none" ? null : toNumber(form.target_value),
        current_value: form.unit === "none" ? null : toNumber(form.current_value),
        deadline: form.deadline || null,
        notes: form.notes.trim() || null,
      });
      return res.json();
    },
    onSuccess: () => {
      invalidate();
      setForm(EMPTY_FORM);
      setShowForm(false);
      toast({ title: "Goal saved" });
    },
    onError: (err) =>
      toast({ title: "Couldn't save goal", description: getErrorMessage(err, "Please try again."), variant: "destructive" }),
  });

  const updateMut = useMutation({
    mutationFn: async ({ id, patch }: { id: number; patch: Partial<Goal> }) => {
      const res = await apiRequest("PATCH", `/api/companies/${companyId}/goals/${id}`, patch);
      return res.json();
    },
    onSuccess: () => invalidate(),
    onError: (err) =>
      toast({ title: "Couldn't update goal", description: getErrorMessage(err, "Please try again."), variant: "destructive" }),
  });

  const deleteMut = useMutation({
    mutationFn: async (id: number) => apiRequest("DELETE", `/api/companies/${companyId}/goals/${id}`),
    onSuccess: () => {
      invalidate();
      toast({ title: "Goal removed" });
    },
    onError: (err) =>
      toast({ title: "Couldn't remove goal", description: getErrorMessage(err, "Please try again."), variant: "destructive" }),
  });

  const goals = goalsQuery.data?.goals ?? [];
  const canSave = !!companyId && form.title.trim().length > 0 && !createMut.isPending;

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2" data-testid="text-goals-title">
            <Flag className="h-6 w-6 text-primary" />
            Goals
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Set targets, track progress, and stay accountable to your key milestones.
          </p>
        </div>
        {companyId && !showForm && (
          <Button onClick={() => setShowForm(true)} data-testid="button-new-goal">
            <Plus className="h-4 w-4 mr-1" /> New goal
          </Button>
        )}
      </div>

      {!companyId && (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            Select or create a company to set goals.
          </CardContent>
        </Card>
      )}

      {showForm && (
        <Card data-testid="card-goal-form">
          <CardHeader>
            <CardTitle className="text-lg">New goal</CardTitle>
            <CardDescription>Only the name is required. Money targets use {currency}.</CardDescription>
          </CardHeader>
          <CardContent>
            <form
              className="space-y-3"
              onSubmit={(e) => {
                e.preventDefault();
                if (canSave) createMut.mutate();
              }}
            >
              <Input
                aria-label="Goal"
                placeholder="e.g. Reach ₹50L monthly revenue"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                maxLength={200}
                autoFocus
                data-testid="input-goal-title"
              />
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                <div className="space-y-1">
                  <label htmlFor="goal-unit" className="text-xs font-medium text-muted-foreground">Measured in</label>
                  <Select value={form.unit} onValueChange={(v) => setForm({ ...form, unit: v as Unit })}>
                    <SelectTrigger id="goal-unit" data-testid="select-goal-unit">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="currency">Money ({currency})</SelectItem>
                      <SelectItem value="months">Months</SelectItem>
                      <SelectItem value="percent">Percent</SelectItem>
                      <SelectItem value="count">Count</SelectItem>
                      <SelectItem value="none">Milestone (no number)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {form.unit !== "none" && (
                  <>
                    <div className="space-y-1">
                      <label htmlFor="goal-target" className="text-xs font-medium text-muted-foreground">Target</label>
                      <Input
                        id="goal-target"
                        inputMode="decimal"
                        value={form.target_value}
                        onChange={(e) => setForm({ ...form, target_value: e.target.value })}
                        data-testid="input-goal-target"
                      />
                    </div>
                    <div className="space-y-1">
                      <label htmlFor="goal-current" className="text-xs font-medium text-muted-foreground">Current</label>
                      <Input
                        id="goal-current"
                        inputMode="decimal"
                        value={form.current_value}
                        onChange={(e) => setForm({ ...form, current_value: e.target.value })}
                        data-testid="input-goal-current"
                      />
                    </div>
                  </>
                )}
                <div className="space-y-1">
                  <label htmlFor="goal-deadline" className="text-xs font-medium text-muted-foreground">Deadline</label>
                  <Input
                    id="goal-deadline"
                    type="date"
                    value={form.deadline}
                    onChange={(e) => setForm({ ...form, deadline: e.target.value })}
                    data-testid="input-goal-deadline"
                  />
                </div>
              </div>
              <Textarea
                aria-label="Notes"
                placeholder="Notes (optional)"
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                maxLength={2000}
                rows={2}
              />
              <div className="flex gap-2">
                <Button type="submit" disabled={!canSave} data-testid="button-save-goal">
                  {createMut.isPending ? "Saving…" : "Save goal"}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setShowForm(false);
                    setForm(EMPTY_FORM);
                  }}
                >
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {companyId && goalsQuery.isLoading ? (
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      ) : companyId && goalsQuery.isError ? (
        <Card>
          <CardContent className="py-10 text-center space-y-3">
            <p className="text-sm text-muted-foreground">
              {getErrorMessage(goalsQuery.error, "Couldn't load your goals.")}
            </p>
            <Button variant="outline" size="sm" onClick={() => goalsQuery.refetch()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : companyId && goals.length === 0 && !showForm ? (
        <Card data-testid="card-goals-empty">
          <CardContent className="py-12 text-center space-y-3">
            <Target className="h-10 w-10 mx-auto text-muted-foreground" />
            <h2 className="text-base font-semibold" data-testid="text-goals-empty">No goals yet</h2>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              Write down the few targets that matter this quarter (monthly revenue, runway, a hire, a raise) and
              update progress as you go.
            </p>
            <Button size="sm" onClick={() => setShowForm(true)} data-testid="button-goals-empty-create">
              <Plus className="h-4 w-4 mr-1" /> Set your first goal
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {goals.map((g) => {
            const pct =
              g.unit !== "none" && g.target_value && g.current_value != null
                ? Math.max(0, Math.min(100, (g.current_value / g.target_value) * 100))
                : null;
            return (
              <Card key={g.id} data-testid={`card-goal-${g.id}`}>
                <CardContent className="p-4 space-y-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className={`font-semibold break-words ${g.status === "done" ? "line-through text-muted-foreground" : ""}`}>
                        {g.title}
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {g.unit !== "none" && (
                          <>
                            {formatValue(g.current_value, g.unit, currency)} of {formatValue(g.target_value, g.unit, currency)}
                          </>
                        )}
                        {g.unit !== "none" && g.deadline && " · "}
                        {g.deadline && <>by {new Date(g.deadline + "T00:00:00").toLocaleDateString()}</>}
                      </p>
                      {g.notes && <p className="text-xs text-muted-foreground mt-1 whitespace-pre-wrap">{g.notes}</p>}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge variant="outline" className={STATUS_CLASS[g.status]}>
                        {STATUS_LABEL[g.status]}
                      </Badge>
                      <Select
                        value={g.status}
                        onValueChange={(v) => updateMut.mutate({ id: g.id, patch: { status: v as Status } })}
                      >
                        <SelectTrigger className="h-8 w-[120px]" aria-label="Change status" data-testid={`select-goal-status-${g.id}`}>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {(Object.keys(STATUS_LABEL) as Status[]).map((s) => (
                            <SelectItem key={s} value={s}>
                              {STATUS_LABEL[s]}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Delete goal"
                        onClick={() => deleteMut.mutate(g.id)}
                        data-testid={`button-delete-goal-${g.id}`}
                      >
                        <Trash2 className="h-4 w-4 text-muted-foreground" />
                      </Button>
                    </div>
                  </div>
                  {pct != null && (
                    <div className="h-2 rounded-full bg-muted overflow-hidden">
                      <div className="h-full bg-primary rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                  )}
                  {g.unit !== "none" && g.status !== "done" && (
                    <form
                      className="flex items-center gap-2"
                      onSubmit={(e) => {
                        e.preventDefault();
                        const input = (e.currentTarget.elements.namedItem("current") as HTMLInputElement | null);
                        const value = toNumber(input?.value ?? "");
                        if (value == null) return;
                        updateMut.mutate({ id: g.id, patch: { current_value: value } });
                        if (input) input.value = "";
                      }}
                    >
                      <Input name="current" aria-label="Current value" inputMode="decimal" placeholder="Update current value" className="h-8 max-w-[200px]" />
                      <Button type="submit" size="sm" variant="outline" className="h-8">
                        Update
                      </Button>
                    </form>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
