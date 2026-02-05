import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BookOpen, Mail, MessageCircle, ExternalLink } from 'lucide-react';

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="text-center space-y-4">
          <Badge variant="secondary" className="mb-2">Documentation</Badge>
          <h1 className="text-3xl font-bold">Help & Documentation</h1>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            We're building comprehensive documentation to help you get the most out of Predixen.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <Card data-testid="card-getting-started">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-primary" />
                Getting Started
              </CardTitle>
              <CardDescription>
                Learn the basics of Predixen
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2 text-sm text-muted-foreground">
                <p><strong>1. Company Setup</strong> - Enter your company info and connect data sources</p>
                <p><strong>2. Financial Baseline</strong> - Input your current financials (revenue, expenses, cash)</p>
                <p><strong>3. Truth Scan</strong> - Get AI-powered insights on your financial health</p>
                <p><strong>4. Simulations</strong> - Run Monte Carlo simulations for strategic planning</p>
              </div>
              <Badge variant="outline">Guide coming soon</Badge>
            </CardContent>
          </Card>

          <Card data-testid="card-simulation-guide">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageCircle className="h-5 w-5 text-primary" />
                Simulation Engine
              </CardTitle>
              <CardDescription>
                Understanding Monte Carlo simulations
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2 text-sm text-muted-foreground">
                <p><strong>What is Monte Carlo?</strong> - Run thousands of scenarios to understand probability distributions</p>
                <p><strong>P10/P50/P90</strong> - Percentiles representing pessimistic, median, and optimistic outcomes</p>
                <p><strong>Runway Projections</strong> - How long your cash will last under various scenarios</p>
              </div>
              <Badge variant="outline">Guide coming soon</Badge>
            </CardContent>
          </Card>
        </div>

        <Card data-testid="card-contact-support">
          <CardHeader>
            <CardTitle>Need Help?</CardTitle>
            <CardDescription>
              Our team is here to support you
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-4">
            <Button variant="outline" asChild data-testid="button-email-support">
              <a href="mailto:support@predixen.app">
                <Mail className="h-4 w-4 mr-2" />
                Email Support
              </a>
            </Button>
            <Button variant="outline" disabled data-testid="button-live-chat">
              <MessageCircle className="h-4 w-4 mr-2" />
              Live Chat
              <Badge variant="secondary" className="ml-2 text-[10px]">Coming Soon</Badge>
            </Button>
          </CardContent>
        </Card>

        <div className="text-center text-sm text-muted-foreground">
          <p>Full documentation launching soon. Check back for comprehensive guides, API references, and tutorials.</p>
        </div>
      </div>
    </div>
  );
}
