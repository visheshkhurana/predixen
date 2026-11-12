import { CreditCard, XCircle, RotateCcw, Clock, Mail, Building2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Link } from "wouter";
import { useSEO } from "@/lib/seo";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { LegalEntityNotice } from "@/components/marketing/LegalEntity";
import {
  LEGAL_ENTITY_NAME,
  PRODUCT_OF_LINE,
  SUPPORT_EMAIL,
  FIRST_PAYMENT_REFUND_WINDOW_DAYS,
  REFUND_PROCESSING_TIME,
} from "@/data/legal";
import { STARTER_PRICES, ANNUAL_LABEL } from "@/data/public-pricing";

// The prerendered copy of this page is buildRefundPolicyBodyContent() in
// server/seo-prerender.ts. Both read client/src/data/legal.ts and
// shared/pricing.json, so the numbers cannot disagree.

function Section({ icon: Icon, title, children, testId }: {
  icon: any; title: string; children: React.ReactNode; testId: string;
}) {
  return (
    <Card data-testid={testId}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon className="h-5 w-5 text-indigo-400" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm leading-relaxed text-muted-foreground">
        {children}
      </CardContent>
    </Card>
  );
}

export default function RefundPolicyPage() {
  const days = FIRST_PAYMENT_REFUND_WINDOW_DAYS;
  const p = STARTER_PRICES;

  useSEO({
    title: "Refund & Cancellation Policy | FounderConsole",
    description: `How cancellations and refunds work for FounderConsole subscriptions billed through Razorpay. Cancel anytime; refunds within ${days} days of your first payment.`,
    path: "/refund-policy",
  });

  const mail = (
    <a href={`mailto:${SUPPORT_EMAIL}`} className="text-indigo-400 hover:underline" data-testid="link-refund-email">
      {SUPPORT_EMAIL}
    </a>
  );

  return (
    <MarketingLayout>
      <div className="max-w-3xl mx-auto px-4 py-12 md:py-16 space-y-6">
        <div className="space-y-2 text-center mb-8" data-testid="refund-header">
          <h1 className="text-3xl font-bold tracking-tight">Refund &amp; Cancellation Policy</h1>
          <p className="text-muted-foreground">Last updated: November 2026</p>
        </div>

        <p className="text-sm text-muted-foreground leading-relaxed">
          This policy explains how cancellations and refunds work for paid FounderConsole subscriptions. {PRODUCT_OF_LINE}{" "}
          In this policy, "we", "our" and "us" mean {LEGAL_ENTITY_NAME}.
        </p>

        <Section icon={CreditCard} title="Subscription plans and billing" testId="section-refund-billing">
          <p>
            FounderConsole is a software-as-a-service subscription. Paid plans are billed in advance through Razorpay,
            monthly or annually, and renew automatically at the end of each billing period until cancelled.
          </p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li>
              <strong className="text-foreground">Starter, monthly:</strong> {p.INR.monthlyLabel} / {p.USD.monthlyLabel} / {p.AED.monthlyLabel} per month
            </li>
            <li>
              <strong className="text-foreground">Starter, annual:</strong> {p.INR.annualLabel} / {p.USD.annualLabel} / {p.AED.annualLabel} per year ({ANNUAL_LABEL})
            </li>
          </ul>
          <p>
            Your charge currency follows the currency set for your company in FounderConsole: INR if it is INR, AED if
            it is AED, and USD otherwise. Current prices are always shown on{" "}
            <Link href="/pricing" className="text-indigo-400 hover:underline">pricing</Link>. The Free plan is never charged.
          </p>
        </Section>

        <Section icon={XCircle} title="Cancellation" testId="section-cancellation">
          <p>
            You can cancel anytime from <strong className="text-foreground">Billing</strong> in your FounderConsole account.
            Cancellation takes effect at the end of the current billing period: you keep paid access until then, and no
            further charges are made after you cancel. You can also cancel by writing to {mail} from your account email.
          </p>
        </Section>

        <Section icon={RotateCcw} title="Refunds" testId="section-refunds">
          <ul className="list-disc pl-5 space-y-1.5">
            <li>
              <strong className="text-foreground">No partial-period refunds.</strong> Fees already paid for the current
              billing period, monthly or annual, are not refunded when you cancel or downgrade, except as set out below.
            </li>
            <li>
              <strong className="text-foreground">First payment.</strong> If you are not satisfied, you can request a full
              refund within {days} days of the first payment of a new subscription. This applies once per customer, to the
              first payment only, not to renewals.
            </li>
            <li>
              <strong className="text-foreground">Duplicate or erroneous charges.</strong> If you were charged twice, or
              charged in error, we refund the incorrect charge in full.
            </li>
          </ul>
        </Section>

        <Section icon={Clock} title="How refunds are processed" testId="section-refund-processing">
          <p>
            Approved refunds are issued through Razorpay to the original payment method. The amount reaches your account
            within {REFUND_PROCESSING_TIME} of approval, depending on your bank or card issuer. We do not refund to a
            different card, account or wallet.
          </p>
        </Section>

        <Section icon={Mail} title="How to request a refund" testId="section-refund-request">
          <p>
            Email {mail} from the email address on your account, with the payment date and the Razorpay payment ID if you
            have it. We reply within 2 business days.
          </p>
        </Section>

        <Section icon={Building2} title="Contact" testId="section-refund-contact">
          <LegalEntityNotice className="space-y-1" />
        </Section>

        <div className="text-center pt-4 text-xs text-muted-foreground">
          <Link href="/terms" className="text-indigo-400 hover:underline" data-testid="link-terms">Terms of Service</Link>
          <span className="mx-2">·</span>
          <Link href="/privacy" className="text-indigo-400 hover:underline" data-testid="link-privacy">Privacy Policy</Link>
          <span className="mx-2">·</span>
          <Link href="/contact" className="text-indigo-400 hover:underline" data-testid="link-contact">Contact</Link>
        </div>
      </div>
    </MarketingLayout>
  );
}
