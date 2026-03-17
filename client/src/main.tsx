import { createRoot } from "react-dom/client";
import { HelmetProvider } from "react-helmet-async";
import App from "./App";
import { ErrorBoundary } from "./components/ErrorBoundary";
import "./index.css";
import { initSentry } from "./lib/sentry";
import { Sentry } from "./lib/sentry";

/**
 * Top-level Error Boundary
 * This is the final safety net that catches any errors that slip through
 * the application-level error boundaries
 */
// Initialize Sentry error tracking
initSentry();

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element not found. Ensure there is an element with id='root' in index.html.");
}
createRoot(rootElement).render(
  <HelmetProvider>
    <ErrorBoundary
      onError={(error) => {
        console.error('Uncaught Error at Root Level:', error);
          Sentry.captureException(error);
      }}
    >
      <App />
    </ErrorBoundary>
  </HelmetProvider>
);
