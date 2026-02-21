import React, { ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

/**
 * Error Boundary Component
 * Catches React rendering errors and displays a user-friendly fallback UI
 *
 * Usage:
 * <ErrorBoundary>
 *   <YourComponent />
 * </ErrorBoundary>
 *
 * With custom fallback:
 * <ErrorBoundary fallback={(error, reset) => <CustomErrorUI />}>
 *   <YourComponent />
 * </ErrorBoundary>
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log to console for development
    console.error('ErrorBoundary caught an error:', error);
    console.error('Component Stack:', errorInfo.componentStack);

    // Update state with error details
    this.setState({ errorInfo });

    // Call optional onError callback for error logging/tracking
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
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.resetError);
      }

      // Default error UI
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
                {process.env.NODE_ENV === 'development' && this.state.error && (
                  <details className="mt-3 text-xs bg-destructive/10 p-2 rounded border border-destructive/20">
                    <summary className="cursor-pointer font-medium mb-1">Error Details</summary>
                    <pre className="overflow-auto text-xs whitespace-pre-wrap break-words">
                      {this.state.error.toString()}
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
