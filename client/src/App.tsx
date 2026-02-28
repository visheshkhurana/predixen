import { useEffect, useState, useRef, useCallback, lazy, Suspense } from "react";
const ReactMarkdownLazy = lazy(() => import("react-markdown").then(m => ({ default: m.default })));
import { Switch, Route, Redirect, useLocation } from "wouter";
import { queryClient, apiRequest } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/theme-provider";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { Stepper } from "@/components/Layout/Stepper";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { ContextBar } from "@/components/ContextBar";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { PageErrorFallback } from "@/components/PageErrorFallback";
import { BackendStatusBanner } from "@/components/BackendStatusBanner";
import { useFounderStore } from "@/store/founderStore";
import { Bell, Sun, AlertTriangle, TrendingDown, Clock, Sparkles, DollarSign, Flame, Timer, BarChart3, Send, Command, Loader2 } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { api } from "@/api/client";
import { useFinancialMetrics } from "@/hooks/useFinancialMetrics";
import { formatCurrencyAbbrev } from "@/lib/utils";
import GlobalLoadingBar from "@/components/GlobalLoadingBar";
import { AskAIButton } from "@/components/AskAIButton";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import AuthPage from "@/pages/auth";
import AuthCallback from "@/pages/auth-callback";
import OnboardingPage from "@/pages/onboarding";
import OverviewPage from "@/pages/overview";
import TruthScanPage from "@/pages/truth-scan";
import ScenariosPage from "@/pages/scenarios";
import DecisionsPage from "@/pages/decisions";
import CopilotPage from "@/pages/copilot";
import DataInputPage from "@/pages/data-input";
import IntegrationsPage from "@/pages/integrations";
import AlertsPage from "@/pages/alerts";
import TemplatesPage from "@/pages/templates";
import DataVerificationPage from "@/pages/data-verification";
import NotFound from "@/pages/not-found";
import DemoRedirectPage from "@/pages/demo-redirect";
import AdminDashboard from "@/pages/admin/index";
import AdminUsers from "@/pages/admin/users";
import AdminCompanies from "@/pages/admin/companies";
import AdminBilling from "@/pages/admin/billing";
import AdminMetrics from "@/pages/admin/metrics";
import AdminLoginHistory from "@/pages/admin/login-history";
import AdminActivity from "@/pages/admin/activity";
import AdminInvites from "@/pages/admin/invites";
import AdminEmailTemplates from "@/pages/admin/email-templates";
import AdminEmailTracking from "@/pages/admin/email-tracking";
import AdminLoginPage from "@/pages/admin/login";
import AdminLLMAudit from "@/pages/admin/llm-audit";
import AdminEvals from "@/pages/admin/evals";
import AiGovernancePage from "@/pages/admin/ai-governance";
import AdminTeam from "@/pages/admin/team";
import { AdminLayout } from "@/components/admin/AdminLayout";
import OwnerConsole from "@/pages/owner-console";
import FundraisingPage from "@/pages/fundraising";
import CapTablePage from "@/pages/cap-table";
import InvestorRoomPage from "@/pages/investor-room";
import KPIBoardPage from "@/pages/kpi-board";
import ConnectorMarketplacePage from "@/pages/connector-marketplace";
import AddDataSourcePage from "@/pages/add-data-source";
import DashboardsPage from "@/pages/dashboards";
import DashboardBuilderPage from "@/pages/dashboard-builder";
import MetricCatalogPage from "@/pages/metric-catalog";
import SuggestedMetricsPage from "@/pages/suggested-metrics";
import DocsPage from "@/pages/docs";
import MessagingPage from "@/pages/messaging";
import JournalPage from "@/pages/journal";
import GoalsPage from "@/pages/goals";
import SharedScenarioPage from "@/pages/shared-scenario";
import QAFrontPage from "@/pages/qa";
import PricingPage from "@/pages/pricing";

function AuthenticatedRoute({ component: Component, allowWithoutCompany = false }: { component: React.ComponentType; allowWithoutCompany?: boolean }) {
  const token = useFounderStore((s) => s.token);
  const currentCompany = useFounderStore((s) => s.currentCompany);

  if (!token) {
    return <Redirect to="/auth" />;
  }

  if (!allowWithoutCompany && !currentCompany) {
    return <Redirect to="/onboarding" />;
  }

  // Wrap authenticated routes with page-level error boundary
  return (
    <ErrorBoundary
      fallback={(error, reset) => (
        <PageErrorFallback
          error={error}
          reset={reset}
          pageName="Page"
        />
      )}
      onError={(error, info) => {
        console.error('Authenticated Route Error:', error);
        console.error('Component Stack:', info.componentStack);
      }}
    >
      <Component />
    </ErrorBoundary>
  );
}

function AdminRoute({ component: Component }: { component: React.ComponentType }) {
  const token = useFounderStore((s) => s.token);
  const user = useFounderStore((s) => s.user);
  const setUser = useFounderStore((s) => s.setUser);
  const isAdmin = useFounderStore((s) => s.isAdmin);
  const [loading, setLoading] = useState(!user?.role);
  const [accessDenied, setAccessDenied] = useState(false);
  
  useEffect(() => {
    if (token && !user?.role) {
      api.admin.me()
        .then((data) => {
          if (user) {
            setUser({ ...user, role: data.role });
          }
          setLoading(false);
          if (!data.is_admin) {
            setAccessDenied(true);
          }
        })
        .catch(() => {
          setLoading(false);
          setAccessDenied(true);
        });
    } else {
      setLoading(false);
      if (user?.role && !isAdmin()) {
        setAccessDenied(true);
      }
    }
  }, [token, user?.role]);

  // Identify user for Analytics & Remarketing when already logged in
  useEffect(() => {
    if (user?.id && user?.email) {
      if ((window as any).gtag) {
        (window as any).gtag('config', 'G-NJKW0TGC4C', { user_id: String(user.id) });
        (window as any).gtag('set', 'user_properties', { user_email: user.email });
      }
      if ((window as any).fbq) {
        (window as any).fbq('init', '872167299140812', { em: user.email });
      }
    }
  }, [user]);

  
  if (!token) {
    return <Redirect to="/admin/login" />;
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="text-muted-foreground">Checking access...</div>
      </div>
    );
  }
  
  if (accessDenied) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-background gap-4">
        <div className="text-2xl font-bold text-destructive">Access Denied</div>
        <p className="text-muted-foreground">You don't have permission to access the admin console.</p>
        <a href="/admin/login" className="text-primary hover:underline">Go to Admin Login</a>
      </div>
    );
  }

  // Wrap admin routes with error boundary
  return (
    <ErrorBoundary
      fallback={(error, reset) => (
        <PageErrorFallback
          error={error}
          reset={reset}
          pageName="Admin Panel"
        />
      )}
      onError={(error, info) => {
        console.error('Admin Route Error:', error);
        console.error('Component Stack:', info.componentStack);
      }}
    >
      <AdminLayout>
        <Component />
      </AdminLayout>
    </ErrorBoundary>
  );
}

function Router() {
  return (
    <ErrorBoundary
      onError={(error) => {
        // Log to console with context
        console.error('Router Error:', error);
      }}
    >
      <Switch>
        <Route path="/pricing" component={PricingPage} />
        <Route path="/auth/callback" component={AuthCallback} />
        <Route path="/auth" component={AuthPage} />
      <Route path="/login">
        {() => <Redirect to="/auth" />}
      </Route>
      <Route path="/onboarding">
        {() => <AuthenticatedRoute component={OnboardingPage} allowWithoutCompany />}
      </Route>
      <Route path="/">
        {() => <AuthenticatedRoute component={OverviewPage} />}
      </Route>
      <Route path="/overview">
        {() => <AuthenticatedRoute component={OverviewPage} />}
      </Route>
      <Route path="/dashboard">
        {() => <AuthenticatedRoute component={OverviewPage} />}
      </Route>
      <Route path="/kpi-board">
        {() => <AuthenticatedRoute component={KPIBoardPage} />}
      </Route>
      <Route path="/truth-scan">
          {() => <AuthenticatedRoute component={TruthScanPage} />}
        </Route>
        <Route path="/truth">
        {() => <AuthenticatedRoute component={TruthScanPage} />}
      </Route>
      <Route path="/data">
        {() => <AuthenticatedRoute component={DataInputPage} />}
      </Route>
      <Route path="/data/verify/:sessionId">
        {() => <AuthenticatedRoute component={DataVerificationPage} />}
      </Route>
      <Route path="/simulate">
        {() => <Redirect to="/scenarios" />}
      </Route>
      <Route path="/scenarios">
        {() => <AuthenticatedRoute component={ScenariosPage} />}
      </Route>
      <Route path="/scenarios/:id">
        {() => <AuthenticatedRoute component={ScenariosPage} />}
      </Route>
      <Route path="/decisions">
        {() => <AuthenticatedRoute component={DecisionsPage} />}
      </Route>
      <Route path="/copilot">
        {() => <AuthenticatedRoute component={CopilotPage} />}
      </Route>
      <Route path="/integrations">
        {() => <AuthenticatedRoute component={IntegrationsPage} />}
      </Route>
      <Route path="/marketplace">
        {() => <AuthenticatedRoute component={ConnectorMarketplacePage} />}
      </Route>
      <Route path="/add-data-source">
        {() => <AuthenticatedRoute component={AddDataSourcePage} />}
      </Route>
      <Route path="/alerts">
        {() => <AuthenticatedRoute component={AlertsPage} />}
      </Route>
      <Route path="/templates">
        {() => <AuthenticatedRoute component={TemplatesPage} />}
      </Route>
      <Route path="/docs">
        {() => <AuthenticatedRoute component={DocsPage} />}
      </Route>
      <Route path="/admin/messaging">
        {() => <AdminRoute component={MessagingPage} />}
      </Route>
      <Route path="/cap-table">
        {() => <AuthenticatedRoute component={CapTablePage} />}
      </Route>
      <Route path="/fundraising">
        {() => <AuthenticatedRoute component={FundraisingPage} />}
      </Route>
      <Route path="/investor-room">
        {() => <AuthenticatedRoute component={InvestorRoomPage} />}
      </Route>
      <Route path="/dashboards">
        {() => <AuthenticatedRoute component={DashboardsPage} />}
      </Route>
      <Route path="/dashboard/:id">
        {() => <AuthenticatedRoute component={DashboardBuilderPage} />}
      </Route>
      <Route path="/metrics">
        {() => <AuthenticatedRoute component={MetricCatalogPage} />}
      </Route>
      <Route path="/suggested-metrics">
        {() => <AuthenticatedRoute component={SuggestedMetricsPage} />}
      </Route>
      <Route path="/journal">
        {() => <AuthenticatedRoute component={JournalPage} />}
      </Route>
      <Route path="/goals">
        {() => <AuthenticatedRoute component={GoalsPage} />}
      </Route>
      <Route path="/billing">
        {() => <Redirect to="/admin/billing" />}
      </Route>
      <Route path="/admin/login" component={AdminLoginPage} />
      <Route path="/admin">
        {() => <AdminRoute component={AdminDashboard} />}
      </Route>
      <Route path="/admin/users">
        {() => <AdminRoute component={AdminUsers} />}
      </Route>
      <Route path="/admin/companies">
        {() => <AdminRoute component={AdminCompanies} />}
      </Route>
      <Route path="/admin/billing">
        {() => <AdminRoute component={AdminBilling} />}
      </Route>
      <Route path="/admin/metrics">
        {() => <AdminRoute component={AdminMetrics} />}
      </Route>
      <Route path="/admin/login-history">
        {() => <AdminRoute component={AdminLoginHistory} />}
      </Route>
      <Route path="/admin/activity">
        {() => <AdminRoute component={AdminActivity} />}
      </Route>
      <Route path="/admin/invites">
        {() => <AdminRoute component={AdminInvites} />}
      </Route>
      <Route path="/admin/email-templates">
        {() => <AdminRoute component={AdminEmailTemplates} />}
      </Route>
      <Route path="/admin/email-tracking">
        {() => <AdminRoute component={AdminEmailTracking} />}
      </Route>
      <Route path="/admin/llm-audit">
        {() => <AdminRoute component={AdminLLMAudit} />}
      </Route>
      <Route path="/admin/evals">
        {() => <AdminRoute component={AdminEvals} />}
      </Route>
                <Route path="/admin/ai-governance">
                    {() => <AdminRoute component={AiGovernancePage} />}
                </Route>
      <Route path="/admin/team">
        {() => <AdminRoute component={AdminTeam} />}
      </Route>
      <Route path="/qa">
        {() => <AdminRoute component={QAFrontPage} />}
      </Route>
        <Route path="/scenarios/shared/:uuid" component={SharedScenarioPage} />
        <Route path="/owner-console" component={OwnerConsole} />
        <Route path="/demo" component={DemoRedirectPage} />
        <Route component={NotFound} />
      </Switch>
    </ErrorBoundary>
  );
}

interface CopilotMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
  followups?: string[];
}

function CopilotDrawer({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { currentCompany } = useFounderStore();

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 100);
  }, [open]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const sendMessage = useCallback(async (overrideMsg?: string) => {
    const q = (overrideMsg || input).trim();
    if (!q || isLoading || !currentCompany?.id) return;
    if (!overrideMsg) setInput('');
    setMessages(prev => [...prev, { role: 'user', content: q }]);
    setIsLoading(true);
    try {
      const history = messages.map(m => ({ role: m.role, content: m.content }));
      const res = await apiRequest('POST', `/api/companies/${currentCompany.id}/quick-chat`, {
        message: q,
        conversation_history: history,
      });
      const data = await res.json();
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response || 'No response available.',
        sources: data.sources_used,
        followups: data.suggested_followups,
      }]);
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I couldn\'t process that right now. Try again or visit the full Copilot page.' }]);
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, currentCompany?.id, messages]);

  const clearChat = useCallback(() => {
    setMessages([]);
    setInput('');
  }, []);

  const lastAssistantMsg = messages.filter(m => m.role === 'assistant').slice(-1)[0];

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[420px] sm:w-[480px] p-0 flex flex-col" data-testid="drawer-copilot">
        <SheetHeader className="p-4 pb-2 border-b shrink-0">
          <SheetTitle className="flex items-center gap-2 text-sm">
            <Sparkles className="h-4 w-4 text-primary" />
            AI Copilot
            {messages.length > 0 && (
              <Button variant="ghost" size="sm" onClick={clearChat} className="ml-auto text-xs text-muted-foreground h-6 px-2" data-testid="button-copilot-clear">
                Clear
              </Button>
            )}
            <Badge variant="secondary" className={`text-[10px] px-1.5 py-0 h-4 bg-primary/15 text-primary border-0 ${messages.length === 0 ? 'ml-auto' : ''}`}>
              <Command className="h-2.5 w-2.5 mr-0.5" />K
            </Badge>
          </SheetTitle>
        </SheetHeader>
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
          {!currentCompany && messages.length === 0 && (
            <div className="text-center py-8 space-y-3">
              <AlertTriangle className="h-8 w-8 text-muted-foreground/40 mx-auto" />
              <p className="text-sm text-muted-foreground">Select a company first to start chatting with the AI copilot.</p>
            </div>
          )}
          {currentCompany && messages.length === 0 && (
            <div className="text-center py-8 space-y-4">
              <Sparkles className="h-8 w-8 text-primary/40 mx-auto" />
              <div>
                <p className="text-sm font-medium">Ask anything about your finances</p>
                <p className="text-xs text-muted-foreground mt-1">I have access to all your company data and real-time market research</p>
              </div>
              <div className="flex flex-col gap-1.5">
                {[
                  'What was my payroll cost last month?',
                  'How has revenue trended over the last 3 months?',
                  'What\'s my current runway?',
                  'How does my burn rate compare to industry benchmarks?',
                  'What should my target gross margin be?',
                ].map(q => (
                  <Button key={q} variant="outline" size="sm" className="text-xs justify-start" onClick={() => sendMessage(q)} data-testid={`copilot-prompt-${q.slice(0, 20).replace(/\s/g, '-').toLowerCase()}`}>
                    {q}
                  </Button>
                ))}
              </div>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[90%] rounded-md px-3 py-2 text-sm ${msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`} data-testid={`copilot-msg-${i}`}>
                {msg.role === 'assistant' ? (
                  <div className="prose prose-sm dark:prose-invert max-w-none [&_p]:my-1 [&_ul]:my-1 [&_li]:my-0.5 [&_strong]:text-foreground">
                    <Suspense fallback={<span>{msg.content}</span>}><ReactMarkdownLazy skipHtml disallowedElements={['script', 'iframe', 'object', 'embed']}>{msg.content}</ReactMarkdownLazy></Suspense>
                  </div>
                ) : msg.content}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2 pt-1.5 border-t border-border/50">
                    {msg.sources.map(s => (
                      <span key={s} className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary/70">{s}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-muted rounded-md px-3 py-2 text-sm flex items-center gap-2">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Analyzing your data...
              </div>
            </div>
          )}
        </div>
        {!isLoading && lastAssistantMsg?.followups && lastAssistantMsg.followups.length > 0 && (
          <div className="px-4 pb-2 shrink-0">
            <div className="flex flex-wrap gap-1">
              {lastAssistantMsg.followups.map(f => (
                <Button key={f} variant="outline" size="sm" className="text-[11px] h-7" onClick={() => sendMessage(f)} data-testid={`copilot-followup-${f.slice(0, 15).replace(/\s/g, '-').toLowerCase()}`}>
                  {f}
                </Button>
              ))}
            </div>
          </div>
        )}
        <div className="border-t p-3 shrink-0">
          <div className="flex items-center gap-2">
            <Input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') sendMessage(); }}
              placeholder="Ask about your financials..."
              className="flex-1"
              data-testid="input-copilot-drawer"
            />
            <Button size="icon" onClick={() => sendMessage()} disabled={isLoading || !input.trim()} data-testid="button-copilot-send">
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function AppLayout({ children }: { children: React.ReactNode }) {
  const { token, currentCompany, truthScan, currentStep, currentScenario, latestRun } = useFounderStore();
  const [, navigate] = useLocation();
  const [briefingOpen, setBriefingOpen] = useState(false);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const { metrics: liveMetrics } = useFinancialMetrics();
  const confidence = truthScan?.data_confidence_score || 0;

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        const tag = (e.target as HTMLElement)?.tagName;
        const isEditable = tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement)?.isContentEditable;
        if (isEditable && !copilotOpen) return;
        e.preventDefault();
        setCopilotOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [copilotOpen]);
  
  const style = {
    "--sidebar-width": "16rem",
    "--sidebar-width-icon": "3rem",
  };
  
  // Check if we're on a standalone page (owner console, auth, onboarding, admin)
  const isStandalonePage = typeof window !== 'undefined' && 
    (window.location.pathname === '/owner-console' || 
     window.location.pathname === '/auth' ||
     window.location.pathname === '/pricing' ||
     window.location.pathname === '/demo' ||
     window.location.pathname === '/onboarding' ||
     window.location.pathname.startsWith('/admin') ||
     window.location.pathname.startsWith('/scenarios/shared/'));
  
  if (!token || isStandalonePage) {
    return <>{children}</>;
  }
  
  const getConfidenceBadge = () => {
    if (!truthScan) return null;
    const badgeClass = "text-xs whitespace-nowrap shrink-0 cursor-pointer";
    const handleClick = () => navigate('/data');
    if (confidence < 60) {
      return <Badge variant="destructive" className={badgeClass} onClick={handleClick} data-testid="badge-confidence">Confidence: {confidence}%</Badge>;
    } else if (confidence < 80) {
      return <Badge className={`bg-amber-500/20 text-amber-400 ${badgeClass}`} onClick={handleClick} data-testid="badge-confidence">Confidence: {confidence}%</Badge>;
    }
    return <Badge className={`bg-emerald-500/20 text-emerald-400 ${badgeClass}`} onClick={handleClick} data-testid="badge-confidence">Confidence: {confidence}%</Badge>;
  };

  return (
    <SidebarProvider style={style as React.CSSProperties}>
      <div className="flex h-screen w-full">
        <div className="no-print">
          <AppSidebar />
        </div>
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
          <BackendStatusBanner />
          <header className="no-print flex items-center justify-between gap-2 p-2 px-3 border-b bg-background sticky top-0 z-50">
            <div className="flex items-center gap-2 sm:gap-3 shrink-0">
              <SidebarTrigger data-testid="button-sidebar-toggle" className="shrink-0" />
              {currentCompany && <div className="hidden sm:block"><Stepper currentStep={currentStep} /></div>}
            </div>
            <div className="flex items-center gap-1.5 min-w-0">
              <div className="hidden lg:block min-w-0 overflow-hidden shrink">
                <ContextBar 
                  scenarioName={currentScenario?.name}
                  scenarioId={currentScenario?.id}
                  runId={latestRun?.id}
                  runTimestamp={latestRun?.timestamp}
                />
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="relative shrink-0" data-testid="button-header-alerts">
                    <Bell className="h-4 w-4" />
                    <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-red-500" data-testid="indicator-alert-dot" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-80">
                  <DropdownMenuLabel className="flex items-center justify-between gap-2 flex-wrap">
                    <span>Recent Alerts</span>
                    <Badge variant="destructive" className="text-[10px]" data-testid="badge-alert-count">3 active</Badge>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem className="flex items-start gap-3 p-3 cursor-pointer" onClick={() => navigate('/alerts')} data-testid="alert-item-runway">
                    <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
                    <div className="space-y-0.5 min-w-0">
                      <p className="text-sm font-medium" data-testid="text-alert-runway-title">Runway below 12 months</p>
                      <p className="text-xs text-muted-foreground">Cash reserves declining faster than projected</p>
                      <p className="text-[10px] text-muted-foreground flex items-center gap-1 flex-wrap"><Clock className="h-3 w-3" />2 hours ago</p>
                    </div>
                  </DropdownMenuItem>
                  <DropdownMenuItem className="flex items-start gap-3 p-3 cursor-pointer" onClick={() => navigate('/alerts')} data-testid="alert-item-burn">
                    <TrendingDown className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                    <div className="space-y-0.5 min-w-0">
                      <p className="text-sm font-medium" data-testid="text-alert-burn-title">Burn rate increased 15%</p>
                      <p className="text-xs text-muted-foreground">Monthly burn up from $18K to $20.7K</p>
                      <p className="text-[10px] text-muted-foreground flex items-center gap-1 flex-wrap"><Clock className="h-3 w-3" />5 hours ago</p>
                    </div>
                  </DropdownMenuItem>
                  <DropdownMenuItem className="flex items-start gap-3 p-3 cursor-pointer" onClick={() => navigate('/alerts')} data-testid="alert-item-churn">
                    <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                    <div className="space-y-0.5 min-w-0">
                      <p className="text-sm font-medium" data-testid="text-alert-churn-title">Churn spike detected</p>
                      <p className="text-xs text-muted-foreground">Churn rate at {liveMetrics.churnRatePct > 0 ? `${liveMetrics.churnRatePct.toFixed(1)}%` : '3.2%'}, above 2% target</p>
                      <p className="text-[10px] text-muted-foreground flex items-center gap-1 flex-wrap"><Clock className="h-3 w-3" />1 day ago</p>
                    </div>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem className="justify-center text-sm text-primary cursor-pointer" onClick={() => navigate('/alerts')} data-testid="button-view-all-alerts">
                    View All Alerts
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              <Button variant="ghost" size="sm" className="shrink-0" onClick={() => setBriefingOpen(true)} data-testid="button-header-briefing">
                <Sun className="h-4 w-4 mr-1" />
                <span className="hidden sm:inline">Briefing</span>
              </Button>
              {getConfidenceBadge()}
            </div>
          </header>
          <Dialog open={briefingOpen} onOpenChange={setBriefingOpen}>
            <DialogContent className="sm:max-w-lg" data-testid="modal-briefing">
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2 flex-wrap" data-testid="text-modal-briefing-title">
                  <Sun className="h-5 w-5 text-amber-400" />
                  Morning Briefing
                </DialogTitle>
                <DialogDescription data-testid="text-modal-briefing-date">
                  {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 pt-2">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1 p-3 rounded-md bg-muted/50">
                    <div className="flex items-center gap-1.5 flex-wrap text-xs text-muted-foreground">
                      <DollarSign className="h-3.5 w-3.5" />
                      MRR
                    </div>
                    <p className="text-lg font-semibold" data-testid="text-briefing-modal-mrr">{formatCurrencyAbbrev(liveMetrics.mrr)}</p>
                    <p className="text-xs text-emerald-500" data-testid="text-briefing-modal-mrr-growth">{liveMetrics.mrr > 0 ? '+8.2% growth' : 'No data yet'}</p>
                  </div>
                  <div className="space-y-1 p-3 rounded-md bg-muted/50">
                    <div className="flex items-center gap-1.5 flex-wrap text-xs text-muted-foreground">
                      <Flame className="h-3.5 w-3.5" />
                      Burn Rate
                    </div>
                    <p className="text-lg font-semibold" data-testid="text-briefing-modal-burn">{formatCurrencyAbbrev(liveMetrics.netBurn)}/mo</p>
                    <p className={`text-xs ${liveMetrics.burnMultiple > 2 ? 'text-amber-500' : 'text-emerald-500'}`} data-testid="text-briefing-modal-burn-status">{liveMetrics.burnMultiple > 2 ? 'Slightly elevated' : 'Under control'}</p>
                  </div>
                  <div className="space-y-1 p-3 rounded-md bg-muted/50">
                    <div className="flex items-center gap-1.5 flex-wrap text-xs text-muted-foreground">
                      <Timer className="h-3.5 w-3.5" />
                      Runway
                    </div>
                    <p className="text-lg font-semibold" data-testid="text-briefing-modal-runway">{liveMetrics.runwayDisplay}</p>
                    <p className="text-xs text-muted-foreground" data-testid="text-briefing-modal-runway-cash">{formatCurrencyAbbrev(liveMetrics.cashOnHand)} cash</p>
                  </div>
                  <div className="space-y-1 p-3 rounded-md bg-muted/50">
                    <div className="flex items-center gap-1.5 flex-wrap text-xs text-muted-foreground">
                      <BarChart3 className="h-3.5 w-3.5" />
                      LTV:CAC
                    </div>
                    <p className="text-lg font-semibold" data-testid="text-briefing-modal-ltvcac">{liveMetrics.ltvCacRatio > 0 ? `${liveMetrics.ltvCacRatio.toFixed(1)}x` : 'N/A'}</p>
                    <p className={`text-xs ${liveMetrics.ltvCacRatio >= 3 ? 'text-emerald-500' : liveMetrics.ltvCacRatio >= 2 ? 'text-amber-500' : 'text-red-500'}`} data-testid="text-briefing-modal-ltvcac-status">{liveMetrics.ltvCacRatio >= 3 ? 'Healthy' : liveMetrics.ltvCacRatio >= 2 ? 'Fair' : 'Needs attention'}</p>
                  </div>
                </div>
                <Separator />
                <div className="space-y-2">
                  <p className="text-sm font-medium flex items-center gap-1.5 flex-wrap">
                    <Sparkles className="h-4 w-4 text-primary" />
                    AI Insight
                  </p>
                  <p className="text-sm text-muted-foreground leading-relaxed" data-testid="text-briefing-modal-insight">
                    {liveMetrics.burnMultiple > 1.5 ? `Burn multiple is ${liveMetrics.burnMultiple > 0 ? `at ${liveMetrics.burnMultiple.toFixed(1)}x` : 'elevated'}. Consider simulating "What if we cut hiring by 30%?" to see the runway impact.` : `Your burn efficiency looks solid.`}
                    {liveMetrics.churnRatePct > 2 ? ` Your churn is above target at ${liveMetrics.churnRatePct.toFixed(1)}% \u2014 addressing this could add 4+ months of runway.` : liveMetrics.churnRatePct > 0 ? ` Churn at ${liveMetrics.churnRatePct.toFixed(1)}% is within healthy range.` : ''}
                  </p>
                </div>
                <Separator />
                <div className="flex items-center gap-2 flex-wrap">
                  <Button size="sm" onClick={() => { setBriefingOpen(false); navigate('/scenarios'); }} data-testid="button-briefing-modal-simulate">
                    Run Simulation
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => { setBriefingOpen(false); navigate('/overview'); }} data-testid="button-briefing-modal-overview">
                    Go to Overview
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
          <CopilotDrawer open={copilotOpen} onOpenChange={setCopilotOpen} />
          <Breadcrumbs />
          <main className="flex-1 overflow-auto bg-background">
            {children}
          </main>
          <AskAIButton />
        </div>
      </div>
    </SidebarProvider>
  );
}

function App() {
  return (
    <ErrorBoundary
      onError={(error) => {
        // Global error logging - this could send to an error tracking service
        console.error('App-level Error:', error);
      }}
    >
      <QueryClientProvider client={queryClient}>
        <ThemeProvider defaultTheme="dark" storageKey="founderconsole-theme">
          <TooltipProvider delayDuration={0}>
            <GlobalLoadingBar />
            <AppLayout>
              <Router />
            </AppLayout>
            <Toaster />
          </TooltipProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
