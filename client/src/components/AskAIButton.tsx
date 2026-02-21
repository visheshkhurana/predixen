import { useState } from "react";
import { useLocation } from "wouter";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

const SUGGESTED_PROMPTS = [
  "Analyze my financial health",
  "What scenarios should I run?",
  "How can I extend my runway?",
];

export function AskAIButton() {
  const [location] = useLocation();
  const [isHovering, setIsHovering] = useState(false);

  // Hide on auth, onboarding, and admin pages
  const shouldHide =
    location === "/auth" ||
    location === "/onboarding" ||
    location.startsWith("/admin") ||
    location === "/pricing" ||
    location === "/demo" ||
    location === "/owner-console" ||
    location.startsWith("/scenarios/shared/");

  if (shouldHide) {
    return null;
  }

  return (
    <Popover open={isHovering} onOpenChange={setIsHovering}>
      <PopoverTrigger asChild>
        <Button
          onClick={() => {
            window.location.href = "/copilot";
          }}
          className="fixed bottom-6 right-6 rounded-full shadow-lg h-14 w-14 p-0 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white"
          onMouseEnter={() => setIsHovering(true)}
          onMouseLeave={() => setIsHovering(false)}
          data-testid="button-ask-ai"
        >
          <Sparkles className="h-6 w-6" />
        </Button>
      </PopoverTrigger>
      <PopoverContent side="top" align="end" className="w-56">
        <div className="space-y-2">
          <p className="text-xs font-semibold text-foreground">Suggested prompts:</p>
          <div className="space-y-1.5">
            {SUGGESTED_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                onClick={() => {
                  window.location.href = "/copilot";
                }}
                className="w-full text-xs text-left p-2 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
