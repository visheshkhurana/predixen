import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Shield, Rocket, Scale } from "lucide-react";
import { cn } from "@/lib/utils";

export type SimulationGoal = 'extend_runway' | 'accelerate_growth' | 'balance';

interface GoalOption {
  id: SimulationGoal;
  title: string;
  description: string;
  icon: typeof Shield;
  color: string;
  metrics: string[];
}

const GOALS: GoalOption[] = [
  {
    id: 'extend_runway',
    title: 'Extend Runway',
    description: 'Maximize survival time by reducing burn and extending cash runway to 18+ months',
    icon: Shield,
    color: 'text-emerald-500',
    metrics: ['Target 18+ months runway', 'Cost optimization focus', 'Conservative growth'],
  },
  {
    id: 'accelerate_growth',
    title: 'Accelerate Growth',
    description: 'Invest aggressively in sales and marketing to capture market share quickly',
    icon: Rocket,
    color: 'text-blue-500',
    metrics: ['Rapid ARR growth', 'Increased burn rate', 'Higher risk/reward'],
  },
  {
    id: 'balance',
    title: 'Balance Growth & Burn',
    description: 'Find the optimal balance between sustainable growth and healthy runway',
    icon: Scale,
    color: 'text-amber-500',
    metrics: ['Sustainable growth', 'Moderate burn', 'Risk-balanced approach'],
  },
];

interface GoalSelectorProps {
  selectedGoal?: SimulationGoal;
  onSelectGoal: (goal: SimulationGoal) => void;
  className?: string;
}

export function GoalSelector({ selectedGoal, onSelectGoal, className }: GoalSelectorProps) {
  return (
    <div className={cn("space-y-4", className)}>
      <div className="text-center mb-6">
        <h2 className="text-xl font-semibold">What's your primary objective?</h2>
        <p className="text-muted-foreground mt-1">
          Select a goal to see recommended strategies and scenarios
        </p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {GOALS.map((goal) => {
          const Icon = goal.icon;
          const isSelected = selectedGoal === goal.id;
          
          return (
            <Card
              key={goal.id}
              onClick={() => onSelectGoal(goal.id)}
              className={cn(
                "cursor-pointer transition-all hover-elevate",
                isSelected && "ring-2 ring-primary border-primary"
              )}
              data-testid={`goal-card-${goal.id}`}
            >
              <CardHeader className="pb-3">
                <div className={cn("w-10 h-10 rounded-lg flex items-center justify-center mb-2", 
                  isSelected ? "bg-primary/20" : "bg-muted"
                )}>
                  <Icon className={cn("w-5 h-5", goal.color)} />
                </div>
                <CardTitle className="text-lg">{goal.title}</CardTitle>
                <CardDescription className="text-sm">
                  {goal.description}
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                <ul className="space-y-1">
                  {goal.metrics.map((metric, idx) => (
                    <li key={idx} className="text-xs text-muted-foreground flex items-center gap-2">
                      <span className={cn("w-1.5 h-1.5 rounded-full", 
                        isSelected ? "bg-primary" : "bg-muted-foreground/50"
                      )} />
                      {metric}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

export { GOALS };
