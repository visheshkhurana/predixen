import React, { ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { getErrorMessage } from '@/lib/errors';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  inline?: boolean;
  label?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

function toSafeError(value: unknown): Error {
  if (value instanceof Error) return value;
  return new Error(getErrorMessage(value, 'An unexpected error occurred'));
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(rawError: unknown): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error: toSafeError(rawError),
    };
  }

  componentDidCatch(rawError: unknown, errorInfo: React.ErrorInfo) {
    const error = toSafeError(rawError);
    console.error('ErrorBoundary caught an error:', error);
    console.error('Component Stack:', errorInfo.componentStack);

    this.setState({ error, errorInfo });

    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  resetError = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.resetError);
      }

      const safeMessage = getErrorMessage(this.state.error, 'An unexpected error occurred');
      const label = this.props.label || 'this section';

      if (this.props.inline) {
        return (
          <div className="p-4 rounded-md border border-destructive/30 bg-destructive/5" data-testid="error-boundary-inline">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-destructive">
                  Failed to load {label}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {safeMessage}
                </p>
                <Button
                  onClick={this.resetError}
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  data-testid="button-error-retry-inline"
                >
                  <RefreshCw className="h-3 w-3 mr-1" />
                  Retry
                </Button>
              </div>
            </div>
          </div>
        );
      }

      return (
        <div className="flex items-center justify-center min-h-screen bg-background p-4">
          <div className="w-full max-w-md space-y-4">
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Something Went Wrong</AlertTitle>
              <AlertDescription className="mt-2">
                <p className="text-sm mb-2">
                  An unexpected error occurred. Please try again or contact support if the problem persists.
                </p>
                {import.meta.env.DEV && (
                  <details className="mt-3 text-xs bg-destructive/10 p-2 rounded border border-destructive/20">
                    <summary className="cursor-pointer font-medium mb-1">Error Details</summary>
                    <pre className="overflow-auto text-xs whitespace-pre-wrap break-words">
                      {safeMessage}
                      {'\n\n'}
                      {this.state.errorInfo?.componentStack}
                    </pre>
                  </details>
                )}
              </AlertDescription>
            </Alert>

            <div className="flex gap-2">
              <Button
                onClick={this.resetError}
                variant="default"
                className="flex-1"
                data-testid="button-error-retry"
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
                data-testid="button-error-go-home"
              >
                Go Home
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
