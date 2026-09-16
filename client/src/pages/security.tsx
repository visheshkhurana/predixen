import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { useSEO } from "@/lib/seo";
import { ArrowRight } from "lucide-react";

export default function SecurityPage() {
  useSEO({
    title: "Security — Encryption, Privacy, and Compliance | FounderConsole",
    description:
      "How FounderConsole protects your data: AES-256 at rest, TLS in transit, OAuth2 read-only integrations, encrypted credentials, bcrypt passwords, US PostgreSQL with backups, GDPR, and work toward SOC2 Type II. We do not sell your data.",
    path: "/security",
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "WebPage",
      name: "Security — Encryption, Privacy, and Compliance | FounderConsole",
      description:
        "How FounderConsole protects your data: AES-256 at rest, TLS in transit, OAuth2 read-only integrations, US PostgreSQL with backups, GDPR, and work toward SOC2 Type II. We do not sell your data.",
      url: "https://founderconsole.ai/security",
      isPartOf: { "@type": "WebSite", name: "FounderConsole", url: "https://founderconsole.ai" },
    },
  });

  return (
    <MarketingLayout>
      <article className="mx-auto max-w-3xl px-4 py-16 md:py-20">
        <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-security-title">
          Security at FounderConsole
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          FounderConsole is privacy-first: your financial data is encrypted at rest and in transit. Read-only integrations. No data resale. Ever. This page restates the security claims already published on our FAQ, Privacy Policy, and About pages.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Encryption at rest and in transit
        </h2>
        <p className="mt-3 text-muted-foreground">
          All data is encrypted using AES-256 at rest and TLS in transit. All connections use HTTPS/TLS encryption in transit.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Integrations and credentials
        </h2>
        <p className="mt-3 text-muted-foreground">
          Integrations use OAuth2 with read-only access where possible. Credentials are stored encrypted. Passwords are hashed using bcrypt before storage.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Where data is stored
        </h2>
        <p className="mt-3 text-muted-foreground">
          Your data is stored in US-based PostgreSQL databases with automated daily backups. See the{" "}
          <Link href="/product" className="text-primary hover:underline" data-testid="link-security-product">
            product
          </Link>{" "}
          overview for what the platform does with connected data.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Compliance
        </h2>
        <p className="mt-3 text-muted-foreground">
          We are fully GDPR compliant and are actively working toward SOC2 Type II certification. We do not claim SOC2 certification. You can request a full data export or deletion at any time.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          No data resale
        </h2>
        <p className="mt-3 text-muted-foreground">
          We never sell your data to third parties. No data resale. Ever. The full legal text is on our{" "}
          <Link href="/privacy" className="text-primary hover:underline" data-testid="link-security-privacy">
            Privacy Policy
          </Link>{" "}
          and{" "}
          <Link href="/terms" className="text-primary hover:underline" data-testid="link-security-terms">
            Terms of Service
          </Link>
          .
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Questions
        </h2>
        <p className="mt-3 text-muted-foreground">
          <Link href="/contact" className="text-primary hover:underline" data-testid="link-security-contact">
            Contact us
          </Link>{" "}
          if you have a privacy or security question. When you are ready to connect live data, get started free.
        </p>
        <div className="mt-8">
          <Button asChild data-testid="button-security-signup">
            <Link href="/signup">
              Get started free
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>
      </article>
    </MarketingLayout>
  );
}
