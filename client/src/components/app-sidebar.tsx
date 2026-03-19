import { Link, useLocation } from "wouter";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
} from "@/components/ui/sidebar";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  LayoutDashboard,
  FlaskConical,
  Target,
  Settings,
  LogOut,
  HelpCircle,
  Sparkles,
  Upload,
  Link2,
  FileCode,
  LayoutGrid,
  Shield,
  Users,
  Building2,
  CreditCard,
  BarChart3,
  History,
  FileText,
  Mail,
  UsersRound,
  Command,
  ChevronRight,
  AlertTriangle,
  Database,
  Activity,
  Briefcase,
  Flag,
  BookOpen,
  Brain,
  Plug,
} from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { useFounderStore } from "@/store/founderStore";
import { CompanySwitcher } from "@/components/CompanySwitcher";
import founderconsoleLogo from "@assets/image_1773944058788.png";
import { cn } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";

interface SettingsNavItem {
  title: string;
  url: string;
  icon: React.ComponentType<{ className?: string }>;
}

const settingsGroups: { label: string; items: SettingsNavItem[] }[] = [
  {
    label: "Tools",
    items: [
      { title: "Marketplace", url: "/marketplace", icon: Database },
      { title: "Doc Generator", url: "/doc-generator", icon: FileText },
    ],
  },
  {
    label: "Track",
    items: [
      { title: "Journal", url: "/journal", icon: BookOpen },
      { title: "Goals", url: "/goals", icon: Flag },
    ],
  },
];

const adminSettingsItems: SettingsNavItem[] = [
  { title: "Dashboard", url: "/admin", icon: Shield },
  { title: "Users", url: "/admin/users", icon: Users },
  { title: "Invitations", url: "/admin/invites", icon: Mail },
  { title: "Login History", url: "/admin/login-history", icon: History },
  { title: "Activity Logs", url: "/admin/activity", icon: FileText },
  { title: "Companies", url: "/admin/companies", icon: Building2 },
  { title: "Team", url: "/admin/team", icon: UsersRound },
  { title: "Billing", url: "/admin/billing", icon: CreditCard },
  { title: "Metrics", url: "/admin/metrics", icon: BarChart3 },
];

const NON_DATA_PATHS = ["/docs", "/help", "/privacy", "/terms", "/integrations", "/settings"];

function HealthScoreCard() {
  const [location] = useLocation();
  const { truthScan } = useFounderStore();
  const confidence = truthScan?.data_confidence_score ?? 0;
  const qualityIndex = truthScan?.quality_of_growth_index ?? 0;
  const hasData = truthScan != null;
  const healthScore = hasData
    ? (qualityIndex > 0 ? Math.min(Math.round(qualityIndex), 100) : 0)
    : null;

  const isNonDataPage = NON_DATA_PATHS.some((p) => location.startsWith(p));
  if (!hasData || isNonDataPage) return null;

  const getHealthColor = (score: number) => {
    if (score >= 70) return "text-emerald-400";
    if (score >= 50) return "text-amber-400";
    return "text-red-400";
  };

  const getProgressColor = (score: number) => {
    if (score >= 70) return "[&>div]:bg-emerald-500";
    if (score >= 50) return "[&>div]:bg-amber-500";
    return "[&>div]:bg-red-500";
  };

  return (
    <div
      className="mx-3 rounded-md p-3 border border-primary/20"
      style={{ background: "linear-gradient(135deg, hsl(217 91% 60% / 0.08), hsl(271 81% 56% / 0.08))" }}
    >
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <span className="text-xs font-medium text-muted-foreground">Business Health</span>
        <span className={cn("text-sm font-bold font-mono", healthScore !== null ? getHealthColor(healthScore) : "text-muted-foreground")} data-testid="text-health-score">
          {healthScore !== null ? `${healthScore}/100` : "N/A"}
        </span>
      </div>
      <Progress
        value={healthScore ?? 0}
        className={cn("h-1.5 bg-muted/40", healthScore !== null ? getProgressColor(healthScore) : "")}
      />
      <div className="flex items-center justify-between gap-2 mt-2">
        <span className="text-[11px] text-muted-foreground">Data Confidence</span>
        <span className="text-[11px] font-medium text-muted-foreground font-mono" data-testid="text-data-confidence">
          {hasData ? `${confidence}%` : "N/A"}
        </span>
      </div>
    </div>
  );
}

function SettingsDrawer() {
  const [location, setLocation] = useLocation();
  const [open, setOpen] = useState(false);
  const { isAdmin, logout } = useFounderStore();
  const showAdmin = isAdmin();

  const handleNavigate = (url: string) => {
    setLocation(url);
    setOpen(false);
  };

  const isActive = (url: string) => location === url;

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={cn(
            "w-full justify-start gap-2",
            open && "text-foreground"
          )}
          data-testid="button-settings"
        >
          <Settings className="h-4 w-4" />
          <span className="flex-1 text-left">Settings & Tools</span>
          <ChevronRight className="h-3.5 w-3.5" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-80 p-0 overflow-y-auto">
        <SheetHeader className="p-4 pb-2 border-b">
          <SheetTitle className="text-sm font-semibold">Settings & Tools</SheetTitle>
        </SheetHeader>
        <div className="p-2 space-y-4">
          {settingsGroups.map((group) => (
            <div key={group.label}>
              <p className="text-xs font-medium text-muted-foreground px-3 mb-1 uppercase tracking-wider">
                {group.label}
              </p>
              <div className="space-y-0.5">
                {group.items.map((item) => (
                  <Button
                    key={item.url}
                    variant="ghost"
                    size="sm"
                    onClick={() => handleNavigate(item.url)}
                    className={cn(
                      "w-full justify-start gap-2.5",
                      isActive(item.url) && "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                    )}
                    data-testid={`settings-nav-${item.title.toLowerCase().replace(/\s/g, "-")}`}
                  >
                    <item.icon className="h-4 w-4 shrink-0" />
                    <span>{item.title}</span>
                  </Button>
                ))}
              </div>
            </div>
          ))}

          {showAdmin && (
            <div>
              <p className="text-xs font-medium text-muted-foreground px-3 mb-1 uppercase tracking-wider">
                Admin
              </p>
              <div className="space-y-0.5">
                {adminSettingsItems.map((item) => (
                  <Button
                    key={item.url}
                    variant="ghost"
                    size="sm"
                    onClick={() => handleNavigate(item.url)}
                    className={cn(
                      "w-full justify-start gap-2.5",
                      isActive(item.url) && "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                    )}
                    data-testid={`settings-nav-admin-${item.title.toLowerCase().replace(/\s/g, "-")}`}
                  >
                    <item.icon className="h-4 w-4 shrink-0" />
                    <span>{item.title}</span>
                  </Button>
                ))}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleNavigate("/qa")}
                  className={cn(
                    "w-full justify-start gap-2.5",
                    isActive("/qa") && "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                  )}
                  data-testid="settings-nav-admin-qa-front"
                >
                  <Activity className="h-4 w-4 shrink-0" />
                  <span>QA Front</span>
                </Button>
              </div>
            </div>
          )}

          <div className="border-t pt-3 mt-2">
            <p className="text-xs font-medium text-muted-foreground px-3 mb-1 uppercase tracking-wider">
              Support
            </p>
            <div className="space-y-0.5">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleNavigate("/docs")}
                className={cn(
                  "w-full justify-start gap-2.5",
                  isActive("/docs") && "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                )}
                data-testid="settings-nav-help-docs"
              >
                <HelpCircle className="h-4 w-4 shrink-0" />
                <span>Help & Docs</span>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={async () => {
                  try { await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }); } catch {}
                  logout();
                  window.location.href = '/auth';
                }}
                className="w-full justify-start gap-2.5 text-destructive"
                data-testid="settings-nav-sign-out"
              >
                <LogOut className="h-4 w-4 shrink-0" />
                <span>Sign Out</span>
              </Button>
            </div>
          </div>

          <div className="border-t pt-3 mt-2">
            <p className="text-xs font-medium text-muted-foreground px-3 mb-1 uppercase tracking-wider">
              Legal
            </p>
            <div className="space-y-0.5">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleNavigate("/privacy")}
                className={cn(
                  "w-full justify-start gap-2.5",
                  isActive("/privacy") && "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                )}
                data-testid="settings-nav-privacy"
              >
                <Shield className="h-4 w-4 shrink-0" />
                <span>Privacy Policy</span>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleNavigate("/terms")}
                className={cn(
                  "w-full justify-start gap-2.5",
                  isActive("/terms") && "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                )}
                data-testid="settings-nav-terms"
              >
                <FileText className="h-4 w-4 shrink-0" />
                <span>Terms of Service</span>
              </Button>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

export function AppSidebar() {
  const [location] = useLocation();
  const { currentCompany } = useFounderStore();

  const { data: scenarios } = useQuery<any[]>({
    queryKey: ["/api/scenarios"],
    enabled: !!currentCompany?.id,
  });

  const { data: decisions } = useQuery<any[]>({
    queryKey: ["/api/companies", currentCompany?.id, "decisions"],
    queryFn: async () => {
      if (!currentCompany?.id) return [];
      const res = await fetch(`/api/companies/${currentCompany.id}/decisions`, {
        credentials: 'include',
      });
      if (!res.ok) return [];
      const data = await res.json();
      return Array.isArray(data) ? data : (data.decisions || []);
    },
    enabled: !!currentCompany?.id,
  });

  const { data: smartAlertsData } = useQuery<{ alerts: any[]; total: number; unacknowledged: number }>({
    queryKey: ["/api/companies", currentCompany?.id, "smart-alerts"],
    enabled: !!currentCompany?.id,
  });

  const unreadAlertCount = smartAlertsData?.unacknowledged ?? smartAlertsData?.alerts?.filter((a: any) => !a.acknowledged)?.length ?? 0;

  const scenarioCount = scenarios?.length ?? 0;
  const pendingDecisionCount = decisions?.filter((d: any) => d.status === "pending" || d.status === "open")?.length ?? 0;

  return (
    <Sidebar>
      <SidebarHeader className="p-4">
        <div className="flex items-center gap-3">
          <img
            src={founderconsoleLogo}
            alt="FounderConsole"
            className="h-9 w-9 rounded-md"
          />
          <div>
            <span className="font-semibold text-sm">FounderConsole</span>
            <p className="text-xs text-muted-foreground">Intelligence OS</p>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent className="px-2 overflow-y-auto">
        <div className="px-2 py-2 mb-1">
          <p className="text-xs text-muted-foreground mb-2 px-2">Company</p>
          <CompanySwitcher />
        </div>

        <div className="px-3 mb-2">
          <Link href="/copilot">
            <Button
              variant="default"
              size="sm"
              className={cn(
                "w-full justify-start gap-2.5 text-white border border-white/10",
                location === "/copilot" && "ring-1 ring-white/30"
              )}
              style={{
                background: "linear-gradient(135deg, hsl(217 91% 55%), hsl(271 81% 50%))",
              }}
              data-testid="nav-copilot"
            >
              <Sparkles className="h-4 w-4" />
              <span className="flex-1 text-left">AI Copilot</span>
              <span
                className="flex items-center gap-0.5 text-[10px] font-mono bg-white/15 px-1.5 py-0.5 rounded"
              >
                <Command className="h-2.5 w-2.5" />K
              </span>
            </Button>
          </Link>
        </div>

        <HealthScoreCard />

        <div className="h-px bg-border/50 mx-3 my-2" />

        <SidebarGroup className="py-0">
          <SidebarGroupLabel className="px-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Core
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={location === "/" || location === "/overview"}
                  data-testid="nav-dashboard"
                >
                  <Link href="/overview">
                    <LayoutDashboard className="h-4 w-4" />
                    <span>Dashboard</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={location === "/simulate" || location === "/scenarios" || location.startsWith("/scenarios/")}
                  data-testid="nav-simulate"
                >
                  <Link href="/simulate">
                    <FlaskConical className="h-4 w-4" />
                    <span className="flex-1">Simulate</span>
                    {scenarioCount > 0 && (
                      <Badge variant="secondary" className="ml-auto text-[10px] px-1.5 py-0 h-4 bg-primary/15 text-primary border-0" data-testid="badge-scenario-count">
                        {scenarioCount}
                      </Badge>
                    )}
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={location === "/decisions"}
                  data-testid="nav-decisions"
                >
                  <Link href="/decisions">
                    <Target className="h-4 w-4" />
                    <span className="flex-1">Decisions</span>
                    {pendingDecisionCount > 0 && (
                      <Badge variant="destructive" className="ml-auto text-[10px] px-1.5 py-0 h-4 border-0" data-testid="badge-decision-count">
                        {pendingDecisionCount}
                      </Badge>
                    )}
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={location === "/alerts"}
                  data-testid="nav-alerts"
                >
                  <Link href="/alerts">
                    <AlertTriangle className="h-4 w-4" />
                    <span className="flex-1">Alerts</span>
                    {unreadAlertCount > 0 && (
                      <Badge variant="destructive" className="ml-auto text-[10px] px-1.5 py-0 h-4 border-0" data-testid="badge-alert-count">
                        {unreadAlertCount}
                      </Badge>
                    )}
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="py-0">
          <SidebarGroupLabel className="px-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Finance
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={location === "/cap-table"}
                  data-testid="nav-cap-table"
                >
                  <Link href="/cap-table">
                    <BarChart3 className="h-4 w-4" />
                    <span>Cap Table</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={location === "/fundraising"}
                  data-testid="nav-fundraising"
                >
                  <Link href="/fundraising">
                    <CreditCard className="h-4 w-4" />
                    <span>Fundraising</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={location === "/investor-room"}
                  data-testid="nav-investor-room"
                >
                  <Link href="/investor-room">
                    <Briefcase className="h-4 w-4" />
                    <span>Investor Room</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={location === "/hiring-planner"}
                  data-testid="nav-hiring-planner"
                >
                  <Link href="/hiring-planner">
                    <UsersRound className="h-4 w-4" />
                    <span>Hiring Planner</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="py-0">
          <SidebarGroupLabel className="px-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Intelligence
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={location === "/digital-twin"}
                  data-testid="nav-digital-twin"
                >
                  <Link href="/digital-twin">
                    <Brain className="h-4 w-4" />
                    <span>Digital Twin</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={location === "/metrics" || location === "/dashboards" || location.startsWith("/dashboards/")}
                  data-testid="nav-metrics"
                >
                  <Link href="/dashboards">
                    <LayoutGrid className="h-4 w-4" />
                    <span>KPI Dashboards</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={location === "/truth"}
                  data-testid="nav-health-check"
                >
                  <Link href="/truth">
                    <Activity className="h-4 w-4" />
                    <span>Health Check</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="py-0">
          <SidebarGroupLabel className="px-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Data
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={location === "/data" || location.startsWith("/data/")}
                  data-testid="nav-data"
                >
                  <Link href="/data">
                    <Upload className="h-4 w-4" />
                    <span>Data Input</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="py-0">
          <SidebarGroupLabel className="px-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Integrations
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={location === "/integrations"}
                  data-testid="nav-integrations"
                >
                  <Link href="/integrations">
                    <Plug className="h-4 w-4" />
                    <span>Integrations</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="px-2 pb-3 space-y-1">
        <SettingsDrawer />
        <div className="flex items-center justify-between px-3 py-1">
          <ThemeToggle />
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
