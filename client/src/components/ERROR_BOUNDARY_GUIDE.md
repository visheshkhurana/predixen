# Error Boundary Implementation Guide

## Overview

This application now has comprehensive Error Boundary support to prevent white-screen crashes. The error boundary system consists of three layers of protection:

1. **Top-Level Boundary** (main.tsx) - Final safety net for any uncaught errors
2. **Application Boundary** (App.tsx) - Catches errors in the main app structure
3. **Route-Level Boundaries** (App.tsx) - Catches errors in specific authenticated and admin routes

## Components

### 1. ErrorBoundary.tsx
**Location:** `/client/src/components/ErrorBoundary.tsx`

The main error boundary component. It's a class component (required for error boundaries in React) that catches React rendering errors.

**Features:**
- Catches and logs errors with component stack
- Shows user-friendly fallback UI
- "Try Again" button to reset error state
- Optional custom fallback component
- Optional error callback for analytics/logging
- Development mode shows detailed error info

**Props:**
```typescript
interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode; // Optional custom UI
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void; // Optional error logging
}
```

**Basic Usage:**
```tsx
<ErrorBoundary>
  <YourComponent />
</ErrorBoundary>
```

**With Custom Fallback:**
```tsx
<ErrorBoundary
  fallback={(error, reset) => (
    <CustomErrorUI error={error} onRetry={reset} />
  )}
  onError={(error, info) => {
    // Send to error tracking service
    console.error('Error:', error);
  }}
>
  <YourComponent />
</ErrorBoundary>
```

### 2. PageErrorFallback.tsx
**Location:** `/client/src/components/PageErrorFallback.tsx`

A pre-built page-level error UI component for use as a fallback. Shows:
- Error type classification (Network, Data, Application)
- User-friendly error description
- Contextual suggestions based on error type
- Technical details (development mode only)
- "Try Again" and "Go Home" buttons
- Support message

**Props:**
```typescript
interface PageErrorFallbackProps {
  error: Error;
  reset: () => void;
  pageName?: string; // e.g., "Scenarios", "Overview", "Admin Panel"
}
```

**Usage:**
```tsx
<ErrorBoundary
  fallback={(error, reset) => (
    <PageErrorFallback
      error={error}
      reset={reset}
      pageName="Scenarios"
    />
  )}
>
  <ScenariosPage />
</ErrorBoundary>
```

## Current Implementation

### Top-Level Protection (main.tsx)
The entire app is wrapped with an ErrorBoundary to catch any errors that slip through lower-level boundaries.

```typescript
<ErrorBoundary
  onError={(error) => {
    console.error('Uncaught Error at Root Level:', error);
    // Could send to error tracking service
  }}
>
  <App />
</ErrorBoundary>
```

### Application-Level Protection (App.tsx)
The App component is wrapped to protect the QueryClientProvider, ThemeProvider, and other core providers.

### Route-Level Protection (App.tsx)
Both `AuthenticatedRoute` and `AdminRoute` are wrapped with page-level error boundaries.

**AuthenticatedRoute:**
```tsx
<ErrorBoundary
  fallback={(error, reset) => (
    <PageErrorFallback error={error} reset={reset} pageName="Page" />
  )}
  onError={(error, info) => {
    console.error('Authenticated Route Error:', error);
  }}
>
  <Component />
</ErrorBoundary>
```

**AdminRoute:**
```tsx
<ErrorBoundary
  fallback={(error, reset) => (
    <PageErrorFallback error={error} reset={reset} pageName="Admin Panel" />
  )}
  onError={(error, info) => {
    console.error('Admin Route Error:', error);
  }}
>
  <AdminLayout>
    <Component />
  </AdminLayout>
</ErrorBoundary>
```

## Adding Error Boundaries to New Components

### Wrapping a New Page
If you create a new page component, it will automatically be wrapped by the route-level error boundary. No additional action needed.

### Wrapping a Custom Component
If you want to add error boundaries to specific components within pages:

```tsx
import { ErrorBoundary } from '@/components/ErrorBoundary';

function MyComponent() {
  return (
    <ErrorBoundary
      fallback={(error, reset) => (
        <div className="p-4 text-red-500">
          <p>Component failed to load</p>
          <button onClick={reset}>Retry</button>
        </div>
      )}
    >
      <RiskyComponent />
    </ErrorBoundary>
  );
}
```

### Wrapping Multiple Components
```tsx
<ErrorBoundary fallback={(error, reset) => <CustomError />}>
  <Component1 />
  <Component2 />
  <Component3 />
</ErrorBoundary>
```

## Error Logging and Analytics

### Console Logging
All errors are logged to the console with:
- Error message
- Component stack (development)
- Error type (Router, Authenticated Route, Admin Route, Root Level)

### Custom Error Logging
You can pass an `onError` callback to send errors to an error tracking service:

```tsx
<ErrorBoundary
  onError={(error, errorInfo) => {
    // Send to Sentry, LogRocket, or your own service
    fetch('/api/errors', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        url: window.location.href,
        timestamp: new Date().toISOString(),
      }),
    }).catch(() => {});
  }}
>
  <App />
</ErrorBoundary>
```

### Development Mode
In development (`NODE_ENV === 'development'`), error details are shown in expandable `<details>` elements, allowing developers to see:
- Full error message
- Stack trace
- Component stack

This is hidden in production for security.

## What Errors Are Caught

Error Boundaries catch errors that occur:
- During rendering
- In lifecycle methods
- In constructors

Error Boundaries do **NOT** catch:
- Event handlers (use try-catch instead)
- Asynchronous code (setTimeout, Promises)
- Server-side rendering errors
- Errors thrown in the error boundary itself

## Testing Error Boundaries

### Trigger an Error Deliberately
```tsx
function BuggyComponent() {
  const [count, setCount] = useState(0);

  // This will cause an error when count > 0
  if (count > 0) {
    throw new Error('Test error boundary');
  }

  return (
    <button onClick={() => setCount(count + 1)}>
      Click me
    </button>
  );
}
```

### Verify the Fallback Works
1. Wrap the component with ErrorBoundary
2. Trigger the error
3. Confirm the fallback UI appears
4. Click "Try Again" to verify reset functionality

## Best Practices

1. **Use Multiple Boundaries**: Don't rely solely on the root-level boundary. Add boundaries at strategic points.

2. **Meaningful Fallbacks**: Provide context-specific error messages and recovery options.

3. **Error Logging**: Always implement error logging for production diagnostics.

4. **Development vs Production**: Show detailed errors in development, generic messages in production.

5. **User Communication**: Help users understand what went wrong and what they can do.

6. **Recovery Options**: Always provide a way to retry or navigate elsewhere.

## Error Types and Suggestions

The PageErrorFallback component intelligently detects error types and provides relevant suggestions:

**Network Errors** (Network, Fetch, Timeout)
- Check your internet connection
- Try refreshing the page
- Clear your browser cache and cookies
- Wait a moment and try again

**Data Errors** (Database, Data, Query)
- Refresh the page to reload data
- Check if your data is complete and valid
- Try navigating to another page and back
- Contact support if the issue persists

**Application Errors** (Other)
- Try refreshing the page
- Clear your browser cache
- Disable browser extensions and try again
- Use a different browser if the problem continues

## Future Enhancements

Possible improvements:
- Integrate with error tracking service (Sentry, LogRocket)
- Add error replay functionality
- Implement error rate monitoring
- Add user feedback collection
- Create admin panel for error monitoring
- Add sourcemap support for stack traces
- Implement error deduplication
- Add error recovery suggestions from ML

## References

- [React Error Boundaries Documentation](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary)
- [Error Handling in React](https://react.dev/reference/react/useCallback#handling-rendering-errors-in-an-error-boundary)

## Support

For issues or questions about error boundaries, please refer to:
1. This guide
2. The component JSDoc comments
3. The implementation in App.tsx
4. The React documentation
