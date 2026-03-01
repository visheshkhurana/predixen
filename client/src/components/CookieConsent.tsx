import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Cookie } from 'lucide-react';

export function CookieConsent() {
  const [visible, setVisible] = useState(() => !localStorage.getItem('cookie-consent'));

  if (!visible) return null;

  const handleChoice = (choice: 'accepted' | 'declined') => {
    localStorage.setItem('cookie-consent', choice);
    setVisible(false);
  };

  return (
    <div
      className="fixed bottom-5 left-5 z-[1000] max-w-[380px] rounded-xl border bg-background p-4 shadow-2xl"
      data-testid="cookie-consent"
    >
      <div className="flex items-start gap-3">
        <Cookie className="h-5 w-5 text-indigo-400 shrink-0 mt-0.5" />
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground leading-relaxed">
            We use cookies for analytics to improve your experience.
          </p>
          <div className="flex gap-2">
            <Button
              size="sm"
              className="h-8 px-4 text-xs bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700"
              onClick={() => handleChoice('accepted')}
              data-testid="button-cookie-accept"
            >
              Accept
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-8 px-4 text-xs"
              onClick={() => handleChoice('declined')}
              data-testid="button-cookie-decline"
            >
              Decline
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}