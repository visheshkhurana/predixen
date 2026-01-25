import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { X, ChevronLeft, ChevronRight, HelpCircle, Lightbulb, Target, DollarSign, Rocket } from 'lucide-react';
import { cn } from '@/lib/utils';

interface TutorialStep {
  id: number;
  title: string;
  description: string;
  icon: React.ElementType;
  tips: string[];
}

const TUTORIAL_STEPS: TutorialStep[] = [
  {
    id: 1,
    title: 'Choose a Starting Template',
    description: 'Templates provide pre-configured scenarios based on common startup strategies. Select one to get started quickly, or skip to create a custom scenario from scratch.',
    icon: Lightbulb,
    tips: [
      'Baseline (Status Quo) is great for comparison',
      'Use "Conservative Cut" when runway is a concern',
      'Try multiple scenarios to compare outcomes',
    ],
  },
  {
    id: 2,
    title: 'Adjust Financial Parameters',
    description: 'Fine-tune the financial levers that directly impact your runway. Each slider affects how your company performs in the simulation.',
    icon: Target,
    tips: [
      'Pricing changes affect revenue but may impact growth',
      'Burn reduction extends runway but may slow hiring',
      'Watch the "Projected Impact" card for real-time feedback',
      'Click on any value to type an exact number',
    ],
  },
  {
    id: 3,
    title: 'Model Fundraising',
    description: 'Add a funding round to see how it affects your runway. You can specify when the round closes and how much you expect to raise.',
    icon: DollarSign,
    tips: [
      'Leave empty if not planning a fundraise',
      'Bridge rounds are typically $250K-$500K',
      'Seed rounds are typically $1M-$3M',
      'Series A rounds are typically $5M-$15M',
    ],
  },
  {
    id: 4,
    title: 'Review and Run',
    description: 'Name your scenario and review all your inputs. When ready, run the Monte Carlo simulation to see probability distributions of outcomes.',
    icon: Rocket,
    tips: [
      'Give your scenario a descriptive name',
      'Review the summary to verify your inputs',
      'Simulations run 1,000 iterations for accuracy',
      'Compare multiple scenarios in the Results tab',
    ],
  },
];

interface ScenarioTutorialProps {
  currentStep: number;
  onClose: () => void;
  onNeverShowAgain: () => void;
}

export function ScenarioTutorial({ currentStep, onClose, onNeverShowAgain }: ScenarioTutorialProps) {
  const [tutorialStep, setTutorialStep] = useState(0);
  const step = TUTORIAL_STEPS[tutorialStep];
  const StepIcon = step.icon;

  return (
    <Card className="fixed bottom-4 right-4 w-96 z-50 shadow-lg border-primary/20" data-testid="tutorial-card">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-full bg-primary/10">
              <StepIcon className="h-4 w-4 text-primary" />
            </div>
            <div>
              <CardTitle className="text-base">Step {step.id}: {step.title}</CardTitle>
              <CardDescription className="text-xs">
                Tutorial {tutorialStep + 1} of {TUTORIAL_STEPS.length}
              </CardDescription>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} data-testid="tutorial-close">
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">{step.description}</p>
        
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">Tips:</p>
          <ul className="space-y-1">
            {step.tips.map((tip, i) => (
              <li key={i} className="flex items-start gap-2 text-xs">
                <span className="text-primary mt-0.5">•</span>
                <span>{tip}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="flex items-center justify-between pt-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setTutorialStep(Math.max(0, tutorialStep - 1))}
            disabled={tutorialStep === 0}
            data-testid="tutorial-prev"
          >
            <ChevronLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          
          <div className="flex gap-1">
            {TUTORIAL_STEPS.map((_, i) => (
              <button
                key={i}
                onClick={() => setTutorialStep(i)}
                className={cn(
                  'w-2 h-2 rounded-full transition-colors',
                  i === tutorialStep ? 'bg-primary' : 'bg-muted-foreground/30'
                )}
                aria-label={`Go to tutorial step ${i + 1}`}
              />
            ))}
          </div>
          
          {tutorialStep < TUTORIAL_STEPS.length - 1 ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setTutorialStep(tutorialStep + 1)}
              data-testid="tutorial-next"
            >
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          ) : (
            <Button
              size="sm"
              onClick={onClose}
              data-testid="tutorial-finish"
            >
              Got it!
            </Button>
          )}
        </div>

        <div className="border-t pt-3">
          <Button
            variant="ghost"
            size="sm"
            className="text-xs text-muted-foreground p-0 h-auto"
            onClick={onNeverShowAgain}
            data-testid="tutorial-never-show"
          >
            Don't show this again
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

interface TutorialTriggerProps {
  onClick: () => void;
}

export function TutorialTrigger({ onClick }: TutorialTriggerProps) {
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={onClick}
      className="gap-1.5"
      data-testid="button-show-tutorial"
    >
      <HelpCircle className="h-4 w-4" />
      Help
    </Button>
  );
}
