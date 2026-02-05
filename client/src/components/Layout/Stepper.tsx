import { Check } from 'lucide-react';
import { Link, useLocation } from 'wouter';
import { cn } from '@/lib/utils';

interface StepperProps {
  currentStep: 'truth' | 'simulation' | 'decision';
}

const steps = [
  { id: 'truth', label: 'Truth', path: '/truth-scan' },
  { id: 'simulation', label: 'Simulation', path: '/scenarios' },
  { id: 'decision', label: 'Decision', path: '/decisions' },
];

export function Stepper({ currentStep }: StepperProps) {
  const [location] = useLocation();
  const currentIndex = steps.findIndex((s) => s.id === currentStep);
  
  return (
    <div className="flex items-center gap-2" data-testid="stepper">
      {steps.map((step, index) => {
        const isCompleted = index < currentIndex;
        const isCurrent = index === currentIndex;
        const isActive = location === step.path;
        
        return (
          <div key={step.id} className="flex items-center">
            <Link href={step.path}>
              <div
                className={cn(
                  'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-colors cursor-pointer hover-elevate',
                  isCompleted && 'bg-emerald-500/20 text-emerald-400',
                  (isCurrent || isActive) && 'bg-primary/20 text-primary',
                  !isCompleted && !isCurrent && !isActive && 'text-muted-foreground'
                )}
                data-testid={`step-${step.id}`}
              >
                {isCompleted ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <span
                    className={cn(
                      'w-5 h-5 rounded-full flex items-center justify-center text-xs border',
                      (isCurrent || isActive) ? 'border-primary bg-primary text-primary-foreground' : 'border-muted-foreground'
                    )}
                  >
                    {index + 1}
                  </span>
                )}
                <span>{step.label}</span>
              </div>
            </Link>
            {index < steps.length - 1 && (
              <div className="w-8 h-px bg-border mx-2" />
            )}
          </div>
        );
      })}
    </div>
  );
}
