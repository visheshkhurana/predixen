import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { useSEO } from "@/lib/seo";

const faqSections = [
  {
    title: "Getting Started",
    items: [
      {
        question: "What problem does FounderConsole solve?",
        answer:
          "FounderConsole helps founders make explainable financial decisions under uncertainty using real-time forecasting and Monte Carlo confidence intervals. Instead of relying on a single spreadsheet forecast, you see the range of possible outcomes and the probability of hitting key targets.",
      },
      {
        question: "How do I get started?",
        answer:
          "Sign up for free (no credit card required), connect one or more data sources like QuickBooks, Stripe, or Mercury, and you'll have a baseline forecast with confidence intervals within 5 minutes.",
      },
      {
        question: "What do I get in the first 5 minutes?",
        answer:
          "A baseline forecast from your connected sources, one scenario simulation with confidence bands (P10/P50/P90), an AI narrative explaining your key risk drivers, and an investor-ready summary draft.",
      },
      {
        question: "Is there a demo I can try?",
        answer:
          "Yes — you can sign in with demo credentials or watch our product walkthrough on the Demo page. The demo includes sample company data so you can explore simulations, the AI copilot, and reporting features without connecting your own data.",
      },
    ],
  },
  {
    title: "Simulation Engine",
    items: [
      {
        question: "How is this different from a spreadsheet forecast?",
        answer:
          "Spreadsheets typically show one outcome. Monte Carlo simulation shows the range of possible outcomes (P10/P50/P90) and the probability of hitting key targets, while explainability tells you which variables are driving the risk.",
      },
      {
        question: "Why do confidence intervals matter?",
        answer:
          "Confidence intervals make risk measurable. Instead of hoping your single-point forecast is right, you can quantify the probability of different outcomes and make decisions with clearer tradeoffs. Investors and board members understand probability — gut feelings, not so much.",
      },
      {
        question: "How many simulations can I run?",
        answer:
          "Each Monte Carlo simulation runs 100 to 10,000 iterations depending on your settings. You can create unlimited scenarios during the beta period, compare them side by side, and version your work over time.",
      },
    ],
  },
  {
    title: "Data & Security",
    items: [
      {
        question: "How is my financial data protected?",
        answer:
          "All data is encrypted using AES-256 at rest and TLS in transit. Integrations use OAuth2 with read-only access where possible. Credentials are stored with envelope encryption. We never sell or share your data with third parties.",
      },
      {
        question: "Where is my data stored?",
        answer:
          "Your data is stored in US-based PostgreSQL databases with automated daily backups and point-in-time recovery. Infrastructure is hosted on secure, SOC2-compliant cloud providers with strict access controls and audit logging.",
      },
      {
        question: "What compliance standards do you follow?",
        answer:
          "We are fully GDPR compliant and are actively working toward SOC2 Type II certification. We conduct regular security audits, enforce role-based access controls, and maintain detailed audit logs of all data access. You can request a full data export or deletion at any time.",
      },
    ],
  },
  {
    title: "Pricing & Plans",
    items: [
      {
        question: "Is FounderConsole really free during beta?",
        answer:
          "Yes. All features are unlocked during the public beta at no cost. No credit card required. We'll announce pricing tiers well in advance before the beta ends, and early users will receive preferred rates.",
      },
      {
        question: "What will pricing look like after beta?",
        answer:
          "We plan to offer a free tier for basic forecasting, a Startup tier ($49/month) for unlimited scenarios and investor reporting, and a Growth tier ($129/month) for teams with advanced features. Beta users will be grandfathered at preferred rates.",
      },
      {
        question: "Do you offer enterprise pricing?",
        answer:
          "Yes — if you need custom integrations, dedicated support, or team-level access controls, contact us to discuss enterprise options.",
      },
    ],
  },
];

const allFaqItems = faqSections.flatMap((s) => s.items);

export default function FAQPage() {
  useSEO({
    title: "FAQ | FounderConsole",
    description: "FounderConsole FAQ: product, data, pricing, accuracy, and explainability.",
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "FAQPage",
      mainEntity: allFaqItems.map((item) => ({
        "@type": "Question",
        name: item.question,
        acceptedAnswer: {
          "@type": "Answer",
          text: item.answer,
        },
      })),
    },
  });

  return (
    <MarketingLayout>
      <section>
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-faq-title">
            Frequently Asked Questions
          </h1>
          <p className="mt-3 max-w-2xl text-lg text-muted-foreground">
            Clear answers, organized by what founders actually ask.
          </p>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-3xl px-4 py-10">
          {faqSections.map((section) => (
            <div key={section.title} className="mb-10">
              <h2 className="mb-4 text-lg font-semibold text-foreground" data-testid={`text-faq-section-${section.title.toLowerCase().replace(/\s+/g, "-")}`}>
                {section.title}
              </h2>
              <Accordion type="single" collapsible className="space-y-2">
                {section.items.map((item, i) => (
                  <AccordionItem
                    key={item.question}
                    value={`${section.title}-${i}`}
                    className="rounded-lg border bg-card px-4"
                    data-testid={`accordion-faq-${section.title.toLowerCase().replace(/\s+/g, "-")}-${i}`}
                  >
                    <AccordionTrigger className="text-sm font-medium text-foreground hover:no-underline">
                      {item.question}
                    </AccordionTrigger>
                    <AccordionContent className="text-sm text-muted-foreground">
                      {item.answer}
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </div>
          ))}

          <div className="rounded-xl border bg-card/50 p-6 text-center">
            <h3 className="text-base font-semibold text-foreground" data-testid="text-faq-still-questions">
              Still have questions?
            </h3>
            <p className="mt-2 text-sm text-muted-foreground">
              We're happy to help. Reach out and we'll get back to you within 24 hours.
            </p>
            <div className="mt-4">
              <Button asChild data-testid="button-faq-contact">
                <Link href="/contact">Contact Us</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
