import { Link, useLocation } from "wouter";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
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
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
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
  Store,
  LayoutGrid,
  ChevronDown,
  FileCode,
} from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { useFounderStore } from "@/store/founderStore";
import { CompanySwitcher } from "@/components/CompanySwitcher";
import predixenLogo from "@assets/generated_images/predixen_fintech_logo_icon.png";
import { cn } from "@/lib/utils";

interface NavItem {
  title: string;
  url: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface NavGroup {
  label: string;
  items: NavItem[];
  defaultOpen?: boolean;
}

const navGroups: NavGroup[] = [
  {
    label: "Analytics",
    defaultOpen: true,
    items: [
      { title: "Overview", url: "/", icon: LayoutDashboard },
      { title: "KPI Board", url: "/kpi-board", icon: Activity },
      { title: "Metric Catalog", url: "/metrics", icon: FileCode },
      { title: "Truth Scan", url: "/truth", icon: Search },
      { title: "Alerts", url: "/alerts", icon: Bell },
    ],
  },
  {
    label: "Data & Setup",
    defaultOpen: true,
    items: [
      { title: "Data Input", url: "/data", icon: Upload },
      { title: "Integrations", url: "/integrations", icon: Link2 },
      { title: "Marketplace", url: "/marketplace", icon: Store },
    ],
  },
  {
    label: "Planning",
    defaultOpen: true,
    items: [
      { title: "Simulation", url: "/scenarios", icon: TrendingUp },
      { title: "Templates", url: "/templates", icon: Layers },
      { title: "Decisions", url: "/decisions", icon: Lightbulb },
    ],
  },
  {
    label: "Stakeholders",
    defaultOpen: true,
    items: [
      { title: "Fundraising", url: "/fundraising", icon: DollarSign },
      { title: "KPI Dashboards", url: "/dashboards", icon: LayoutGrid },
      { title: "Investor Room", url: "/investor-room", icon: Briefcase },
    ],
  },
];

const adminMenuItems: NavItem[] = [
  { title: "Dashboard", url: "/admin", icon: Shield },
  { title: "Users", url: "/admin/users", icon: Users },
  { title: "Invitations", url: "/admin/invites", icon: Mail },
  { title: "Login History", url: "/admin/login-history", icon: History },
  { title: "Activity Logs", url: "/admin/activity", icon: FileText },
  { title: "Companies", url: "/admin/companies", icon: Building2 },
  { title: "Billing", url: "/admin/billing", icon: CreditCard },
  { title: "Metrics", url: "/admin/metrics", icon: BarChart3 },
];

function NavGroupSection({ group, location }: { group: NavGroup; location: string }) {
  const [isOpen, setIsOpen] = useState(group.defaultOpen ?? true);
  const hasActiveItem = group.items.some(item => item.url === location);
  
  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <SidebarGroup className="py-0">
        <CollapsibleTrigger className="w-full">
          <SidebarGroupLabel 
            className={cn(
              "flex items-center justify-between cursor-pointer rounded-md transition-colors px-2 py-1.5 hover-elevate",
              hasActiveItem && "text-sidebar-accent-foreground"
            )}
          >
            <span>{group.label}</span>
            <ChevronDown 
              className={cn(
                "h-4 w-4 text-muted-foreground transition-transform duration-200",
                isOpen && "rotate-180"
              )} 
            />
          </SidebarGroupLabel>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <SidebarGroupContent>
            <SidebarMenu>
              {group.items.map((item) => (
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
        </CollapsibleContent>
      </SidebarGroup>
    </Collapsible>
  );
}

export function AppSidebar() {
  const [location] = useLocation();
  const { currentCompany, logout, isAdmin } = useFounderStore();
  const showAdmin = isAdmin();
  const [adminOpen, setAdminOpen] = useState(true);

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
      <SidebarContent className="px-2">
        <div className="px-2 py-2 mb-1">
          <p className="text-xs text-muted-foreground mb-2 px-2">Company</p>
          <CompanySwitcher />
        </div>
        
        {/* AI Copilot - Prominent at top */}
        <SidebarGroup className="py-1">
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={location === "/copilot"}
                  className="bg-primary/10 border border-primary/20"
                  data-testid="nav-copilot"
                >
                  <Link href="/copilot">
                    <Sparkles className="h-4 w-4 text-primary" />
                    <span className="font-medium">AI Copilot</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <div className="h-px bg-border/50 mx-2 my-2" />

        {/* Navigation Groups */}
        <div className="space-y-1">
          {navGroups.map((group) => (
            <NavGroupSection key={group.label} group={group} location={location} />
          ))}
        </div>

        {/* Admin Section */}
        {showAdmin && (
          <>
            <div className="h-px bg-border/50 mx-2 my-2" />
            <Collapsible open={adminOpen} onOpenChange={setAdminOpen}>
              <SidebarGroup className="py-0">
                <CollapsibleTrigger className="w-full">
                  <SidebarGroupLabel className="flex items-center justify-between cursor-pointer rounded-md transition-colors px-2 py-1.5 hover-elevate">
                    <span className="flex items-center gap-2">
                      <Shield className="h-3.5 w-3.5" />
                      Admin
                    </span>
                    <ChevronDown 
                      className={cn(
                        "h-4 w-4 text-muted-foreground transition-transform duration-200",
                        adminOpen && "rotate-180"
                      )} 
                    />
                  </SidebarGroupLabel>
                </CollapsibleTrigger>
                <CollapsibleContent>
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
                </CollapsibleContent>
              </SidebarGroup>
            </Collapsible>
          </>
        )}
      </SidebarContent>
      <SidebarFooter className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">Theme</span>
          <ThemeToggle />
        </div>
        <div
          className="flex items-center gap-2 text-sm text-muted-foreground px-2 py-1.5 rounded-md opacity-50 cursor-not-allowed"
          data-testid="link-help-docs"
          title="Documentation coming soon"
        >
          <HelpCircle className="h-4 w-4" />
          <span className="flex-1">Help & Docs</span>
          <Badge variant="outline" className="text-[10px] px-1 py-0">Soon</Badge>
        </div>
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
