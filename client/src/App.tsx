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
import { useFounderStore } from "@/store/founderStore";
import AuthPage from "@/pages/auth";
import OnboardingPage from "@/pages/onboarding";
import OverviewPage from "@/pages/overview";
import TruthScanPage from "@/pages/truth-scan";
import ScenariosPage from "@/pages/scenarios";
import DecisionsPage from "@/pages/decisions";
import CopilotPage from "@/pages/copilot";
import DataInputPage from "@/pages/data-input";
import NotFound from "@/pages/not-found";

function AuthenticatedRoute({ component: Component }: { component: React.ComponentType }) {
  const token = useFounderStore((s) => s.token);
  
  if (!token) {
    return <Redirect to="/auth" />;
  }
  
  return <Component />;
}

function Router() {
  return (
    <Switch>
      <Route path="/auth" component={AuthPage} />
      <Route path="/onboarding" component={OnboardingPage} />
      <Route path="/">
        {() => <AuthenticatedRoute component={OverviewPage} />}
      </Route>
      <Route path="/truth">
        {() => <AuthenticatedRoute component={TruthScanPage} />}
      </Route>
      <Route path="/data-input">
        {() => <AuthenticatedRoute component={DataInputPage} />}
      </Route>
      <Route path="/scenarios">
        {() => <AuthenticatedRoute component={ScenariosPage} />}
      </Route>
      <Route path="/decisions">
        {() => <AuthenticatedRoute component={DecisionsPage} />}
      </Route>
      <Route path="/copilot">
        {() => <AuthenticatedRoute component={CopilotPage} />}
      </Route>
      <Route component={NotFound} />
    </Switch>
  );
}

function AppLayout({ children }: { children: React.ReactNode }) {
  const { token, currentCompany, truthScan, currentStep } = useFounderStore();
  const confidence = truthScan?.data_confidence_score || 0;
  
  const style = {
    "--sidebar-width": "16rem",
    "--sidebar-width-icon": "3rem",
  };
  
  if (!token) {
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
