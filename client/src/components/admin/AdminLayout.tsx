import { Link, useLocation } from 'wouter';
import { useFounderStore } from '@/store/founderStore';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { 
  LayoutDashboard, Users, UsersRound, Mail, Activity, BarChart3, 
  Building2, CreditCard, LogOut, ChevronRight,
  Menu, X, FileText, Shield, FlaskConical, Brain, Send, MessageSquare
} from 'lucide-react';
import { useState } from 'react';
import { ThemeToggle } from '@/components/theme-toggle';
import predixenLogo from "@assets/generated_images/predixen_fintech_logo_icon.png";

interface NavItem {
  title: string;
  href: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { title: 'Dashboard', href: '/admin', icon: LayoutDashboard },
  { title: 'Users', href: '/admin/users', icon: Users },
  { title: 'Invitations', href: '/admin/invites', icon: Mail },
  { title: 'Email Templates', href: '/admin/email-templates', icon: FileText },
  { title: 'Email Tracking', href: '/admin/email-tracking', icon: Send },
  { title: 'Companies', href: '/admin/companies', icon: Building2 },
  { title: 'Team', href: '/admin/team', icon: UsersRound },
  { title: 'Billing', href: '/admin/billing', icon: CreditCard },
  { title: 'Metrics', href: '/admin/metrics', icon: BarChart3 },
  { title: 'Login History', href: '/admin/login-history', icon: Activity },
  { title: 'LLM Audit', href: '/admin/llm-audit', icon: Shield },
  { title: 'Evaluations', href: '/admin/evals', icon: FlaskConical },
  { title: 'AI Governance', href: '/admin/ai-governance', icon: Brain },
  { title: 'Messaging', href: '/admin/messaging', icon: MessageSquare },
];

export function AdminLayout({ children }: { children: React.ReactNode }) {
  const [location, setLocation] = useLocation();
  const { user, logout } = useFounderStore();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleLogout = () => {
    localStorage.removeItem('predixen-admin-session');
    logout();
    setLocation('/admin/login');
  };

  return (
    <div className="flex h-screen bg-background">
      <aside 
        className={`${sidebarOpen ? 'w-64' : 'w-16'} transition-all duration-300 border-r border-border bg-card flex flex-col`}
      >
        <div className="h-16 flex items-center justify-between px-4 border-b border-border">
          {sidebarOpen && (
            <div className="flex items-center gap-2">
              <img 
                src={predixenLogo} 
                alt="Predixen" 
                className="h-8 w-8 rounded-lg"
              />
              <span className="font-semibold text-sm">Admin Console</span>
            </div>
          )}
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={() => setSidebarOpen(!sidebarOpen)}
            data-testid="button-toggle-sidebar"
          >
            {sidebarOpen ? <ChevronRight className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </Button>
        </div>

        <ScrollArea className="flex-1 py-4">
          <nav className="space-y-1 px-2">
            {navItems.map((item) => {
              const isActive = location === item.href || 
                (item.href !== '/admin' && location.startsWith(item.href));
              
              return (
                <Link key={item.href} href={item.href}>
                  <div
                    className={`flex items-center gap-3 px-3 py-2 rounded-md transition-colors cursor-pointer
                      ${isActive 
                        ? 'bg-primary text-primary-foreground' 
                        : 'hover-elevate text-muted-foreground hover:text-foreground'
                      }`}
                    data-testid={`nav-${item.title.toLowerCase().replace(/\s/g, '-')}`}
                  >
                    <item.icon className="h-4 w-4 flex-shrink-0" />
                    {sidebarOpen && <span className="text-sm">{item.title}</span>}
                  </div>
                </Link>
              );
            })}
          </nav>
        </ScrollArea>

        <div className="border-t border-border p-4">
          {sidebarOpen ? (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-primary/10 text-primary text-xs">
                    {user?.email?.charAt(0).toUpperCase() || 'A'}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{user?.email || 'Admin'}</p>
                  <p className="text-xs text-muted-foreground capitalize">{user?.role || 'Owner'}</p>
                </div>
              </div>
              <Button 
                variant="outline" 
                size="sm" 
                className="w-full justify-start gap-2"
                onClick={handleLogout}
                data-testid="button-admin-logout"
              >
                <LogOut className="h-4 w-4" />
                Sign Out
              </Button>
            </div>
          ) : (
            <Button 
              variant="ghost" 
              size="icon"
              onClick={handleLogout}
              data-testid="button-admin-logout-icon"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          )}
        </div>
      </aside>

      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 border-b border-border flex items-center justify-between px-6 bg-card">
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold">Predixen Admin</h1>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
          </div>
        </header>

        <main className="flex-1 overflow-auto p-6 bg-background">
          {children}
        </main>
      </div>
    </div>
  );
}
