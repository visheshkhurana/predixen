import { Link, useLocation } from "wouter";
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
  LayoutDashboard,
  Search,
  TrendingUp,
  Lightbulb,
  Sparkles,
  LogOut,
  Upload,
  Link2,
  Bell,
  Layers,
  Shield,
  Users,
  Building2,
  CreditCard,
  BarChart3,
  History,
  FileText,
  HelpCircle,
  ExternalLink,
  Mail,
  DollarSign,
  Briefcase,
  Activity,
} from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { useFounderStore } from "@/store/founderStore";
import { CompanySwitcher } from "@/components/CompanySwitcher";
import predixenLogo from "@assets/generated_images/predixen_fintech_logo_icon.png";

const menuItems = [
  {
    title: "Overview",
    url: "/",
    icon: LayoutDashboard,
  },
  {
    title: "KPI Board",
    url: "/kpi-board",
    icon: Activity,
  },
  {
    title: "Data Input",
    url: "/data",
    icon: Upload,
  },
  {
    title: "Truth Scan",
    url: "/truth",
    icon: Search,
  },
  {
    title: "Simulation",
    url: "/scenarios",
    icon: TrendingUp,
  },
  {
    title: "Templates",
    url: "/templates",
    icon: Layers,
  },
  {
    title: "Decisions",
    url: "/decisions",
    icon: Lightbulb,
  },
  {
    title: "Copilot",
    url: "/copilot",
    icon: Sparkles,
  },
  {
    title: "Alerts",
    url: "/alerts",
    icon: Bell,
  },
  {
    title: "Fundraising",
    url: "/fundraising",
    icon: DollarSign,
  },
  {
    title: "Investor Room",
    url: "/investor-room",
    icon: Briefcase,
  },
  {
    title: "Integrations",
    url: "/integrations",
    icon: Link2,
  },
];

const adminMenuItems = [
  {
    title: "Dashboard",
    url: "/admin",
    icon: Shield,
  },
  {
    title: "Users",
    url: "/admin/users",
    icon: Users,
  },
  {
    title: "Invitations",
    url: "/admin/invites",
    icon: Mail,
  },
  {
    title: "Login History",
    url: "/admin/login-history",
    icon: History,
  },
  {
    title: "Activity Logs",
    url: "/admin/activity",
    icon: FileText,
  },
  {
    title: "Companies",
    url: "/admin/companies",
    icon: Building2,
  },
  {
    title: "Billing",
    url: "/admin/billing",
    icon: CreditCard,
  },
  {
    title: "Metrics",
    url: "/admin/metrics",
    icon: BarChart3,
  },
];

export function AppSidebar() {
  const [location] = useLocation();
  const { currentCompany, logout, isAdmin } = useFounderStore();
  const showAdmin = isAdmin();

  const handleLogout = () => {
    localStorage.removeItem('predixen-token');
    logout();
    window.location.href = '/auth';
  };

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
      <SidebarContent>
        <div className="px-4 py-2 mb-2">
          <p className="text-xs text-muted-foreground mb-2">Company</p>
          <CompanySwitcher />
        </div>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {menuItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={location === item.url}
                    data-testid={`nav-${item.title.toLowerCase().replace(/\s/g, "-")}`}
                  >
                    <Link href={item.url}>
                      <item.icon className="h-4 w-4" />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        {showAdmin && (
          <SidebarGroup>
            <SidebarGroupLabel>Admin</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {adminMenuItems.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      asChild
                      isActive={location === item.url || (item.url === "/admin" && location === "/admin")}
                      data-testid={`nav-admin-${item.title.toLowerCase().replace(/\s/g, "-")}`}
                    >
                      <Link href={item.url}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>
      <SidebarFooter className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">Theme</span>
          <ThemeToggle />
        </div>
        <a
          href="https://docs.predixen.com"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors px-2 py-1.5 rounded-md hover-elevate"
          data-testid="link-help-docs"
        >
          <HelpCircle className="h-4 w-4" />
          <span className="flex-1">Help & Docs</span>
          <ExternalLink className="h-3 w-3" />
        </a>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start"
          onClick={handleLogout}
          data-testid="button-logout"
        >
          <LogOut className="h-4 w-4 mr-2" />
          Sign Out
        </Button>
      </SidebarFooter>
    </Sidebar>
  );
}
