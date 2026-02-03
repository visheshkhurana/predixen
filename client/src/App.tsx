import { useEffect, useState } from "react";
import { Switch, Route, Redirect } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/theme-provider";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { Stepper } from "@/components/Layout/Stepper";
import { Badge } from "@/components/ui/badge";
import { ContextBar } from "@/components/ContextBar";
import { useFounderStore } from "@/store/founderStore";
import { api } from "@/api/client";
import AuthPage from "@/pages/auth";
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
import AdminDashboard from "@/pages/admin/index";
import AdminUsers from "@/pages/admin/users";
import AdminCompanies from "@/pages/admin/companies";
import AdminBilling from "@/pages/admin/billing";
import AdminMetrics from "@/pages/admin/metrics";
import AdminLoginHistory from "@/pages/admin/login-history";
import AdminActivity from "@/pages/admin/activity";
import AdminInvites from "@/pages/admin/invites";
import AdminEmailTemplates from "@/pages/admin/email-templates";
import AdminLoginPage from "@/pages/admin/login";
import AdminLLMAudit from "@/pages/admin/llm-audit";
import AdminEvals from "@/pages/admin/evals";
import { AdminLayout } from "@/components/admin/AdminLayout";
import OwnerConsole from "@/pages/owner-console";
import FundraisingPage from "@/pages/fundraising";
import InvestorRoomPage from "@/pages/investor-room";
import KPIBoardPage from "@/pages/kpi-board";
import ConnectorMarketplacePage from "@/pages/connector-marketplace";
import AddDataSourcePage from "@/pages/add-data-source";

function AuthenticatedRoute({ component: Component }: { component: React.ComponentType }) {
  const token = useFounderStore((s) => s.token);
  
  if (!token) {
    return <Redirect to="/auth" />;
  }
  
  return <Component />;
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
  
  return (
    <AdminLayout>
      <Component />
    </AdminLayout>
  );
}

function Router() {
  return (
    <Switch>
      <Route path="/auth" component={AuthPage} />
      <Route path="/onboarding">
        {() => <AuthenticatedRoute component={OnboardingPage} />}
      </Route>
      <Route path="/">
        {() => <AuthenticatedRoute component={OverviewPage} />}
      </Route>
      <Route path="/kpi-board">
        {() => <AuthenticatedRoute component={KPIBoardPage} />}
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
      <Route path="/fundraising">
        {() => <AuthenticatedRoute component={FundraisingPage} />}
      </Route>
      <Route path="/investor-room">
        {() => <AuthenticatedRoute component={InvestorRoomPage} />}
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
      <Route path="/admin/llm-audit">
        {() => <AdminRoute component={AdminLLMAudit} />}
      </Route>
      <Route path="/admin/evals">
        {() => <AdminRoute component={AdminEvals} />}
      </Route>
      <Route path="/owner-console" component={OwnerConsole} />
      <Route component={NotFound} />
    </Switch>
  );
}

function AppLayout({ children }: { children: React.ReactNode }) {
  const { token, currentCompany, truthScan, currentStep, currentScenario, latestRun } = useFounderStore();
  const confidence = truthScan?.data_confidence_score || 0;
  
  const style = {
    "--sidebar-width": "16rem",
    "--sidebar-width-icon": "3rem",
  };
  
  // Check if we're on a standalone page (owner console, auth, onboarding, admin)
  const isStandalonePage = typeof window !== 'undefined' && 
    (window.location.pathname === '/owner-console' || 
     window.location.pathname === '/auth' ||
     window.location.pathname === '/onboarding' ||
     window.location.pathname.startsWith('/admin'));
  
  if (!token || isStandalonePage) {
    return <>{children}</>;
  }
  
  const getConfidenceBadge = () => {
    if (!truthScan) return null;
    if (confidence < 60) {
      return <Badge variant="destructive" className="text-xs">Confidence: {confidence}</Badge>;
    } else if (confidence < 80) {
      return <Badge className="bg-amber-500/20 text-amber-400 text-xs">Confidence: {confidence}</Badge>;
    }
    return <Badge className="bg-emerald-500/20 text-emerald-400 text-xs">Confidence: {confidence}</Badge>;
  };

  return (
    <SidebarProvider style={style as React.CSSProperties}>
      <div className="flex h-screen w-full">
        <AppSidebar />
        <div className="flex flex-col flex-1 overflow-hidden">
          <header className="flex items-center justify-between gap-4 p-3 border-b bg-background sticky top-0 z-50">
            <div className="flex items-center gap-4">
              <SidebarTrigger data-testid="button-sidebar-toggle" />
              {currentCompany && <Stepper currentStep={currentStep} />}
            </div>
            <div className="flex items-center gap-2">
              <ContextBar 
                scenarioName={currentScenario?.name}
                scenarioId={currentScenario?.id}
                runId={latestRun?.id}
                runTimestamp={latestRun?.timestamp}
              />
              {getConfidenceBadge()}
            </div>
          </header>
          <main className="flex-1 overflow-auto bg-background">
            {children}
          </main>
        </div>
      </div>
    </SidebarProvider>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="dark" storageKey="predixen-theme">
        <TooltipProvider>
          <AppLayout>
            <Router />
          </AppLayout>
          <Toaster />
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
