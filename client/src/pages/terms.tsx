import { FileText, AlertTriangle, Scale, Ban, ShieldCheck, UserX, Gavel, Mail, UserCheck, Database, Bell } from 'lucide-react';
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

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-3xl mx-auto px-4 py-12 md:py-16 space-y-6">
        <div className="space-y-2 text-center mb-8" data-testid="terms-header">
          <h1 className="text-3xl font-bold tracking-tight">Terms of Service</h1>
          <p className="text-muted-foreground">Last updated: January 2026</p>
        </div>

        <p className="text-sm text-muted-foreground leading-relaxed">
          These Terms of Service ("Terms") govern your use of FounderConsole ("the Service"), operated by FounderConsole ("we", "our", "us"). By accessing or using the Service, you agree to be bound by these Terms.
        </p>

        <Section icon={FileText} title="Service Description" testId="section-service">
          <p>FounderConsole is an AI-powered financial intelligence platform for startups. The Service provides:</p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li>Financial dashboards and KPI tracking.</li>
            <li>Monte Carlo simulations and scenario modeling.</li>
            <li>AI-powered copilot for financial analysis and recommendations.</li>
            <li>Data integrations with accounting, payroll, and payment platforms.</li>
            <li>Cap table management and fundraising tools.</li>
          </ul>
        </Section>

        <Section icon={AlertTriangle} title="Beta Disclaimer" testId="section-beta">
          <p>The Service is currently in <strong className="text-foreground">beta</strong>. This means:</p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li>All features are provided free of charge during the beta period.</li>
            <li>The Service may contain bugs, errors, or incomplete functionality.</li>
            <li>Features may be added, modified, or removed without prior notice.</li>
            <li>Data loss, while unlikely, is possible. We recommend maintaining your own backups.</li>
            <li>AI-generated insights are informational only and should not be the sole basis for financial decisions.</li>
            <li>We reserve the right to introduce pricing after the beta period with reasonable notice.</li>
          </ul>
        </Section>

        <Section icon={UserCheck} title="Account Terms" testId="section-account-terms">
          <ul className="list-disc pl-5 space-y-1.5">
            <li>You must be at least <strong className="text-foreground">18 years of age</strong> to use the Service.</li>
            <li>You are responsible for maintaining the confidentiality of your login credentials.</li>
            <li>You are responsible for all activity that occurs under your account.</li>
            <li>You must provide accurate and complete information when creating your account.</li>
            <li>You must notify us immediately of any unauthorized use of your account.</li>
            <li>One person or legal entity may not maintain more than one account.</li>
          </ul>
        </Section>

        <Section icon={ShieldCheck} title="Acceptable Use" testId="section-acceptable-use">
          <p>You agree to:</p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li>Provide accurate information when creating your account.</li>
            <li>Keep your login credentials secure and confidential.</li>
            <li>Use the Service only for lawful business purposes.</li>
            <li>Not attempt to reverse-engineer, decompile, or exploit the Service.</li>
            <li>Not upload malicious content, malware, or automated scripts.</li>
            <li>Not use the Service to store or process data you do not have the right to use.</li>
            <li>Not share your account with unauthorized users.</li>
          </ul>
        </Section>

        <Section icon={Ban} title="Limitation of Liability" testId="section-liability">
          <p>To the maximum extent permitted by law:</p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li>The Service is provided <strong className="text-foreground">"as is"</strong> and <strong className="text-foreground">"as available"</strong> without warranties of any kind.</li>
            <li>We do not guarantee the accuracy, completeness, or reliability of AI-generated insights, simulations, or recommendations.</li>
            <li>We are not liable for any direct, indirect, incidental, or consequential damages arising from your use of the Service.</li>
            <li>Our total liability is limited to the amount you paid for the Service in the 12 months preceding the claim (during beta: $0).</li>
            <li>You are solely responsible for financial decisions made based on information from the Service.</li>
          </ul>
        </Section>

        <Section icon={Database} title="Data Rights" testId="section-data-rights">
          <ul className="list-disc pl-5 space-y-1.5">
            <li><strong className="text-foreground">Your Data:</strong> You retain full ownership of all data you upload to the Service, including financial records, documents, and company information.</li>
            <li><strong className="text-foreground">Our License:</strong> By using the Service, you grant us a limited license to process, store, and analyze your data solely to provide the Service to you.</li>
            <li>We will not sell, rent, or share your data with third parties except as described in our <a href="/privacy" className="text-indigo-400 hover:underline">Privacy Policy</a>.</li>
            <li>You may export your data at any time using the built-in export features.</li>
            <li>We may use anonymized, aggregate data to improve the Service.</li>
          </ul>
        </Section>

        <Section icon={Scale} title="Intellectual Property" testId="section-ip">
          <ul className="list-disc pl-5 space-y-1.5">
            <li><strong className="text-foreground">Our IP:</strong> The Service, including its design, code, algorithms, and AI models, is owned by FounderConsole. You may not copy, modify, or distribute any part of the Service.</li>
            <li><strong className="text-foreground">Your Data:</strong> You retain full ownership of all financial data, documents, and content you upload to the Service. We claim no ownership over your data.</li>
            <li>We may use anonymized, aggregate data to improve the Service.</li>
          </ul>
        </Section>

        <Section icon={UserX} title="Termination" testId="section-termination">
          <ul className="list-disc pl-5 space-y-1.5">
            <li>You may delete your account at any time by contacting us.</li>
            <li>We may suspend or terminate your account if you violate these Terms.</li>
            <li>Upon termination, you may request an export of your data within 30 days.</li>
            <li>After 30 days, your data will be permanently deleted.</li>
            <li>Provisions regarding liability, intellectual property, and governing law survive termination.</li>
          </ul>
        </Section>

        <Section icon={Bell} title="Changes to Terms" testId="section-changes">
          <ul className="list-disc pl-5 space-y-1.5">
            <li>We may update these Terms from time to time to reflect changes in the Service or legal requirements.</li>
            <li>We will notify you of material changes by email at least 30 days before they take effect.</li>
            <li>Continued use of the Service after changes take effect constitutes acceptance of the updated Terms.</li>
            <li>If you do not agree to the updated Terms, you may terminate your account before they take effect.</li>
          </ul>
        </Section>

        <Section icon={Gavel} title="Governing Law" testId="section-governing-law">
          <p>These Terms are governed by and construed in accordance with the laws of the State of California, United States, without regard to conflict of law principles. Any disputes arising from these Terms shall be resolved in the state or federal courts located in San Francisco County, California.</p>
        </Section>

        <Section icon={Mail} title="Contact" testId="section-terms-contact">
          <p>For questions about these Terms, contact us at:</p>
          <p className="font-medium text-foreground">
            <a href="mailto:vk@founderconsole.com" className="text-indigo-400 hover:underline" data-testid="link-terms-contact-email">
              vk@founderconsole.com
            </a>
          </p>
        </Section>

        <div className="text-center pt-4 text-xs text-muted-foreground">
          <Link href="/privacy" className="text-indigo-400 hover:underline" data-testid="link-privacy">Privacy Policy</Link>
          <span className="mx-2">·</span>
          <Link href="/" className="text-indigo-400 hover:underline" data-testid="link-home">Back to FounderConsole</Link>
        </div>
      </div>
    </div>
  );
}