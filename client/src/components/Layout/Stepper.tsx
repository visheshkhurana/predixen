import { useLocation } from 'wouter';
import { cn } from '@/lib/utils';
import { Link } from 'wouter';
import { ShieldCheck, FlaskConical, Lightbulb, ChevronRight } from 'lucide-react';

interface StepperProps {
  currentStep: 'truth' | 'simulation' | 'decision';
}

const steps = [
  { id: 'truth', label: 'Know Your Truth', path: '/truth', icon: ShieldCheck },
  { id: 'simulation', label: 'Simulate', path: '/scenarios', icon: FlaskConical },
  { id: 'decision', label: 'Decide & Act', path: '/decisions', icon: Lightbulb },
];

const routeToStep: Record<string, string> = {
  '/truth': 'truth',
  '/data': 'truth',
  '/overview': 'truth',
  '/scenarios': 'simulation',
  '/decisions': 'decision',
  '/alerts': 'decision',
  '/goals': 'decision',
};

export function Stepper({ currentStep }: StepperProps) {
  const [location] = useLocation();
  const activeStepId = routeToStep[location] || currentStep;

  return (
    <div className="flex items-center gap-1 flex-wrap" data-testid="stepper">
      {steps.map((step, index) => {
        const isActive = step.id === activeStepId;
        const Icon = step.icon;

        return (
          <div key={step.id} className="flex items-center">
            <Link href={step.path}>
              <div
                className={cn(
                  'flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer',
                  isActive
                    ? 'bg-primary/15 text-primary'
                    : 'text-muted-foreground hover-elevate'
                )}
                data-testid={`step-${step.id}`}
              >
                <Icon className="h-3.5 w-3.5" />
                <span className="hidden lg:inline">{step.label}</span>
              </div>
            </Link>
            {index < steps.length - 1 && (
              <ChevronRight className="h-3 w-3 text-muted-foreground/50 mx-0.5 shrink-0" />
            )}
          </div>
        );
      })}
    </div>
  );
}
