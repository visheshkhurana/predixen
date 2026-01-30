import { Button } from "@/components/ui/button";
import { Play, Save, RotateCcw, Loader2, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface StickyActionBarProps {
  onRunSimulation: () => void;
  onSaveScenario: () => void;
  onResetInputs: () => void;
  onBack?: () => void;
  onNext?: () => void;
  isRunning?: boolean;
  isSaving?: boolean;
  canRun?: boolean;
  canSave?: boolean;
  canGoBack?: boolean;
  canGoNext?: boolean;
  statusMessage?: string;
  currentStep?: number;
  totalSteps?: number;
  className?: string;
}

export function StickyActionBar({
  onRunSimulation,
  onSaveScenario,
  onResetInputs,
  onBack,
  onNext,
  isRunning = false,
  isSaving = false,
  canRun = true,
  canSave = false,
  canGoBack = false,
  canGoNext = false,
  statusMessage,
  currentStep,
  totalSteps,
  className,
}: StickyActionBarProps) {
  return (
    <div 
      className={cn(
        "fixed bottom-0 left-0 right-0 z-50 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80",
        className
      )}
      data-testid="sticky-action-bar"
    >
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            {onBack && (
              <Button
                variant="outline"
                size="sm"
                onClick={onBack}
                disabled={!canGoBack}
                className="gap-1"
                data-testid="button-back"
              >
                <ChevronLeft className="w-4 h-4" />
                Back
              </Button>
            )}
            
            {currentStep && totalSteps && (
              <div className="hidden sm:flex items-center gap-2 px-3">
                {Array.from({ length: totalSteps }).map((_, i) => (
                  <div
                    key={i}
                    className={cn(
                      "w-2 h-2 rounded-full transition-colors",
                      i + 1 === currentStep 
                        ? "bg-primary" 
                        : i + 1 < currentStep 
                          ? "bg-primary/50" 
                          : "bg-muted-foreground/30"
                    )}
                  />
                ))}
              </div>
            )}
          </div>
          
          <div className="flex-1 flex justify-center">
            {statusMessage && (
              <span className="text-sm text-muted-foreground hidden md:block">
                {statusMessage}
              </span>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={onResetInputs}
              disabled={isRunning}
              className="gap-1"
              data-testid="button-reset"
            >
              <RotateCcw className="w-4 h-4" />
              <span className="hidden sm:inline">Reset</span>
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={onSaveScenario}
              disabled={!canSave || isSaving}
              className="gap-1"
              data-testid="button-save-scenario"
            >
              {isSaving ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              <span className="hidden sm:inline">Save</span>
            </Button>
            
            {onNext ? (
              <Button
                size="sm"
                onClick={onNext}
                disabled={!canGoNext || isRunning}
                className="gap-1"
                data-testid="button-next"
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={onRunSimulation}
                disabled={!canRun || isRunning}
                className="gap-1"
                data-testid="button-run-simulation"
              >
                {isRunning ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Running...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    Run Simulation
                  </>
                )}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
