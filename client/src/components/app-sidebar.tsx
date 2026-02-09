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
  DollarSign,
  Search,
  BookOpen,
  Flag,
  Settings,
  LogOut,
  HelpCircle,
  Sparkles,
  Upload,
  Link2,
  Store,
  FileCode,
  LayoutGrid,
  Briefcase,
  Activity,
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
} from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { useFounderStore } from "@/store/founderStore";
import { CompanySwitcher } from "@/components/CompanySwitcher";
import predixenLogo from "@assets/generated_images/predixen_fintech_logo_icon.png";
import { cn } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";

interface SettingsNavItem {
  title: string;
  url: string;
  icon: React.ComponentType<{ className?: string }>;
}

const settingsGroups: { label: string; items: SettingsNavItem[] }[] = [
  {
    label: "Data & Setup",
    items: [
      { title: "Data Input", url: "/data", icon: Upload },
      { title: "Integrations", url: "/integrations", icon: Link2 },
    ],
  },
  {
    label: "Metrics",
    items: [
      { title: "Metric Catalog", url: "/metrics", icon: FileCode },
      { title: "Suggested Metrics", url: "/suggested-metrics", icon: Sparkles },
      { title: "KPI Dashboards", url: "/dashboards", icon: LayoutGrid },
    ],
  },
  {
    label: "Stakeholders",
    items: [
      { title: "Investor Room", url: "/investor-room", icon: Briefcase },
      { title: "KPI Board", url: "/kpi-board", icon: Activity },
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

function HealthScoreCard() {
  const { truthScan } = useFounderStore();
  const confidence = truthScan?.data_confidence_score || 0;
  const qualityIndex = truthScan?.quality_of_growth_index || 0;
  const healthScore = qualityIndex > 0 ? Math.min(Math.round(qualityIndex), 100) : (confidence > 0 ? Math.round(confidence * 0.8 + 15) : 73);

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
        <span className={cn("text-sm font-bold font-mono", getHealthColor(healthScore))} data-testid="text-health-score">
          {healthScore}/100
        </span>
      </div>
      <Progress
        value={healthScore}
        className={cn("h-1.5 bg-muted/40", getProgressColor(healthScore))}
      />
      <div className="flex items-center justify-between gap-2 mt-2">
        <span className="text-[11px] text-muted-foreground">Data Confidence</span>
        <span className="text-[11px] font-medium text-muted-foreground font-mono" data-testid="text-data-confidence">
          {confidence > 0 ? `${confidence}%` : "60%"}
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
          <span className="flex-1 text-left">Settings</span>
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
                onClick={() => {
                  localStorage.removeItem('predixen-token');
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
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
      });
      if (!res.ok) return [];
      const data = await res.json();
      return Array.isArray(data) ? data : (data.decisions || []);
    },
    enabled: !!currentCompany?.id,
  });

  const scenarioCount = scenarios?.length ?? 0;
  const pendingDecisionCount = decisions?.filter((d: any) => d.status === "pending" || d.status === "open")?.length ?? 0;

  return (
    <Sidebar>
      <SidebarHeader className="p-4">
        <div className="flex items-center gap-3">
          <img
            src={predixenLogo}
            alt="Predixen"
            className="h-9 w-9 rounded-md"
          />
          <div>
            <h1 className="font-semibold text-sm">Predixen</h1>
            <p className="text-xs text-muted-foreground">Intelligence OS</p>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent className="px-2">
        <div className="px-2 py-2 mb-1">
          <p className="text-xs text-muted-foreground mb-2 px-2">Company</p>
          <CompanySwitcher />
        </div>

        {/* AI Copilot - Gradient Button */}
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

        {/* Health Score Card */}
        <HealthScoreCard />

        <div className="h-px bg-border/50 mx-3 my-3" />

        {/* Core Section */}
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
                  <Link href="/">
                    <LayoutDashboard className="h-4 w-4" />
                    <span>Dashboard</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={location === "/scenarios" || location.startsWith("/scenarios/")}
                  data-testid="nav-simulate"
                >
                  <Link href="/scenarios">
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
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Finance Section */}
        <SidebarGroup className="py-0 mt-2">
          <SidebarGroupLabel className="px-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Finance
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={location === "/fundraising"}
                  data-testid="nav-fundraising"
                >
                  <Link href="/fundraising">
                    <DollarSign className="h-4 w-4" />
                    <span>Fundraising</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={location === "/truth" || location === "/truth-scan"}
                  data-testid="nav-health-check"
                >
                  <Link href="/truth">
                    <Search className="h-4 w-4" />
                    <span>Health Check</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Track Section */}
        <SidebarGroup className="py-0 mt-2">
          <SidebarGroupLabel className="px-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Track
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={location === "/journal"}
                  data-testid="nav-journal"
                >
                  <Link href="/journal">
                    <BookOpen className="h-4 w-4" />
                    <span className="flex-1">Decision Journal</span>
                    <Badge variant="secondary" className="ml-auto text-[10px] px-1.5 py-0 h-4 bg-primary/15 text-primary border-0">
                      New
                    </Badge>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={location === "/goals"}
                  data-testid="nav-goals"
                >
                  <Link href="/goals">
                    <Flag className="h-4 w-4" />
                    <span className="flex-1">Goals</span>
                    <Badge variant="secondary" className="ml-auto text-[10px] px-1.5 py-0 h-4 bg-primary/15 text-primary border-0">
                      New
                    </Badge>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-3 space-y-1">
        <div className="flex items-center justify-between gap-2 px-2 mb-1">
          <span className="text-xs text-muted-foreground">Theme</span>
          <ThemeToggle />
        </div>
        <SettingsDrawer />
        <Link href="/docs">
          <div
            className="flex items-center gap-2 text-sm text-muted-foreground px-2 py-1.5 rounded-md hover-elevate cursor-pointer"
            data-testid="link-help-docs"
          >
            <HelpCircle className="h-4 w-4" />
            <span>Help & Docs</span>
          </div>
        </Link>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start"
          onClick={() => {
            localStorage.removeItem('predixen-token');
            useFounderStore.getState().logout();
            window.location.href = '/auth';
          }}
          data-testid="button-logout"
        >
          <LogOut className="h-4 w-4 mr-2" />
          Sign Out
        </Button>
      </SidebarFooter>
    </Sidebar>
  );
}
