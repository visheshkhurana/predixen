/**
 * Test Component for Error Boundaries
 *
 * This component is useful for testing error boundary functionality.
 * It intentionally throws errors when triggered by user action.
 *
 * IMPORTANT: This is for development/testing ONLY.
 * Remove or comment out in production builds.
 *
 * Usage in development:
 * 1. Import this component
 * 2. Wrap it with ErrorBoundary
 * 3. Click the buttons to trigger errors
 * 4. Verify error UI appears
 * 5. Click "Try Again" to reset
 *
 * Example:
 * ```tsx
 * import { ErrorBoundaryTestComponent } from '@/components/ErrorBoundaryTestComponent';
 * import { ErrorBoundary } from '@/components/ErrorBoundary';
 *
 * export function TestPage() {
 *   return (
 *     <ErrorBoundary>
 *       <ErrorBoundaryTestComponent />
 *     </ErrorBoundary>
 *   );
 * }
 * ```
 */

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle } from 'lucide-react';

function BuggyComponent() {
  const [shouldError, setShouldError] = useState(false);

  if (shouldError) {
    throw new Error(
      'This is a test error! The Error Boundary should catch this and display a fallback UI.'
    );
  }

  return (
    <div className="space-y-4">
      <p>This component is safe right now.</p>
      <Button onClick={() => setShouldError(true)} variant="destructive">
        Click to Trigger Error
      </Button>
    </div>
  );
}

export function ErrorBoundaryTestComponent() {
  const [testMode, setTestMode] = useState(false);

  if (testMode) {
    return <BuggyComponent />;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          Error Boundary Test Component
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2 text-sm text-muted-foreground">
          <p>
            This is a test component for verifying Error Boundary functionality.
          </p>
          <p>
            Click the button below to switch to buggy mode, then trigger an error to test the Error Boundary.
          </p>
        </div>

        <div className="space-y-2">
          <Button
            onClick={() => setTestMode(true)}
            variant="outline"
            className="w-full"
          >
            Enter Test Mode
          </Button>

          <div className="text-xs text-muted-foreground space-y-1">
            <p>In test mode:</p>
            <ul className="list-disc list-inside space-y-1">
              <li>A button will appear to trigger an error</li>
              <li>Clicking it will throw an error</li>
              <li>The Error Boundary should catch it</li>
              <li>Click "Try Again" to reset and return here</li>
            </ul>
          </div>
        </div>

        <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded text-xs text-amber-600">
          NOTE: Remove this component from production builds. It is for testing only.
        </div>
      </CardContent>
    </Card>
  );
}
