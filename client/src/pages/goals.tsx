import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Flag, Target } from "lucide-react";
import { useLocation } from "wouter";

/**
 * Goals.
 *
 * There is no goals backend yet (no table, no API; the overview's goal cards
 * are fixed targets computed client-side). This page used to show six
 * hardcoded sample goals (MRR, CAC, a Series A raise, ...) with
 * invented deadlines and statuses, plus a "New Goal" button that did nothing.
 * Until goals can be saved, it shows an honest empty state and no create
 * button.
 */
export default function GoalsPage() {
  const [, setLocation] = useLocation();

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2" data-testid="text-goals-title">
          <Flag className="h-6 w-6 text-primary" />
          Goals
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Set targets, track progress, and stay accountable to your key milestones.
        </p>
      </div>

      <Card data-testid="card-goals-empty">
        <CardContent className="py-12 text-center space-y-3">
          <Target className="h-10 w-10 mx-auto text-muted-foreground" />
          <h2 className="text-base font-semibold" data-testid="text-goals-empty">No goals yet</h2>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            Saving your own goals is not available yet. Your live MRR, runway and churn are on the
            overview.
          </p>
          <Button variant="outline" size="sm" onClick={() => setLocation("/overview")} data-testid="button-goals-overview">
            Go to overview
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
