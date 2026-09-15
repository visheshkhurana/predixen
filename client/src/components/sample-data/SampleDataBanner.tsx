import { FlaskConical } from 'lucide-react';
import { Link } from 'wouter';

/**
 * Persistent sample-data label on product routes so a first insight is never
 * mistaken for the founder's own numbers. Demo-account banner in App.tsx
 * stays separate (it also has to sign the visitor out).
 */
export function SampleDataBanner() {
  return (
    <div
      className="no-print flex items-center justify-center gap-2 bg-amber-500/15 border-b border-amber-500/30 px-3 py-1.5 text-xs font-medium text-amber-400"
      data-testid="banner-sample-data"
      role="status"
    >
      <FlaskConical className="h-3.5 w-3.5 shrink-0" />
      <span>
        Sample data — these insights use simulated numbers, not your company.{' '}
        <Link href="/data" className="underline hover:text-amber-300" data-testid="link-sample-replace-data">
          Replace with your data
        </Link>
      </span>
    </div>
  );
}
