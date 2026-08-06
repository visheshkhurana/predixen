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

/**
 * Stale-deploy recovery: after a new deploy, lazy route chunks from the old
 * build 404 in already-open tabs ("Failed to fetch dynamically imported
 * module"), which used to surface the Something Went Wrong boundary when the
 * user clicked a nav link. Vite emits `vite:preloadError` for exactly this —
 * reload once to pick up the new build (one-shot guard to avoid loops).
 */
window.addEventListener("vite:preloadError", (event) => {
  event.preventDefault();
  const key = "fc-chunk-reload";
  if (sessionStorage.getItem(key)) return; // already retried — let the boundary show
  sessionStorage.setItem(key, "1");
  window.location.reload();
});
window.addEventListener("load", () => {
  // successful load — clear the guard so the next deploy can retry again
  setTimeout(() => sessionStorage.removeItem("fc-chunk-reload"), 10_000);
});

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
