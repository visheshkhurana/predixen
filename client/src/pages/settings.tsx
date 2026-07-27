import { useState } from 'react';
import { useLocation } from 'wouter';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { useFounderStore } from '@/store/founderStore';
import { apiRequest } from '@/lib/queryClient';
import { Settings, Lock, Mail, Bell, LogOut, Loader2, User, Shield, Check } from 'lucide-react';
import { FadeIn } from '@/components/ui/motion-primitives';

export default function SettingsPage() {
  const { user, logout } = useFounderStore();
  const [, setLocation] = useLocation();
  const { toast } = useToast();

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  const [emailSimulations, setEmailSimulations] = useState(true);
  const [emailDocuments, setEmailDocuments] = useState(true);
  const [emailDecisions, setEmailDecisions] = useState(true);
  const [emailAlerts, setEmailAlerts] = useState(true);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      toast({ title: 'Passwords do not match', variant: 'destructive' });
      return;
    }
    if (newPassword.length < 8) {
      toast({ title: 'Password must be at least 8 characters', variant: 'destructive' });
      return;
    }
    setIsChangingPassword(true);
    try {
      await apiRequest('POST', '/api/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      toast({ title: 'Password updated', description: 'Your password has been changed successfully.' });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch {
      toast({ title: 'Failed to update password', description: 'Check your current password and try again.', variant: 'destructive' });
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleLogout = async () => {
    try { await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }); } catch {}
    logout();
    window.location.href = '/auth';
  };

  return (
    <FadeIn delay={0.05} duration={0.4}>
    <div className="p-4 md:p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight" data-testid="text-settings-title">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage your account preferences and security</p>
      </div>

      <Card data-testid="card-profile">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <User className="h-5 w-5" />
            Profile
          </CardTitle>
          <CardDescription>Your account information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center text-2xl font-semibold text-primary" data-testid="display-avatar">
              {user?.email?.charAt(0)?.toUpperCase() || 'U'}
            </div>
            <div className="space-y-1">
              <p className="font-medium" data-testid="text-user-email">{user?.email || 'No email'}</p>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-xs" data-testid="badge-user-role">
                  {user?.role || 'Member'}
                </Badge>
                {user?.is_email_verified && (
                  <Badge variant="outline" className="text-xs text-emerald-500 border-emerald-500/30">
                    <Check className="h-3 w-3 mr-1" />
                    Verified
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card data-testid="card-password">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Lock className="h-5 w-5" />
            Change Password
          </CardTitle>
          <CardDescription>Update your account password</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleChangePassword} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="currentPassword">Current Password</Label>
              <Input
                id="currentPassword"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                data-testid="input-current-password"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="newPassword">New Password</Label>
              <Input
                id="newPassword"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                data-testid="input-new-password"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm New Password</Label>
              <Input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                data-testid="input-confirm-password"
              />
            </div>
            <Button type="submit" disabled={isChangingPassword || !currentPassword || !newPassword} data-testid="button-change-password">
              {isChangingPassword && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              Update Password
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card data-testid="card-email-preferences">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Email Preferences
          </CardTitle>
          <CardDescription>Choose which emails you'd like to receive</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <p className="text-sm font-medium">Simulation Reports</p>
              <p className="text-xs text-muted-foreground">Get emailed when Monte Carlo simulations complete</p>
            </div>
            <Switch checked={emailSimulations} onCheckedChange={setEmailSimulations} data-testid="switch-email-simulations" />
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <p className="text-sm font-medium">Document Generation</p>
              <p className="text-xs text-muted-foreground">Receive generated board decks and investor memos</p>
            </div>
            <Switch checked={emailDocuments} onCheckedChange={setEmailDocuments} data-testid="switch-email-documents" />
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <p className="text-sm font-medium">Decision Recommendations</p>
              <p className="text-xs text-muted-foreground">Get notified about new strategic recommendations</p>
            </div>
            <Switch checked={emailDecisions} onCheckedChange={setEmailDecisions} data-testid="switch-email-decisions" />
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <p className="text-sm font-medium">Alert Notifications</p>
              <p className="text-xs text-muted-foreground">Email alerts when critical thresholds are breached</p>
            </div>
            <Switch checked={emailAlerts} onCheckedChange={setEmailAlerts} data-testid="switch-email-alerts" />
          </div>
        </CardContent>
      </Card>

      <Card data-testid="card-security">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Security
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <p className="text-sm font-medium">Active Sessions</p>
              <p className="text-xs text-muted-foreground">You are currently signed in</p>
            </div>
            <Badge variant="outline" className="text-emerald-500 border-emerald-500/30 text-xs">Active</Badge>
          </div>
        </CardContent>
      </Card>

      <Card className="border-destructive/20" data-testid="card-danger-zone">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <p className="text-sm font-medium text-destructive">Sign Out</p>
              <p className="text-xs text-muted-foreground">Sign out of your account on this device</p>
            </div>
            <Button variant="destructive" size="sm" onClick={handleLogout} data-testid="button-logout">
              <LogOut className="h-4 w-4 mr-2" />
              Sign Out
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
    </FadeIn>
  );
}
