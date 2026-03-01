import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Link } from "wouter";

const faqCategories = [
  {
    title: "Getting Started",
    questions: [
      {
        q: "How do I sign up for FounderConsole?",
        a: "Signing up is free during our beta period. Click \"Get Started Free\" on any page, create an account with your email, and you'll be guided through a quick onboarding flow to connect your first data source or explore with sample data.",
      },
      {
        q: "What data do I need to get started?",
        a: "You can start with as little as a spreadsheet upload (CSV or Excel) containing your monthly revenue, expenses, and cash balance. For richer insights, connect integrations like QuickBooks, Stripe, or Mercury to auto-sync your financial data.",
      },
      {
        q: "What should I do first after creating my account?",
        a: "We recommend starting with a Truth Scan to validate your data quality, then running your first Monte Carlo simulation to see your probabilistic runway. The AI Copilot can guide you through each step and explain what the results mean for your business.",
      },
      {
        q: "Can I try FounderConsole with sample data before connecting my own?",
        a: "Yes. During onboarding, you can choose to explore with a pre-loaded sample company (AstroTalk) that demonstrates all features including simulations, Truth Scan, and the AI Copilot. Switch to your own data whenever you're ready.",
      },
    ],
  },
  {
    title: "Simulation Engine",
    questions: [
      {
        q: "What is a Monte Carlo simulation and why should I care?",
        a: "A Monte Carlo simulation runs thousands of possible future scenarios by varying your key business drivers (revenue growth, churn, burn rate, etc.) within realistic ranges. Instead of a single forecast that's almost certainly wrong, you get a probability distribution showing P10 (pessimistic), P50 (base case), and P90 (optimistic) outcomes. This helps you make decisions with eyes wide open.",
      },
      {
        q: "How accurate are the simulation results?",
        a: "Simulations are only as good as the assumptions and data fed into them. FounderConsole uses your actual historical data, industry benchmarks, and calibrated growth models to set realistic parameter ranges. Our Truth Scan validates data quality before simulations run. The goal isn't to predict the future — it's to understand the range of possible outcomes so you can plan accordingly.",
      },
      {
        q: "Can I compare multiple scenarios side by side?",
        a: "Absolutely. You can create unlimited custom scenarios (e.g., \"Aggressive Hiring\" vs. \"Capital Efficient\" vs. \"Raise Now\") and compare them across key metrics like runway, revenue, burn rate, and cash balance. The comparison view highlights trade-offs and helps you see which levers matter most through sensitivity analysis.",
      },
    ],
  },
  {
    title: "Data & Security",
    questions: [
      {
        q: "How is my financial data stored and protected?",
        a: "All data is encrypted at rest (AES-256) and in transit (TLS 1.3). We use credential encryption for all integration tokens and API keys. Your data is never shared with other customers, and our infrastructure is hosted on secure, SOC 2-aligned cloud providers.",
      },
      {
        q: "Is FounderConsole GDPR compliant?",
        a: "Yes. We follow GDPR principles including data minimization, purpose limitation, and right to deletion. You can export or delete all your data at any time. We also implement PII redaction in our AI Copilot interactions to ensure sensitive information is never sent to third-party LLM providers unnecessarily.",
      },
      {
        q: "Which third-party services does FounderConsole use for AI?",
        a: "Our AI Copilot routes queries to the most appropriate model — GPT-4, Claude, or Gemini — depending on the task. Financial calculations stay on our servers. We use Perplexity for real-time market research when you ask about competitors, market sizing, or industry benchmarks. All AI interactions are logged and auditable.",
      },
    ],
  },
  {
    title: "Pricing & Plans",
    questions: [
      {
        q: "Is FounderConsole really free during beta?",
        a: "Yes. During our beta period, all features are available at no cost. We believe founders should be able to evaluate the platform fully before committing. We'll announce pricing plans well in advance of any changes, and early beta users will receive preferential pricing.",
      },
      {
        q: "What will pricing look like after beta?",
        a: "We're designing tiered plans based on company stage and usage. Expect a free tier for very early-stage startups, a growth plan for seed-to-Series A companies, and an enterprise plan for larger organizations. Simulation runs, number of connected integrations, and AI Copilot usage will be the primary scaling factors.",
      },
      {
        q: "Do you offer enterprise or custom plans?",
        a: "Yes. If you need custom integrations, dedicated support, SSO, audit logs, or volume pricing for a portfolio of companies (great for VCs and accelerators), reach out to us at hello@founderconsole.ai and we'll put together a tailored plan.",
      },
    ],
  },
];

export default function FAQPage() {
  return (
    <MarketingLayout>
      <section className="py-16 md:py-24" data-testid="section-faq-hero">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4" data-testid="text-faq-title">
            Frequently Asked Questions
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto" data-testid="text-faq-subtitle">
            Everything you need to know about FounderConsole. Can't find what you're looking for? Reach out to our team.
          </p>
        </div>
      </section>

      <section className="pb-16 md:pb-24" data-testid="section-faq-content">
        <div className="max-w-3xl mx-auto px-4">
          {faqCategories.map((category, catIdx) => (
            <div key={category.title} className="mb-10" data-testid={`section-faq-category-${catIdx}`}>
              <h2 className="text-xl font-semibold mb-4" data-testid={`text-faq-category-${catIdx}`}>
                {category.title}
              </h2>
              <Accordion type="single" collapsible className="w-full">
                {category.questions.map((item, qIdx) => (
                  <AccordionItem key={qIdx} value={`${catIdx}-${qIdx}`} data-testid={`accordion-faq-${catIdx}-${qIdx}`}>
                    <AccordionTrigger className="text-left" data-testid={`button-faq-${catIdx}-${qIdx}`}>
                      {item.q}
                    </AccordionTrigger>
                    <AccordionContent data-testid={`text-faq-answer-${catIdx}-${qIdx}`}>
                      <p className="text-muted-foreground leading-relaxed">{item.a}</p>
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </div>
          ))}
        </div>
      </section>

      <section className="pb-16 md:pb-24" data-testid="section-faq-cta">
        <div className="max-w-3xl mx-auto px-4 text-center">
          <h2 className="text-2xl font-bold mb-3" data-testid="text-faq-cta-title">
            Still have questions?
          </h2>
          <p className="text-muted-foreground mb-6">
            Our team is happy to help. Reach out and we'll get back to you within 24 hours.
          </p>
          <Link href="/contact">
            <Button data-testid="button-faq-contact">Get in Touch</Button>
          </Link>
        </div>
      </section>
    </MarketingLayout>
  );
}
