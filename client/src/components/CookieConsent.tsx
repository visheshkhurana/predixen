import { useEffect, useState } from 'react';
import { Link } from 'wouter';
import { Button } from '@/components/ui/button';
import { Cookie } from 'lucide-react';
import { onConsentChange, readConsent, saveConsent } from '@/lib/consent';

// Mounted on marketing pages (MarketingLayout) and in the app shell. The choice
// is applied by lib/consent.ts; until it is made, tags run without storage.
export function CookieConsent() {
  const [visible, setVisible] = useState(() => typeof window !== 'undefined' && readConsent() === null);

  // Another mounted banner may record the choice first.
  useEffect(() => onConsentChange(() => setVisible(false)), []);

  if (!visible) return null;

  // Compact and bottom-LEFT: the floating Ask AI button lives bottom-right, and
  // on phones the banner stops short of it (right-20) instead of covering it.
  // Mobile bottom-24 clears the marketing pages' sticky sign-up bar.
  return (
    <div
      className="fixed bottom-24 left-3 right-20 z-[9999] rounded-lg border bg-background p-3 shadow-xl md:bottom-4 md:left-4 md:right-auto md:max-w-[340px]"
      role="region"
      aria-label="Cookie consent"
      data-testid="cookie-consent"
    >
      <div className="flex items-start gap-2.5">
        <Cookie className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground leading-relaxed">
            We use cookies for analytics and to measure our ads. Nothing is stored until you accept.{' '}
            <Link href="/privacy" className="underline underline-offset-2 hover:text-foreground">
              Privacy policy
            </Link>
          </p>
          <div className="flex gap-2">
            <Button
              size="sm"
              className="h-8 px-4 text-xs bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700"
              onClick={() => saveConsent('accepted')}
              data-testid="button-cookie-accept"
            >
              Accept
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-8 px-4 text-xs"
              onClick={() => saveConsent('declined')}
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
