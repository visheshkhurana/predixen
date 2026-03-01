import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BookOpen, Mail, MessageCircle, BarChart3, Brain, Plug, ChevronDown, ChevronUp, Rocket, Target, TrendingUp, Zap, HelpCircle, ArrowRight } from 'lucide-react';

function Section({ icon: Icon, title, subtitle, badge, children, testId }: {
  icon: any; title: string; subtitle: string; badge?: string; children: React.ReactNode; testId: string;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card data-testid={testId}>
      <CardHeader className="cursor-pointer" onClick={() => setExpanded(!expanded)} data-testid={`${testId}-toggle`}>
        <div className="flex items-start justify-between">
          <div className="space-y-1.5">
            <CardTitle className="flex items-center gap-2">
              <Icon className="h-5 w-5 text-muted-foreground" />
              {title}
              {badge && <Badge variant="secondary" className="text-[10px] ml-1">{badge}</Badge>}
            </CardTitle>
            <CardDescription>{subtitle}</CardDescription>
          </div>
          <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0">
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </div>
      </CardHeader>
      {expanded && (
        <CardContent className="pt-0 space-y-6 text-sm leading-relaxed text-muted-foreground" data-testid={`${testId}-content`}>
          {children}
        </CardContent>
      )}
    </Card>
  );
}

function SubSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      {children}
    </div>
  );
}

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-background p-4 sm:p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="text-center space-y-3 mb-8">
          <Badge variant="secondary">Documentation</Badge>
          <h1 className="text-3xl font-bold" data-testid="text-docs-title">Help & Documentation</h1>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            Everything you need to get the most out of FounderConsole. Click any section below to expand it.
          </p>
        </div>

        <Section
          icon={BookOpen}
          title="Getting Started"
          subtitle="Set up your account, connect data, and run your first simulation"
          testId="card-getting-started"
        >
          <SubSection title="1. Set Up Your Company Profile">
            <p>
              After signing up, you'll be guided through a short onboarding wizard. Start by entering your company name and basic details. Then choose how you want to bring in your financial data: you can upload a CSV export from your accounting software, enter numbers manually, or connect a live data source like QuickBooks or Stripe. If you're just exploring, the manual entry option is the fastest way to get started — enter your current monthly revenue, monthly expenses, and cash on hand, and the platform will immediately calculate your runway and burn rate.
            </p>
          </SubSection>

          <SubSection title="2. Understand Your Dashboard">
            <p>
              Once your data is in, the dashboard becomes your financial command center. The top row shows your key health metrics: monthly burn rate, cash runway in months, revenue growth trend, and an overall financial health score. Each metric card is color-coded — green means healthy, amber means worth watching, and red signals something that needs attention. If you see "N/A" on any metric, it means the platform needs more data for that calculation. Hover over any metric for a tooltip explaining exactly what it measures and what data it needs.
            </p>
            <p>
              Below the metrics, you'll find your revenue and expense trends over time, anomaly alerts if the system detects unusual spending patterns, and quick-action buttons to run a new simulation or open the AI Copilot. The dashboard refreshes automatically when you update your data, so it always reflects your latest numbers.
            </p>
          </SubSection>

          <SubSection title="3. Run Your First Simulation">
            <p>
              Navigate to the Scenarios page from the sidebar. Click "New Scenario" and give it a name (for example, "What if we hire 3 engineers?"). Adjust the input parameters — you can model changes to revenue growth rate, pricing adjustments, new hires and their costs, burn reduction targets, or a fundraising round. Once your inputs look right, click "Run Simulation." The engine will run thousands of Monte Carlo iterations projecting your finances 24 months forward, then show you the results with P10 (pessimistic), P50 (median), and P90 (optimistic) outcomes, a runway projection, and an AI-generated recommendation on whether to proceed.
            </p>
          </SubSection>
        </Section>

        <Section
          icon={BarChart3}
          title="Simulation Engine"
          subtitle="How Monte Carlo simulations work and how to interpret the results"
          testId="card-simulation-guide"
        >
          <SubSection title="What Are Monte Carlo Simulations?">
            <p>
              Monte Carlo simulation is a technique that runs your financial scenario thousands of times, each time introducing small random variations to account for real-world uncertainty. Instead of giving you a single projected outcome (which is almost never exactly right), it gives you a distribution of possible outcomes. Think of it this way: if you're projecting revenue growth of 10% per month, the simulation might test what happens if growth is actually 7%, 10%, 12%, or even -2% in any given month. By running thousands of these variations, you get a realistic picture of the range of outcomes you might face.
            </p>
            <p>
              FounderConsole runs between 1,000 and 10,000 iterations per simulation (configurable), projects 24 months forward, and accounts for compounding effects across revenue, expenses, hiring costs, and fundraising events. The engine also models second-order effects — for example, if you model a hiring plan, it factors in not just salaries but ramp-up time before new hires become productive.
            </p>
          </SubSection>

          <SubSection title="Reading Your Results: P10, P50, P90">
            <p>
              Results are presented as three key percentiles. <strong>P10</strong> is the pessimistic case — 90% of simulation runs produced a better outcome than this. Use P10 to understand your downside risk and worst-case runway. <strong>P50</strong> is the median — half of runs did better, half did worse. This is your most likely outcome and the best number to use for planning. <strong>P90</strong> is the optimistic case — only 10% of runs beat this number. P90 shows your upside potential, but don't plan around it.
            </p>
            <p>
              A healthy scenario shows a narrow spread between P10 and P90 (meaning outcomes are predictable) and a P10 runway of at least 6 months. If the spread is very wide, it means your outcome is highly uncertain and you should look at which input variables are driving that uncertainty using the sensitivity analysis view.
            </p>
          </SubSection>

          <SubSection title="Decision Scores and Recommendations">
            <p>
              After each simulation, the AI generates a Decision Score from 0 to 100 along with a verdict: GO (score above 70, proceed with confidence), CONDITIONAL (score 40-70, proceed with modifications), or NO-GO (score below 40, reconsider the plan). The score factors in runway impact, burn rate changes, revenue upside, and risk concentration. You'll also see a Before/After Delta Card showing how the scenario changes your key metrics compared to your current baseline, and a Payback Clock showing how long it takes for the investment to pay for itself. Use these tools together to make informed decisions — the simulation tells you what could happen, and the AI recommendation tells you whether it's worth the risk.
            </p>
          </SubSection>
        </Section>

        <Section
          icon={Brain}
          title="AI Copilot"
          subtitle="Ask questions about your finances and get data-backed strategic guidance"
          testId="card-copilot-guide"
        >
          <SubSection title="How the AI Copilot Works">
            <p>
              The FounderConsole AI Copilot is a multi-agent system that routes your question to the right specialist. When you type a question, a router agent analyzes it and directs it to one of several specialized agents: a financial analyst for metrics and forecasting questions, a strategy advisor for growth and fundraising decisions, a data analyst for digging into your numbers, or a market researcher for competitive benchmarks and industry data. Each agent has access to your company's financial data (your Company Knowledge Base) and can pull in real-time market information when needed.
            </p>
            <p>
              Every response includes an "AI insights are informational only" disclaimer and a data timestamp so you know how current the analysis is. You can expand the Sources section at the bottom of any response to see exactly which data points and external sources the AI used.
            </p>
          </SubSection>

          <SubSection title="What to Ask">
            <p>
              The copilot works best with specific, actionable questions. Good examples include: "What's our projected runway if we maintain current burn?" or "How does our gross margin compare to SaaS benchmarks at our stage?" or "Should we hire two more engineers now or wait until after our next round?" or "What's the optimal price increase we could implement without significant churn risk?" The copilot can also help you interpret simulation results — after running a scenario, try asking "Explain the key risks in my latest simulation" or "What would improve the Decision Score for this scenario?"
            </p>
            <p>
              Avoid vague questions like "How are we doing?" — instead, ask about specific metrics or decisions. The more context you give, the better the response. You can reference specific time periods ("How did our burn change in Q4 vs Q3?"), specific scenarios ("Compare scenario A vs scenario B"), or ask for recommendations with constraints ("What's the safest way to extend runway to 18 months without cutting the engineering team?").
            </p>
          </SubSection>

          <SubSection title="Web Research and Market Data">
            <p>
              The copilot can search the web in real-time to pull in market benchmarks, industry reports, and competitor information. When you ask questions about market comparisons, fundraising benchmarks, or industry trends, the copilot uses Perplexity-powered search to find current data and weave it into your company-specific analysis. For example, asking "What are typical Series A terms for B2B SaaS companies at our ARR?" will combine public market data with your specific financial profile to give you a tailored answer.
            </p>
          </SubSection>
        </Section>

        <Section
          icon={Plug}
          title="Integrations"
          subtitle="Connect your financial tools to automatically sync data into FounderConsole"
          testId="card-integrations-guide"
        >
          <SubSection title="Connecting QuickBooks">
            <p>
              Go to the Integrations page from the sidebar and find QuickBooks in the list of active connectors. Click "Connect" and you'll be redirected to Intuit's authorization page where you sign in with your QuickBooks credentials and grant FounderConsole read-only access to your financial data. Once connected, the platform automatically syncs your chart of accounts, income statements, balance sheet, and cash flow data on a daily basis. Your dashboard metrics and simulation inputs will update automatically as new data comes in. You can disconnect at any time from the Integrations page — disconnecting removes the data sync but does not delete any data already imported.
            </p>
          </SubSection>

          <SubSection title="Connecting Stripe">
            <p>
              Stripe integration pulls in your revenue data, subscription metrics, and payment history. From the Integrations page, click "Connect" next to Stripe and authorize the connection through Stripe's OAuth flow. Once connected, FounderConsole imports your MRR, ARR, churn rate, average revenue per customer, and transaction-level data. This is especially useful for SaaS companies — the platform uses your Stripe data to calculate accurate revenue growth trends, detect anomalies in payment patterns, and feed more precise inputs into your Monte Carlo simulations. The sync runs automatically every few hours, and you can trigger a manual sync from the Integrations page whenever you need the latest numbers.
            </p>
          </SubSection>

          <SubSection title="Connecting Payroll Providers (Gusto, Keka, GreytHR)">
            <p>
              Payroll integrations bring in your compensation data so the platform can accurately model your burn rate and hiring scenarios. Navigate to the Integrations page, find your payroll provider, and follow the OAuth authorization flow. Once connected, FounderConsole imports salary data, headcount, department breakdowns, and benefit costs. This data powers the hiring plan simulator — when you model adding new roles, the engine uses your actual average compensation data by department instead of rough estimates. Payroll data also improves the accuracy of your burn rate calculations and cash flow projections. All compensation data is encrypted and only visible to users with owner or admin roles in your company.
            </p>
          </SubSection>
        </Section>

        <Card data-testid="card-contact-support">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HelpCircle className="h-5 w-5 text-muted-foreground" />
              Need Help?
            </CardTitle>
            <CardDescription>
              Can't find what you're looking for? Our team is here to help.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-4">
            <Button variant="outline" asChild data-testid="button-email-support">
              <a href="mailto:support@founderconsole.ai">
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
      </div>
    </div>
  );
}
