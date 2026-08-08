import { useEffect, useState, useRef, useCallback, lazy, Suspense, type ReactNode } from "react";
const ReactMarkdownLazy = lazy(() => import("react-markdown").then(m => ({ default: m.default })));
import { Switch, Route, Redirect, useLocation } from "wouter";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { queryClient, apiRequest } from "./lib/queryClient";
import { QueryClientProvider, useQuery } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/theme-provider";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { DashboardBackground } from "@/components/DashboardBackground";
import { Stepper } from "@/components/Layout/Stepper";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ContextBar } from "@/components/ContextBar";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { PageErrorFallback } from "@/components/PageErrorFallback";
import { BackendStatusBanner } from "@/components/BackendStatusBanner";
import { TrialBanner, PaywallGate } from "@/components/PaywallGate";
import { useFounderStore } from "@/store/founderStore";
import { initPostHog, identifyUser, resetUser, trackPageView, trackEvent } from "@/lib/posthog";
import { Bell, Sun, AlertTriangle, Clock, Sparkles, DollarSign, Flame, Timer, BarChart3, Send, Command, Loader2, FlaskConical, User, Settings, LogOut } from "lucide-react";
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

import { CookieConsent } from "@/components/CookieConsent";
import { Breadcrumbs } from "@/components/Breadcrumbs";
const AuthPage = lazy(() => import("@/pages/auth"));
const AuthCallback = lazy(() => import("@/pages/auth-callback"));
const ResetPasswordPage = lazy(() => import("@/pages/reset-password"));
const VerifyEmailPage = lazy(() => import("@/pages/verify-email"));
const PrivacyPolicyPage = lazy(() => import("@/pages/privacy"));
const TermsOfServicePage = lazy(() => import("@/pages/terms"));
const OnboardingPage = lazy(() => import("@/pages/onboarding"));
const OverviewPage = lazy(() => import("@/pages/overview"));
const TruthScanPage = lazy(() => import("@/pages/truth-scan"));
const ScenariosPage = lazy(() => import("@/pages/scenarios"));
const SimulateWorkspace = lazy(() => import("@/pages/simulate-workspace"));
import SimulateV2Page, { SharedSimulationPage } from "@/pages/simulate-v2";
const DecisionsPage = lazy(() => import("@/pages/decisions"));
const CopilotPage = lazy(() => import("@/pages/copilot"));
const DataInputPage = lazy(() => import("@/pages/data-input"));
const IntegrationsPage = lazy(() => import("@/pages/integrations"));
const AlertsPage = lazy(() => import("@/pages/alerts"));
const TemplatesPage = lazy(() => import("@/pages/templates"));
const DataVerificationPage = lazy(() => import("@/pages/data-verification"));
const NotFound = lazy(() => import("@/pages/not-found"));
const DemoRedirectPage = lazy(() => import("@/pages/demo-redirect"));
const AdminDashboard = lazy(() => import("@/pages/admin/index"));
const AdminUsers = lazy(() => import("@/pages/admin/users"));
const AdminCompanies = lazy(() => import("@/pages/admin/companies"));
const AdminBilling = lazy(() => import("@/pages/admin/billing"));
const AdminMetrics = lazy(() => import("@/pages/admin/metrics"));
const AdminLoginHistory = lazy(() => import("@/pages/admin/login-history"));
const AdminActivity = lazy(() => import("@/pages/admin/activity"));
const AdminInvites = lazy(() => import("@/pages/admin/invites"));
const AdminEmailTemplates = lazy(() => import("@/pages/admin/email-templates"));
const AdminEmailTracking = lazy(() => import("@/pages/admin/email-tracking"));
const AdminLoginPage = lazy(() => import("@/pages/admin/login"));
const AdminLLMAudit = lazy(() => import("@/pages/admin/llm-audit"));
const AdminEvals = lazy(() => import("@/pages/admin/evals"));
const AiGovernancePage = lazy(() => import("@/pages/admin/ai-governance"));
const AdminTeam = lazy(() => import("@/pages/admin/team"));
const AdminSystemTools = lazy(() => import("@/pages/admin/system-tools"));
const LeadGenAdmin = lazy(() => import("@/pages/admin/lead-gen"));
const AdminGrowth = lazy(() => import("@/pages/admin/growth"));
import { AdminLayout } from "@/components/admin/AdminLayout";
const OwnerConsole = lazy(() => import("@/pages/owner-console"));
const FundraisingPage = lazy(() => import("@/pages/fundraising"));
const CapTablePage = lazy(() => import("@/pages/cap-table"));
const InvestorRoomPage = lazy(() => import("@/pages/investor-room"));
const KPIBoardPage = lazy(() => import("@/pages/kpi-board"));
const ConnectorMarketplacePage = lazy(() => import("@/pages/connector-marketplace"));
const AddDataSourcePage = lazy(() => import("@/pages/add-data-source"));
const DashboardsPage = lazy(() => import("@/pages/dashboards"));
const DashboardBuilderPage = lazy(() => import("@/pages/dashboard-builder"));
const MetricCatalogPage = lazy(() => import("@/pages/metric-catalog"));
const SuggestedMetricsPage = lazy(() => import("@/pages/suggested-metrics"));
const DocsPage = lazy(() => import("@/pages/docs"));
const MessagingPage = lazy(() => import("@/pages/messaging"));
const JournalPage = lazy(() => import("@/pages/journal"));
const GoalsPage = lazy(() => import("@/pages/goals"));
const HiringPlannerPage = lazy(() => import("@/pages/hiring-planner"));
const SharedScenarioPage = lazy(() => import("@/pages/shared-scenario"));
const QAFrontPage = lazy(() => import("@/pages/qa"));
const PricingPage = lazy(() => import("@/pages/pricing"));
const AIGraphicsPage = lazy(() => import("@/pages/ai-graphics"));
const DocGeneratorPage = lazy(() => import("@/pages/doc-generator"));
const DigitalTwinPage = lazy(() => import("@/pages/digital-twin"));
const CompetitionPage = lazy(() => import("@/pages/competition"));
const IntelligenceGraphPage = lazy(() => import("@/pages/intelligence-graph"));
const SurvivalSimulatorPage = lazy(() => import("@/pages/survival-simulator"));
const SettingsPage = lazy(() => import("@/pages/settings"));
const BillingPage = lazy(() => import("@/pages/billing"));
const LandingPage = lazy(() => import("@/pages/landing"));
const MarketingFeaturesPage = lazy(() => import("@/pages/marketing-features"));
const AboutPage = lazy(() => import("@/pages/about"));
const ContactPage = lazy(() => import("@/pages/contact"));
const BlogPage = lazy(() => import("@/pages/blog"));
const RunwayByIndustryPage = lazy(() => import("@/pages/runway-by-industry"));
const EmbedSurvivalPage = lazy(() => import("@/pages/embed-survival"));
const FAQPage = lazy(() => import("@/pages/faq"));
const DemoPage = lazy(() => import("@/pages/demo"));
const RunwayCalculatorPage = lazy(() => import("@/pages/runway-calculator"));
const DefaultAlivePage = lazy(() => import("@/pages/default-alive"));
const AiCfoPage = lazy(() => import("@/pages/ai-cfo"));

function AuthenticatedRoute({ component: Component, allowWithoutCompany = false }: { component: React.ComponentType; allowWithoutCompany?: boolean }) {
  const user = useFounderStore((s) => s.user);
  const currentCompany = useFounderStore((s) => s.currentCompany);

  if (!user) {
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

function GatedRoute({ component: Component, feature }: { component: React.ComponentType; feature: string }) {
  const user = useFounderStore((s) => s.user);
  const currentCompany = useFounderStore((s) => s.currentCompany);

  if (!user) return <Redirect to="/auth" />;
  if (!currentCompany) return <Redirect to="/onboarding" />;

  return (
    <ErrorBoundary
      fallback={(error, reset) => <PageErrorFallback error={error} reset={reset} pageName="Page" />}
      onError={(error, info) => {
        console.error('Gated Route Error:', error);
        console.error('Component Stack:', info.componentStack);
      }}
    >
      <PaywallGate feature={feature}>
        <Component />
      </PaywallGate>
    </ErrorBoundary>
  );
}

function AdminRoute({ component: Component }: { component: React.ComponentType }) {
  const user = useFounderStore((s) => s.user);
  const setUser = useFounderStore((s) => s.setUser);
  const isAdmin = useFounderStore((s) => s.isAdmin);
  const [loading, setLoading] = useState(!user?.role);
  const [accessDenied, setAccessDenied] = useState(false);
  
  useEffect(() => {
    if (user && !user?.role) {
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
  }, [user, user?.role]);

  // Identify user for Analytics & Remarketing when already logged in
  useEffect(() => {
    if (user?.id && user?.email) {
      if ((window as any).gtag) {
        (window as any).gtag('config', 'G-NJKW0TGC4C', { user_id: String(user.id) });
        (window as any).gtag('set', 'user_properties', { user_email: user.email });
      }
    }
  }, [user]);

  
  if (!user) {
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

function PublicOrAuthHome() {
  const user = useFounderStore((s) => s.user);
  const currentCompany = useFounderStore((s) => s.currentCompany);

  if (user && currentCompany) {
    return <Redirect to="/overview" />;
  }

  if (user && !currentCompany) {
    return <Redirect to="/onboarding" />;
  }

  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>}>
      <LandingPage />
    </Suspense>
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
      <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>}>
      <Switch>
        <Route path="/survival-simulator" component={SurvivalSimulatorPage} />
        <Route path="/survival/:simId" component={SurvivalSimulatorPage} />
        <Route path="/pricing" component={PricingPage} />
        <Route path="/features">{() => <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>}><MarketingFeaturesPage /></Suspense>}</Route>
        <Route path="/about">{() => <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>}><AboutPage /></Suspense>}</Route>
        <Route path="/contact">{() => <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>}><ContactPage /></Suspense>}</Route>
        <Route path="/blog/:slug">{() => <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>}><BlogPage /></Suspense>}</Route>
        <Route path="/blog">{() => <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>}><BlogPage /></Suspense>}</Route>
        <Route path="/faq">{() => <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>}><FAQPage /></Suspense>}</Route>
        <Route path="/ai-cfo">{() => <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>}><AiCfoPage /></Suspense>}</Route>
        <Route path="/tools/runway-calculator">{() => <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>}><RunwayCalculatorPage /></Suspense>}</Route>
        <Route path="/default-alive">{() => <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>}><DefaultAlivePage /></Suspense>}</Route>
        <Route path="/runway/:slug">{() => <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>}><RunwayByIndustryPage /></Suspense>}</Route>
        <Route path="/embed/survival">{() => <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>}><EmbedSurvivalPage /></Suspense>}</Route>
        <Route path="/demo">{() => <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>}><DemoPage /></Suspense>}</Route>
        <Route path="/auth/callback" component={AuthCallback} />
        <Route path="/auth" component={AuthPage} />
        <Route path="/reset-password" component={ResetPasswordPage} />
        <Route path="/verify-email" component={VerifyEmailPage} />
        <Route path="/privacy" component={PrivacyPolicyPage} />
        <Route path="/terms" component={TermsOfServicePage} />
      {/* /login means login. The other three mean "I want an account" — they
          used to drop the query string and land people on the login tab, so
          anyone typing founderconsole.ai/signup or following an old link was
          shown the wrong form. */}
      <Route path="/login">
        {() => <Redirect to="/auth" />}
      </Route>
      <Route path="/signup">
        {() => <Redirect to="/auth?tab=register" />}
      </Route>
      <Route path="/register">
        {() => <Redirect to="/auth?tab=register" />}
      </Route>
      <Route path="/join">
        {() => <Redirect to="/auth?tab=register" />}
      </Route>
      <Route path="/onboarding">
        {() => <AuthenticatedRoute component={OnboardingPage} allowWithoutCompany />}
      </Route>
      <Route path="/">
        {() => <PublicOrAuthHome />}
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
      <Route path="/health-check">
        {() => <AuthenticatedRoute component={TruthScanPage} />}
      </Route>
      <Route path="/data">
        {() => <AuthenticatedRoute component={DataInputPage} />}
      </Route>
      <Route path="/data/verify/:sessionId">
        {() => <AuthenticatedRoute component={DataVerificationPage} />}
      </Route>
      <Route path="/simulate">
        {() => <AuthenticatedRoute component={SimulateWorkspace} />}
      </Route>
      <Route path="/simulator">
        {() => <Redirect to="/simulate" />}
      </Route>
      <Route path="/simulate-v2">
        {() => <AuthenticatedRoute component={SimulateV2Page} />}
      </Route>
      <Route path="/simulate-v2/shared/:token">
        {() => <SharedSimulationPage />}
      </Route>
      <Route path="/help">
        {() => <Redirect to="/docs" />}
      </Route>
      <Route path="/data-input">
        {() => <Redirect to="/data" />}
      </Route>
      <Route path="/scenarios">
        {() => <Redirect to="/simulate" />}
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
        {() => <GatedRoute component={CapTablePage} feature="cap_table" />}
      </Route>
      <Route path="/fundraising">
        {() => <GatedRoute component={FundraisingPage} feature="fundraising_os" />}
      </Route>
      <Route path="/investor-room">
        {() => <GatedRoute component={InvestorRoomPage} feature="investor_room" />}
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
      <Route path="/hiring-planner">
        {() => <GatedRoute component={HiringPlannerPage} feature="hiring_planner" />}
      </Route>
      <Route path="/doc-generator">
        {() => <GatedRoute component={DocGeneratorPage} feature="document_generator" />}
      </Route>
      <Route path="/ai-graphics">
        {() => <GatedRoute component={AIGraphicsPage} feature="ai_graphics" />}
      </Route>
      <Route path="/digital-twin">
        {() => <GatedRoute component={DigitalTwinPage} feature="digital_twin" />}
      </Route>
      <Route path="/competition">
        {() => <AuthenticatedRoute component={CompetitionPage} />}
      </Route>
      <Route path="/intelligence">
        {() => <AuthenticatedRoute component={IntelligenceGraphPage} />}
      </Route>
      <Route path="/settings">
        {() => <AuthenticatedRoute component={SettingsPage} allowWithoutCompany />}
      </Route>
      <Route path="/profile">
        {() => <Redirect to="/settings" />}
      </Route>
      <Route path="/billing">
        {() => <AuthenticatedRoute component={BillingPage} allowWithoutCompany />}
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
      <Route path="/admin/system">
        {() => <AdminRoute component={AdminSystemTools} />}
      </Route>
      <Route path="/admin/growth">
        {() => <AdminRoute component={AdminGrowth} />}
      </Route>
      <Route path="/admin/lead-gen">
        {() => <AdminRoute component={LeadGenAdmin} />}
      </Route>
      <Route path="/admin/lead-gen/leads">
        {() => <AdminRoute component={LeadGenAdmin} />}
      </Route>
      <Route path="/admin/lead-gen/campaigns">
        {() => <AdminRoute component={LeadGenAdmin} />}
      </Route>
      <Route path="/admin/lead-gen/templates">
        {() => <AdminRoute component={LeadGenAdmin} />}
      </Route>
      <Route path="/admin/lead-gen/settings">
        {() => <AdminRoute component={LeadGenAdmin} />}
      </Route>
      <Route path="/qa">
        {() => <AdminRoute component={QAFrontPage} />}
      </Route>
        <Route path="/scenarios/shared/:uuid" component={SharedScenarioPage} />
        <Route path="/owner-console" component={OwnerConsole} />
        <Route component={NotFound} />
      </Switch>
      </Suspense>
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
      trackEvent('copilot_message', { company_id: currentCompany?.id, source: 'drawer' });
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

/**
 * Relative age for an alert timestamp.
 *
 * The server stores naive UTC ISO strings with no trailing Z. Parsed as-is the
 * browser reads them as local time, which is how the dashboard ended up showing
 * data as "in about 7 hours". Append the Z when it is missing.
 */
function formatAlertAge(timestamp: string): string {
  const iso = /[zZ]|[+-]\d{2}:?\d{2}$/.test(timestamp) ? timestamp : `${timestamp}Z`;
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} minute${mins === 1 ? "" : "s"} ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs} hour${hrs === 1 ? "" : "s"} ago`;
  const days = Math.round(hrs / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, currentCompany, truthScan, currentStep, currentScenario, latestRun } = useFounderStore();
  const [location, navigate] = useLocation();
  const [briefingOpen, setBriefingOpen] = useState(false);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const { metrics: liveMetrics, isLoading: metricsLoading } = useFinancialMetrics();
  const confidence = truthScan?.data_confidence_score || 0;

  /**
   * Real alerts for the header bell.
   *
   * This used to be three hardcoded <DropdownMenuItem>s — "Runway below 12
   * months / 2 hours ago", "Monthly burn up from $18K to $20.7K", a "3 active"
   * badge and an unconditional red dot — none of it tied to any company. A
   * founder with zero alerts saw a clean sidebar and, inches away, a red dot
   * claiming three, with dollar figures belonging to nobody. The churn item even
   * fell back to the literal '3.2%', the same invented churn figure that was
   * removed from the truth scan.
   *
   * Same query key the sidebar already uses, so the two read from one source and
   * cannot disagree.
   */
  const { data: smartAlertsData } = useQuery<{ alerts: any[]; total: number; unacknowledged_count?: number }>({
    queryKey: ["/api/companies", currentCompany?.id, "smart-alerts"],
    enabled: !!currentCompany?.id,
  });

  const headerAlerts = (smartAlertsData?.alerts ?? []).filter((a: any) => !a.acknowledged);
  // The API returns unacknowledged_count; keep the client-side count as a
  // fallback so a shape change degrades to "no badge" rather than a wrong one.
  const unreadAlertCount = smartAlertsData?.unacknowledged_count ?? headerAlerts.length;

  useEffect(() => {
    initPostHog();
  }, []);

  useEffect(() => {
    trackPageView(location);
  }, [location]);

  useEffect(() => {
    if (user) {
      identifyUser(user.id, user.email, user.role);
    } else {
      resetUser();
    }
  }, [user]);

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
  
  const marketingPaths = [
    '/', '/features', '/pricing', '/about', '/blog', '/faq',
    '/contact', '/demo', '/auth', '/onboarding', '/owner-console',
    '/survival-simulator', '/default-alive', '/privacy', '/terms',
    '/reset-password', '/verify-email', '/auth/callback',
    '/login', '/signup', '/register', '/join',
    '/ai-cfo', '/embed/survival',
  ];
  const marketingPrefixes = [
    '/blog/', '/tools/', '/admin', '/scenarios/shared/',
    '/survival/', '/runway/', '/embed/',
  ];
  // Use wouter's location (not window.location) so client-side navigations
  // re-evaluate the shell instead of keeping whatever was true on hard load.
  const currentPath = (location || (typeof window !== 'undefined' ? window.location.pathname : '/')).split('?')[0];
  const isStandalonePage =
    marketingPaths.includes(currentPath) ||
    marketingPrefixes.some((p) => currentPath.startsWith(p));
  
  if (!user || isStandalonePage) {
    return <>{children}</>;
  }
  
  const getConfidenceBadge = () => {
    if (!truthScan) return null;
    const badgeClass = "text-xs whitespace-nowrap shrink-0 cursor-pointer hidden sm:inline-flex";
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
      <div className="flex h-screen w-full relative">
        <DashboardBackground />
        <div className="no-print">
          <AppSidebar />
        </div>
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden relative z-[1]">
          <BackendStatusBanner />
          <TrialBanner />
          {user?.email === 'demo@founderconsole.ai' && (
            <div className="no-print flex items-center justify-center gap-2 bg-amber-500/15 border-b border-amber-500/30 px-3 py-1.5 text-xs font-medium text-amber-400" data-testid="banner-demo-mode">
              <FlaskConical className="h-3.5 w-3.5 shrink-0" />
              {/*
                This is the ONLY way out of the demo, so it has to actually
                work. It previously linked to bare /auth, which lands on the
                login tab — and because the demo session is still active,
                PublicOrAuthHome bounced the user straight back to /overview.
                A recorded visitor tried /auth and / in turn and was returned
                to /overview both times before giving up.

                Signing out first is what makes the escape real: it clears the
                demo session so /auth?tab=register renders instead of
                redirecting.
              */}
              <span>
                Demo Mode — You are viewing simulated sample data.{" "}
                <button
                  type="button"
                  className="underline hover:text-amber-300"
                  data-testid="button-demo-exit-signup"
                  onClick={async () => {
                    try { await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }); } catch {}
                    useFounderStore.getState().logout();
                    navigate('/auth?tab=register');
                  }}
                >
                  Sign up free
                </button>{" "}
                to use your own.
              </span>
            </div>
          )}
          <header className="no-print flex items-center justify-between gap-2 p-2 px-3 border-b border-white/[0.06] bg-background/60 backdrop-blur-xl sticky top-0 z-50">
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
                  <Button
                    variant="ghost"
                    size="icon"
                    className="relative shrink-0"
                    data-testid="button-header-alerts"
                    aria-label={unreadAlertCount > 0 ? `Alerts, ${unreadAlertCount} unread` : "Alerts, none unread"}
                  >
                    <Bell className="h-4 w-4" />
                    {/* Gated on the real count. It used to render unconditionally,
                        so every account permanently looked like it had alerts. */}
                    {unreadAlertCount > 0 && (
                      <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-red-500" data-testid="indicator-alert-dot" />
                    )}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-80">
                  <DropdownMenuLabel className="flex items-center justify-between gap-2 flex-wrap">
                    <span>Recent Alerts</span>
                    {unreadAlertCount > 0 && (
                      <Badge variant="destructive" className="text-[10px]" data-testid="badge-alert-count">
                        {unreadAlertCount} active
                      </Badge>
                    )}
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {headerAlerts.length === 0 ? (
                    <div className="px-3 py-6 text-center" data-testid="alerts-empty">
                      <p className="text-sm text-muted-foreground">No active alerts</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        We&apos;ll flag runway, burn and retention changes here as they happen.
                      </p>
                    </div>
                  ) : (
                    headerAlerts.slice(0, 4).map((alert: any) => (
                      <DropdownMenuItem
                        key={alert.id}
                        className="flex items-start gap-3 p-3 cursor-pointer"
                        onClick={() => navigate('/alerts')}
                        data-testid={`alert-item-${alert.type || 'generic'}`}
                      >
                        <AlertTriangle
                          className={`h-4 w-4 mt-0.5 shrink-0 ${alert.severity === 'critical' ? 'text-red-500' : 'text-amber-500'}`}
                          aria-hidden="true"
                        />
                        <div className="space-y-0.5 min-w-0">
                          <p className="text-sm font-medium">{alert.title}</p>
                          {alert.message && (
                            <p className="text-xs text-muted-foreground">{alert.message}</p>
                          )}
                          {alert.timestamp && (
                            <p className="text-[10px] text-muted-foreground flex items-center gap-1 flex-wrap">
                              <Clock className="h-3 w-3" aria-hidden="true" />
                              {formatAlertAge(alert.timestamp)}
                            </p>
                          )}
                        </div>
                      </DropdownMenuItem>
                    ))
                  )}
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
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="shrink-0 rounded-full" data-testid="button-user-avatar">
                    <div className="h-7 w-7 rounded-full bg-primary/10 flex items-center justify-center text-xs font-semibold text-primary">
                      {user?.email?.charAt(0)?.toUpperCase() || 'U'}
                    </div>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel>
                    <p className="text-sm font-medium truncate">{user?.email || 'Account'}</p>
                    <p className="text-xs text-muted-foreground">{user?.role || 'Member'}</p>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem className="cursor-pointer" onClick={() => navigate('/settings')} data-testid="menu-item-settings">
                    <Settings className="h-4 w-4 mr-2" />
                    Settings
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="cursor-pointer text-destructive focus:text-destructive"
                    onClick={async () => {
                      try { await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }); } catch {}
                      useFounderStore.getState().logout();
                      window.location.href = '/auth';
                    }}
                    data-testid="menu-item-logout"
                  >
                    <LogOut className="h-4 w-4 mr-2" />
                    Sign Out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
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
                {metricsLoading ? (
                  <div className="grid grid-cols-2 gap-3">
                    {[1,2,3,4].map(i => (
                      <div key={i} className="space-y-2 p-3 rounded-md bg-muted/50">
                        <Skeleton className="h-3 w-12" />
                        <Skeleton className="h-6 w-20" />
                        <Skeleton className="h-3 w-16" />
                      </div>
                    ))}
                  </div>
                ) : (
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
                )}
                <Separator />
                {metricsLoading ? (
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-10 w-full" />
                  </div>
                ) : (
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
                )}
                <Separator />
                <div className="flex items-center gap-2 flex-wrap">
                  <Button size="sm" onClick={() => { setBriefingOpen(false); navigate('/simulate'); }} data-testid="button-briefing-modal-simulate">
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
            <AnimatedRouteWrapper>
              {children}
            </AnimatedRouteWrapper>
          </main>

          <AskAIButton />
          <CookieConsent />
        </div>
      </div>
    </SidebarProvider>
  );
}

function AnimatedRouteWrapper({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  const prefersReducedMotion = useReducedMotion();

  if (prefersReducedMotion) {
    return <>{children}</>;
  }

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={location}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -6 }}
        transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
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
