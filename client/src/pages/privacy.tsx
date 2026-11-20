import { Shield, Mail, Database, Eye, Cookie, Clock, Users, ExternalLink, Scale, Building2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Link } from 'wouter';
import { useSEO } from '@/lib/seo';
import { LegalEntityNotice, GrievanceOfficerText } from '@/components/marketing/LegalEntity';
import { LEGAL_ENTITY_NAME, PRODUCT_OF_LINE } from '@/data/legal';

function Section({ icon: Icon, title, children, testId, id }: {
  icon: any; title: string; children: React.ReactNode; testId: string; id?: string;
}) {
  return (
    <Card data-testid={testId} id={id} className="scroll-mt-6">
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

export default function PrivacyPolicyPage() {
  useSEO({
    title: "Privacy Policy | FounderConsole",
    description: "How FounderConsole collects, uses, stores, and protects your information. Read-only integrations, encrypted data, no resale.",
    path: "/privacy",
    robots: "noindex, follow",
  });

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-3xl mx-auto px-4 py-12 md:py-16 space-y-6">
        <div className="space-y-2 text-center mb-8" data-testid="privacy-header">
          <h1 className="text-3xl font-bold tracking-tight">Privacy Policy</h1>
          <p className="text-muted-foreground">Last updated: November 2026</p>
        </div>

        <p className="text-sm text-muted-foreground leading-relaxed">
          FounderConsole ("we", "our", "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, store, and protect your information when you use our platform. {PRODUCT_OF_LINE} {LEGAL_ENTITY_NAME} is responsible for your information under this policy.
        </p>

        <Section icon={Eye} title="Information We Collect" testId="section-info-collect">
          <p>We collect the following types of information:</p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li><strong className="text-foreground">Account Information:</strong> Your email address, name, and password when you register.</li>
            <li><strong className="text-foreground">Company Financial Data:</strong> Revenue, expenses, cash balances, invoices, and other financial metrics you enter manually or sync through connected integrations (QuickBooks, Stripe, Gusto).</li>
            <li><strong className="text-foreground">Usage Data:</strong> Pages visited, features used, simulation runs, and interaction patterns to improve the platform.</li>
            <li><strong className="text-foreground">Authentication Data:</strong> OAuth tokens when you sign in via Google.</li>
          </ul>
        </Section>

        <Section icon={Building2} title="Advertising Account Data (Meta Ads, Google Ads)" testId="section-ad-platform-data" id="ad-platform-data">
          <p>If you choose to connect Meta Ads (Facebook and Instagram) or Google Ads, you sign in with that platform and grant FounderConsole <strong className="text-foreground">read-only</strong> access to your ad accounts (on Meta, the <code>ads_read</code> permission). We never create, edit, pause or spend on your ads.</p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li><strong className="text-foreground">What we read:</strong> the names, IDs and currency of the ad accounts you can access, and monthly totals per account: spend, impressions, clicks, and the purchases and purchase value the platform attributes to its ads.</li>
            <li><strong className="text-foreground">What we do with it:</strong> show your marketing spend, CM3, MER and platform-reported ROAS on your own dashboard, and use it in your own forecasts and simulations. It is visible only to members of your company workspace.</li>
            <li><strong className="text-foreground">What we never do:</strong> sell it, share it with other customers or advertisers, use it to target ads, or combine it with data from other FounderConsole customers.</li>
            <li><strong className="text-foreground">Storage:</strong> the access token is stored encrypted; the monthly totals are stored with your company's financial data. Neither is sent to AI providers except as part of the analysis you ask for in your own workspace.</li>
          </ul>
        </Section>

        <Section icon={Shield} title="Google User Data" testId="section-google-user-data" id="google-user-data">
          <p>When you choose to connect a Google product, you sign in with Google and approve only the read-only access that feature needs:</p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li><strong className="text-foreground">Google Ads</strong> (<code>https://www.googleapis.com/auth/adwords</code>): we read the names, IDs and currency of the ad accounts you can access and monthly totals per account (spend, impressions, clicks, conversions and conversion value). We never create, edit, pause or spend on campaigns, even though Google offers this permission only as a single scope.</li>
            <li><strong className="text-foreground">Google Analytics</strong> (<code>https://www.googleapis.com/auth/analytics.readonly</code>): we read monthly traffic and conversion totals for the GA4 property you connect.</li>
            <li><strong className="text-foreground">Google Sign-In:</strong> your name, email address and profile picture, to create and sign in to your account.</li>
          </ul>
          <p>We use this data only to show it on your own dashboard and in the forecasts, simulations and analysis you ask for in your workspace. It is visible only to members of your company workspace. We store the refresh token encrypted and delete it, together with the data it imported, when you click Disconnect or delete your account.</p>
          <p>
            <strong className="text-foreground">FounderConsole's use and transfer to any other app of information received from Google APIs will adhere to the{' '}
            <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:underline">Google API Services User Data Policy</a>, including the Limited Use requirements.</strong>
          </p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li>We do not sell Google user data, and we do not use or transfer it for advertising, retargeting, credit-worthiness or lending decisions.</li>
            <li>We do not transfer it to others except as needed to provide the features you use (for example, sending figures to an AI provider to answer a question you asked in your workspace), to comply with law, or as part of a merger or acquisition with your notice.</li>
            <li>We do not use Google user data to develop, improve or train generalized or non-personalized AI or machine-learning models, and our AI providers do not retain it beyond the request.</li>
            <li>No person at FounderConsole reads it unless you ask us to for support, it is needed for security or to comply with law, or it is aggregated and anonymized for internal operations.</li>
          </ul>
        </Section>

        <Section icon={Database} title="How We Use Your Data" testId="section-data-use">
          <p>Your data is used to:</p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li>Provide financial dashboards, simulations, and AI-powered insights.</li>
            <li>Run Monte Carlo simulations and scenario modeling on your financial data.</li>
            <li>Generate recommendations and risk assessments through our AI copilot.</li>
            <li>Send transactional emails (verification, password reset, alerts).</li>
            <li>Improve the platform based on aggregate, anonymized usage patterns (data received from Google APIs is only ever used here in aggregated, anonymized form; see Google User Data above).</li>
          </ul>
          <p>We never sell your data to third parties. Your financial data is only used to provide services directly to you.</p>
        </Section>

        <Section icon={ExternalLink} title="Third-Party Services" testId="section-third-party">
          <p>We use the following third-party services:</p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li><strong className="text-foreground">Google Analytics:</strong> Website traffic measurement and visitor behavior analysis. Google may use cookies and collect IP addresses, browser type, pages visited, and session duration. Data is processed by Google LLC under their <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:underline">Privacy Policy</a>.</li>
            <li><strong className="text-foreground">Meta (Facebook) Pixel:</strong> Conversion tracking and audience measurement on our marketing pages. Meta may collect page visit data, browser information, and IP addresses. Data is processed by Meta Platforms, Inc. under their <a href="https://www.facebook.com/privacy/policy/" target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:underline">Privacy Policy</a>. You can opt out via <a href="https://www.facebook.com/settings?tab=ads" target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:underline">Facebook Ad Settings</a>.</li>
            <li><strong className="text-foreground">PostHog:</strong> Product analytics to understand feature usage (anonymized).</li>
            <li><strong className="text-foreground">Google OAuth:</strong> Social login authentication.</li>
            <li><strong className="text-foreground">QuickBooks Online:</strong> Sync accounting data (P&L, balance sheet, invoices) when you connect your account.</li>
            <li><strong className="text-foreground">Stripe:</strong> Sync payment and revenue data when you connect your account.</li>
            <li><strong className="text-foreground">Razorpay:</strong> Subscription payment processing. We do not store your full card or bank details; Razorpay handles them under its own privacy policy.</li>
            <li><strong className="text-foreground">Gusto:</strong> Sync payroll data when you connect your account.</li>
            <li><strong className="text-foreground">Meta Ads and Google Ads:</strong> Read-only ad spend and performance when you connect your ad accounts. See Advertising Account Data above.</li>
            <li><strong className="text-foreground">Resend:</strong> Transactional email delivery.</li>
            <li><strong className="text-foreground">OpenAI, Anthropic, Google Gemini:</strong> AI model providers for copilot and analysis features. Financial data may be sent to these providers to generate insights; data is not retained by them beyond the request.</li>
          </ul>
        </Section>

        <Section icon={Shield} title="Data Storage & Security" testId="section-storage">
          <p>Your data is stored in an encrypted PostgreSQL database. We implement the following security measures:</p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li>Passwords are hashed using bcrypt before storage.</li>
            <li>All connections use HTTPS/TLS encryption in transit.</li>
            <li>Integration credentials (OAuth tokens) are stored encrypted.</li>
            <li>JWT-based authentication with httpOnly cookies.</li>
            <li>CSRF protection on all state-changing requests.</li>
            <li>Rate limiting on authentication and simulation endpoints.</li>
          </ul>
        </Section>

        <Section icon={Clock} title="Data Retention" testId="section-retention">
          <p>We retain your data for as long as your account is active. Specifically:</p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li>Account data is retained until you request deletion.</li>
            <li>Financial data and simulation results are retained while your account is active.</li>
            <li>Analytics data is retained in anonymized form for up to 24 months.</li>
            <li>Upon account deletion, all personally identifiable data is permanently removed within 30 days.</li>
          </ul>
        </Section>

        <Section icon={Users} title="Your Rights" testId="section-rights">
          <p>You have the right to:</p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li><strong className="text-foreground">Access:</strong> Request a copy of all data we hold about you.</li>
            <li><strong className="text-foreground">Correct:</strong> Update or correct inaccurate data.</li>
            <li><strong className="text-foreground">Delete:</strong> Request permanent deletion of your account and all associated data.</li>
            <li><strong className="text-foreground">Export:</strong> Download your financial data in standard formats (CSV, PDF).</li>
            <li><strong className="text-foreground">Withdraw Consent:</strong> Disconnect integrations or opt out of analytics at any time.</li>
          </ul>
          <p>To exercise any of these rights, contact us at the email below.</p>
        </Section>

        <Section icon={Database} title="Deleting Your Data" testId="section-data-deletion" id="data-deletion">
          <p>You can delete data FounderConsole received from a connected platform at any time:</p>
          <ol className="list-decimal pl-5 space-y-1.5">
            <li><strong className="text-foreground">Disconnect the integration:</strong> go to Integrations in FounderConsole and click <em>Disconnect</em> on the Meta Ads or Google Ads card. This immediately deletes the stored access token and every ad spend record that integration imported.</li>
            <li><strong className="text-foreground">Remove our access on the platform:</strong> on Facebook, open Settings &amp; privacy, then Business Integrations, and remove FounderConsole; on Google, remove FounderConsole at myaccount.google.com/permissions.</li>
            <li><strong className="text-foreground">Delete everything:</strong> email <a href="mailto:hello@founderconsole.ai" className="text-indigo-400 hover:underline">hello@founderconsole.ai</a> from your account email asking for deletion. We delete your account and all associated data, including data from Meta and Google, within 30 days and confirm by email.</li>
          </ol>
        </Section>

        <Section icon={Cookie} title="Cookies" testId="section-cookies">
          <p>We use the following cookies:</p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li><strong className="text-foreground">Session Cookies:</strong> Essential for authentication and CSRF protection.</li>
            <li><strong className="text-foreground">Google Analytics (_ga, _gid):</strong> Traffic measurement and visitor behavior analysis. Retained for up to 2 years. Can be blocked without affecting functionality.</li>
            <li><strong className="text-foreground">Meta Pixel (_fbp):</strong> Conversion tracking on marketing pages. Retained for up to 90 days. Active on public marketing pages and the subscription checkout confirmation, not elsewhere inside the app. Can be blocked without affecting functionality.</li>
            <li><strong className="text-foreground">PostHog Analytics:</strong> Anonymous usage tracking to improve the platform. Can be blocked without affecting functionality.</li>
          </ul>
        </Section>

        <Section icon={Mail} title="Contact" testId="section-contact">
          <p>If you have questions about this Privacy Policy or wish to exercise your data rights, contact us at:</p>
          <p className="font-medium text-foreground">
            <a href="mailto:hello@founderconsole.ai" className="text-indigo-400 hover:underline" data-testid="link-contact-email">
              hello@founderconsole.ai
            </a>
          </p>
        </Section>

        <Section icon={Scale} title="Grievance Officer" testId="section-grievance">
          <GrievanceOfficerText />
        </Section>

        <Section icon={Building2} title="Company" testId="section-privacy-company">
          <LegalEntityNotice className="space-y-1" showEmail={false} />
        </Section>

        <div className="text-center pt-4 text-xs text-muted-foreground">
          <Link href="/terms" className="text-indigo-400 hover:underline" data-testid="link-terms">Terms of Service</Link>
          <span className="mx-2">·</span>
          <Link href="/refund-policy" className="text-indigo-400 hover:underline" data-testid="link-refund-policy">Refund &amp; Cancellation Policy</Link>
          <span className="mx-2">·</span>
          <Link href="/" className="text-indigo-400 hover:underline" data-testid="link-home">Back to FounderConsole</Link>
        </div>
      </div>
    </div>
  );
}