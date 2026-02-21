import { createRoot } from "react-dom/client";
import App from "./App";
import { ErrorBoundary } from "./components/ErrorBoundary";
import "./index.css";

/**
 * Top-level Error Boundary
 * This is the final safety net that catches any errors that slip through
 * the application-level error boundaries
 */
const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element not found. Ensure there is an element with id='root' in index.html.");
}
createRoot(rootElement).render(
  <ErrorBoundary
    onError={(error) => {
      // Global error logging - could be sent to error tracking service (Sentry, LogRocket, etc.)
      console.error('Uncaught Error at Root Level:', error);

      // Example: Send to error tracking service
      // if (window.location.hostname !== 'localhost') {
      //   fetch('/api/errors', {
      //     method: 'POST',
      //     headers: { 'Content-Type': 'application/json' },
      //     body: JSON.stringify({
      //       message: error.message,
      //       stack: error.stack,
      //       url: window.location.href,
      //       userAgent: navigator.userAgent,
      //     }),
      //   }).catch(() => {});
      // }
    }}
  >
    <App />
  </ErrorBoundary>
);
