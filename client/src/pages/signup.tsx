import { lazy, Suspense } from "react";
import { Loader2 } from "lucide-react";
import { useSEO } from "@/lib/seo";

/**
 * /signup — the create-account page, and it can now create an account.
 *
 * It used to be a marketing article whose only real control was a button to
 * /auth?tab=register, so `/signup` was a URL that could not do the one thing
 * its name promised. PR #80 repointed the footer's "Get started" away from it
 * for exactly that reason, which left a canonical signup URL with almost no
 * inbound links. Rendering the same component the /auth route renders, in
 * register mode, makes the URL mean what it says and removes a click from the
 * funnel — and it is the smaller change than deleting a registered route whose
 * three pinned expectations would all have to move with it.
 *
 * `initialTab` is a default, not an override: /auth still opens on the login
 * tab, and /auth?tab=register still opens on register, because AuthPage's own
 * `?tab=` effect runs after this and wins.
 *
 * The server-rendered body lives in server/seo-prerender.ts
 * (`buildSignupBodyContent`) and is deliberately unchanged. It is the view a
 * crawler and a no-JS visitor get, and every link in it — the register funnel,
 * /product, /features, /pricing, and the three free tools — is still a real and
 * useful destination. `server/tests/signup-ssr.test.ts` pins that body; nothing
 * here touches it, so it stays true rather than being edited to match.
 *
 * Lazy, like /auth is in App.tsx, so this page does not pull the auth bundle
 * into every other route's chunk.
 */
const AuthPage = lazy(() => import("@/pages/auth"));

export default function SignupPage() {
  useSEO({
    title: "Get Started — Create a Free FounderConsole Account",
    description:
      "Create a free FounderConsole account to connect live data and run ongoing runway forecasts. Every feature is free during early access — no credit card required. Prefer a quick answer first? Try the free tools with no account.",
    path: "/signup",
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "WebPage",
      name: "Get Started — Create a Free FounderConsole Account",
      description:
        "Create a free FounderConsole account to connect live data and run ongoing runway forecasts. Every feature is free during early access — no credit card required.",
      url: "https://founderconsole.ai/signup",
      isPartOf: { "@type": "WebSite", name: "FounderConsole", url: "https://founderconsole.ai" },
    },
  });

  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <AuthPage initialTab="register" />
    </Suspense>
  );
}
