import React from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface PageErrorFallbackProps {
  error: Error;
  reset: () => void;
  pageName?: string;
}

/**
 * Page-level Error Fallback Component
 * Provides a more detailed error UI for individual pages with suggestions
 *
 * Usage:
 * <ErrorBoundary fallback={(error, reset) => <PageErrorFallback error={error} reset={reset} pageName="Scenarios" />}>
 *   <YourPage />
 * </ErrorBoundary>
 */
export function PageErrorFallback({
  error,
  reset,
  pageName = 'Page',
}: PageErrorFallbackProps) {
  const isNetworkError = error.message?.toLowerCase().includes('network') ||
    error.message?.toLowerCase().includes('fetch') ||
    error.message?.toLowerCase().includes('timeout');

  const isDatabaseError = error.message?.toLowerCase().includes('database') ||
    error.message?.toLowerCase().includes('data') ||
    error.message?.toLowerCase().includes('query');

  const getSuggestions = () => {
    if (isNetworkError) {
      return [
        'Check your internet connection',
        'Try refreshing the page',
        'Clear your browser cache and cookies',
        'Wait a moment and try again',
      ];
    }
    if (isDatabaseError) {
      return [
        'Refresh the page to reload data',
        'Check if your data is complete and valid',
        'Try navigating to another page and back',
        'Contact support if the issue persists',
      ];
    }
    return [
      'Try refreshing the page',
      'Clear your browser cache',
      'Disable browser extensions and try again',
      'Use a different browser if the problem continues',
    ];
  };

  const errorType = isNetworkError
    ? 'Network Error'
    : isDatabaseError
      ? 'Data Error'
      : 'Application Error';

  return (
    <div className="flex items-center justify-center min-h-screen bg-background p-4">
      <Card className="w-full max-w-lg border-destructive/50">
        <CardHeader className="space-y-2">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <CardTitle>Error on {pageName}</CardTitle>
          </div>
          <CardDescription>{errorType}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Error Message */}
          <Alert variant="destructive">
            <AlertTitle className="text-sm">What Happened</AlertTitle>
            <AlertDescription className="mt-2 text-xs">
              {error.message || 'An unexpected error occurred while loading this page.'}
            </AlertDescription>
          </Alert>

          {/* Suggestions */}
          <div className="space-y-2">
            <h4 className="font-medium text-sm">What you can try:</h4>
            <ul className="space-y-1.5">
              {getSuggestions().map((suggestion, index) => (
                <li key={index} className="flex gap-2 text-sm text-muted-foreground">
                  <span className="text-primary font-medium">•</span>
                  <span>{suggestion}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Error Details (Development Only) */}
          {process.env.NODE_ENV === 'development' && (
            <details className="text-xs bg-destructive/5 p-3 rounded border border-destructive/20">
              <summary className="cursor-pointer font-medium text-destructive/80 mb-2">
                Technical Details
              </summary>
              <pre className="overflow-auto whitespace-pre-wrap break-words text-destructive/70">
                {error.toString()}
              </pre>
            </details>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2 pt-2">
            <Button
              onClick={reset}
              variant="default"
              className="flex-1"
              size="sm"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </Button>
            <Button
              onClick={() => {
                window.location.href = '/';
              }}
              variant="outline"
              className="flex-1"
              size="sm"
            >
              <Home className="h-4 w-4 mr-2" />
              Go Home
            </Button>
          </div>

          {/* Support Message */}
          <p className="text-xs text-muted-foreground text-center pt-2">
            If this problem persists, please contact our support team.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
