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
  Zap,
  Upload,
} from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { useFounderStore } from "@/store/founderStore";
import { CompanySwitcher } from "@/components/CompanySwitcher";

const menuItems = [
  {
    title: "Overview",
    url: "/",
    icon: LayoutDashboard,
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
    title: "Decisions",
    url: "/decisions",
    icon: Lightbulb,
  },
  {
    title: "Copilot",
    url: "/copilot",
    icon: Sparkles,
  },
];

export function AppSidebar() {
  const [location] = useLocation();
  const { currentCompany, logout } = useFounderStore();

  const handleLogout = () => {
    localStorage.removeItem('predixen-token');
    logout();
    window.location.href = '/auth';
  };

  return (
    <Sidebar>
      <SidebarHeader className="p-4">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-md bg-primary">
            <Zap className="h-5 w-5 text-primary-foreground" />
          </div>
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
      </SidebarContent>
      <SidebarFooter className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">Theme</span>
          <ThemeToggle />
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
