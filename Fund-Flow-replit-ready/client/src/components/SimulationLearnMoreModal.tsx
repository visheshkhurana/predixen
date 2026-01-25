import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { HelpCircle, TrendingUp, BarChart3, Percent } from 'lucide-react';

interface SimulationLearnMoreModalProps {
  testId?: string;
}

export function SimulationLearnMoreModal({ testId = 'learn-more-modal' }: SimulationLearnMoreModalProps) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" data-testid={`${testId}-trigger`}>
          <HelpCircle className="h-4 w-4 mr-2" />
          Learn about simulations
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Understanding Monte Carlo Simulations</DialogTitle>
          <DialogDescription>
            How Predixen projects your company's financial future
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-6 py-4">
          <section className="space-y-3">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-primary" />
              <h3 className="font-semibold">What is Monte Carlo Simulation?</h3>
            </div>
            <p className="text-sm text-muted-foreground">
              Monte Carlo simulation runs thousands of possible scenarios (typically 1,000) by 
              randomly varying key inputs within their expected ranges. Instead of a single 
              projection, you get a distribution of possible outcomes, showing best-case, 
              worst-case, and most likely scenarios.
            </p>
          </section>
          
          <section className="space-y-3">
            <div className="flex items-center gap-2">
              <Percent className="h-5 w-5 text-primary" />
              <h3 className="font-semibold">Understanding P10 / P50 / P90</h3>
            </div>
            <div className="space-y-2 text-sm text-muted-foreground">
              <div className="p-3 rounded-md bg-muted">
                <p><strong className="text-foreground">P10 (10th Percentile)</strong> - Pessimistic outcome. Only 10% of simulations performed worse than this.</p>
              </div>
              <div className="p-3 rounded-md bg-muted">
                <p><strong className="text-foreground">P50 (50th Percentile / Median)</strong> - Most likely outcome. Half the simulations were better, half were worse.</p>
              </div>
              <div className="p-3 rounded-md bg-muted">
                <p><strong className="text-foreground">P90 (90th Percentile)</strong> - Optimistic outcome. Only 10% of simulations performed better than this.</p>
              </div>
            </div>
          </section>
          
          <section className="space-y-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-primary" />
              <h3 className="font-semibold">How Parameters Affect Outcomes</h3>
            </div>
            <div className="space-y-2 text-sm text-muted-foreground">
              <div className="p-3 rounded-md bg-muted">
                <p><strong className="text-foreground">Pricing Change</strong> - Increasing prices typically improves revenue but may reduce growth rate. A +10% price increase might add 5-8% to ARPU but reduce new customer acquisition by 2-3%.</p>
              </div>
              <div className="p-3 rounded-md bg-muted">
                <p><strong className="text-foreground">Growth Uplift</strong> - Accelerates revenue growth rate. +5% is conservative, +10% is moderate (achievable with focused GTM), +20% is aggressive (requires significant investment).</p>
              </div>
              <div className="p-3 rounded-md bg-muted">
                <p><strong className="text-foreground">Burn Reduction</strong> - Extends runway by reducing monthly expenses. +20% (cost cutting) extends runway significantly but may slow growth. Negative values indicate increased spending.</p>
              </div>
              <div className="p-3 rounded-md bg-muted">
                <p><strong className="text-foreground">Fundraising</strong> - Adds a cash injection at a specific month. Consider timing relative to your runway and how it affects your negotiating position.</p>
              </div>
            </div>
          </section>
          
          <section className="space-y-3">
            <h3 className="font-semibold">Tips for Interpreting Results</h3>
            <ul className="space-y-2 text-sm text-muted-foreground list-disc pl-4">
              <li>Focus on the P50 (median) for planning, but consider P10 for risk management</li>
              <li>Survival probability above 80% at 18 months is generally healthy</li>
              <li>Run multiple scenarios to compare trade-offs between growth and runway</li>
              <li>Use the comparison table to see how different strategies stack up</li>
              <li>Wide bands between P10/P90 indicate high uncertainty in outcomes</li>
            </ul>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  );
}
