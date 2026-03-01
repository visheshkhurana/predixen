import { Shield, Mail, Database, Eye, Cookie, Clock, Users, ExternalLink } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Link } from 'wouter';

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

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-3xl mx-auto px-4 py-12 md:py-16 space-y-6">
        <div className="space-y-2 text-center mb-8" data-testid="privacy-header">
          <h1 className="text-3xl font-bold tracking-tight">Privacy Policy</h1>
          <p className="text-muted-foreground">Last updated: January 2026</p>
        </div>

        <p className="text-sm text-muted-foreground leading-relaxed">
          FounderConsole ("we", "our", "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, store, and protect your information when you use our platform.
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

        <Section icon={Database} title="How We Use Your Data" testId="section-data-use">
          <p>Your data is used to:</p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li>Provide financial dashboards, simulations, and AI-powered insights.</li>
            <li>Run Monte Carlo simulations and scenario modeling on your financial data.</li>
            <li>Generate recommendations and risk assessments through our AI copilot.</li>
            <li>Send transactional emails (verification, password reset, alerts).</li>
            <li>Improve the platform based on aggregate, anonymized usage patterns.</li>
          </ul>
          <p>We never sell your data to third parties. Your financial data is only used to provide services directly to you.</p>
        </Section>

        <Section icon={ExternalLink} title="Third-Party Services" testId="section-third-party">
          <p>We use the following third-party services:</p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li><strong className="text-foreground">PostHog:</strong> Product analytics to understand feature usage (anonymized).</li>
            <li><strong className="text-foreground">Google OAuth:</strong> Social login authentication.</li>
            <li><strong className="text-foreground">QuickBooks Online:</strong> Sync accounting data (P&L, balance sheet, invoices) when you connect your account.</li>
            <li><strong className="text-foreground">Stripe:</strong> Sync payment and revenue data when you connect your account.</li>
            <li><strong className="text-foreground">Gusto:</strong> Sync payroll data when you connect your account.</li>
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

        <Section icon={Cookie} title="Cookies" testId="section-cookies">
          <p>We use the following cookies:</p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li><strong className="text-foreground">Session Cookies:</strong> Essential for authentication and CSRF protection.</li>
            <li><strong className="text-foreground">PostHog Analytics:</strong> Anonymous usage tracking to improve the platform. Can be blocked without affecting functionality.</li>
          </ul>
        </Section>

        <Section icon={Mail} title="Contact" testId="section-contact">
          <p>If you have questions about this Privacy Policy or wish to exercise your data rights, contact us at:</p>
          <p className="font-medium text-foreground">
            <a href="mailto:vk@founderconsole.com" className="text-indigo-400 hover:underline" data-testid="link-contact-email">
              vk@founderconsole.com
            </a>
          </p>
        </Section>

        <div className="text-center pt-4 text-xs text-muted-foreground">
          <Link href="/terms" className="text-indigo-400 hover:underline" data-testid="link-terms">Terms of Service</Link>
          <span className="mx-2">·</span>
          <Link href="/" className="text-indigo-400 hover:underline" data-testid="link-home">Back to FounderConsole</Link>
        </div>
      </div>
    </div>
  );
}