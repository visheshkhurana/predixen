import { useState } from 'react';
import { useLocation } from 'wouter';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { useFounderStore } from '@/store/founderStore';
import { apiRequest } from '@/lib/queryClient';
import {
  useNotificationPreferences,
  useUpdateNotificationPreferences,
  useWorkspaceMembers,
  useWorkspaceInvites,
  useInviteMember,
  useUpdateMemberRole,
  useRemoveMember,
  useRevokeInvite,
  useResendInvite,
} from '@/api/workspace';
import { Lock, Bell, LogOut, Loader2, User, Shield, Check, Users } from 'lucide-react';
import { FadeIn } from '@/components/ui/motion-primitives';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { TeamWorkspace } from '@/components/TeamWorkspace';
import {
  canManageTeam,
  inviteCreatedCopy,
  inviteRenewedCopy,
  roleForEmail,
  teamErrorMessage,
} from '@/lib/teamInvites';

type SettingsTab = 'account' | 'team';

function initialTab(): SettingsTab {
  if (typeof window === 'undefined') return 'account';
  return new URLSearchParams(window.location.search).get('tab') === 'team' ? 'team' : 'account';
}

/** Settings → Team: invite teammates to the current company's workspace. */
function TeamSettingsTab() {
  const { user, currentCompany } = useFounderStore();
  const { toast } = useToast();
  const companyId = currentCompany?.id ?? 0;
  const isSample = !!currentCompany?.is_sample;

  const membersQuery = useWorkspaceMembers(isSample ? 0 : companyId);
  const role = roleForEmail(membersQuery.data, user?.email);
  const manager = canManageTeam(role);
  const invitesQuery = useWorkspaceInvites(companyId, { enabled: !isSample && manager });
  const inviteMember = useInviteMember();
  const updateRole = useUpdateMemberRole();
  const removeMember = useRemoveMember();
  const revokeInvite = useRevokeInvite();
  const resendInvite = useResendInvite();

  if (!currentCompany) {
    return (
      <Card data-testid="card-team-no-company">
        <CardContent className="pt-6 text-sm text-muted-foreground">
          Add your company first, then you can invite teammates here.
        </CardContent>
      </Card>
    );
  }

  if (isSample) {
    return (
      <Card data-testid="card-team-sample">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Users className="h-5 w-5" />
            Team
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {currentCompany.name} is a sample company, so you can't invite people to it.
          Switch to your own company to invite teammates.
        </CardContent>
      </Card>
    );
  }

  const fail = (title: string, err: unknown) =>
    toast({ title, description: teamErrorMessage(err), variant: 'destructive' });

  const handleInvite = async (email: string, inviteRole: string) => {
    const trimmed = email.trim();
    try {
      const res = await inviteMember.mutateAsync({ companyId, email: trimmed, role: inviteRole });
      let emailSent: boolean | undefined;
      try {
        emailSent = (await res.json())?.email_sent;
      } catch {
        emailSent = undefined;
      }
      toast(inviteCreatedCopy(trimmed, emailSent === true));
    } catch (err) {
      fail("Couldn't create the invite", err);
      // Keep the dialog open with the same message inline.
      throw new Error(teamErrorMessage(err));
    }
  };

  const handleUpdateRole = async (memberId: number, newRole: string) => {
    try {
      await updateRole.mutateAsync({ memberId, role: newRole, companyId });
      toast({ title: 'Role updated' });
    } catch (err) {
      fail("Couldn't change the role", err);
    }
  };

  const handleRemoveMember = async (memberId: number) => {
    try {
      await removeMember.mutateAsync({ memberId, companyId });
      toast({ title: 'Member removed' });
    } catch (err) {
      fail("Couldn't remove the member", err);
    }
  };

  const handleRevokeInvite = async (inviteId: number) => {
    try {
      await revokeInvite.mutateAsync({ inviteId, companyId });
      toast({ title: 'Invite revoked' });
    } catch (err) {
      fail("Couldn't revoke the invite", err);
    }
  };

  const handleResendInvite = async (inviteId: number) => {
    const email = invitesQuery.data?.find((i) => i.id === inviteId)?.email ?? 'this teammate';
    try {
      await resendInvite.mutateAsync({ inviteId, companyId });
      toast(inviteRenewedCopy(email));
    } catch (err) {
      fail("Couldn't renew the invite", err);
    }
  };

  if (membersQuery.isError) {
    return (
      <Card data-testid="card-team-error">
        <CardContent className="pt-6 text-sm text-muted-foreground">
          We couldn't load your team: {teamErrorMessage(membersQuery.error)}
        </CardContent>
      </Card>
    );
  }

  return (
    <TeamWorkspace
      companyId={companyId}
      companyName={currentCompany.name}
      members={membersQuery.data ?? []}
      invites={(invitesQuery.data ?? []).map((i) => ({ ...i, expires_at: i.expires_at ?? '' }))}
      isLoading={membersQuery.isLoading}
      currentUserEmail={user?.email ?? ''}
      currentUserRole={role}
      onInviteMember={handleInvite}
      onUpdateRole={handleUpdateRole}
      onRemoveMember={handleRemoveMember}
      onRevokeInvite={handleRevokeInvite}
      onResendInvite={handleResendInvite}
    />
  );
}

// Deletion is handled on request (privacy policy, "Your rights"). The request
// goes from the founder's own mail client to the address the policy names.
const ACCOUNT_DELETION_MAILTO =
  'mailto:hello@founderconsole.ai?subject=' +
  encodeURIComponent('Delete my FounderConsole account') +
  '&body=' +
  encodeURIComponent('Please permanently delete my FounderConsole account and all associated data. I am writing from the email address I sign in with.');

export default function SettingsPage() {
  const { user, logout } = useFounderStore();
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const [tab, setTab] = useState<SettingsTab>(initialTab);

  const handleTabChange = (value: string) => {
    const next: SettingsTab = value === 'team' ? 'team' : 'account';
    setTab(next);
    // Keep the tab in the URL so "Settings → Team" can be linked to.
    try {
      const url = new URL(window.location.href);
      if (next === 'team') url.searchParams.set('tab', 'team');
      else url.searchParams.delete('tab');
      window.history.replaceState(window.history.state, '', url.pathname + url.search + url.hash);
    } catch {}
  };

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  // email_enabled is the opt-out every non-account email checks, and the
  // unsubscribe link sets. The digest reads its own monthly_digest flag
  // (server/api/digest.py), which the unsubscribe clears as well, so this
  // screen has to be able to write that flag back: a user with no company has
  // no dashboard switch to do it on.
  const { data: notificationPrefs, isLoading: prefsLoading } = useNotificationPreferences();
  const updateNotificationPrefs = useUpdateNotificationPreferences();
  const productEmailsOn = notificationPrefs?.email_enabled ?? true;
  const monthlyDigestOn = notificationPrefs?.monthly_digest ?? true;

  const handleProductEmailsChange = async (checked: boolean) => {
    if (!notificationPrefs) return;
    try {
      await updateNotificationPrefs.mutateAsync({
        ...notificationPrefs,
        email_enabled: checked,
        // Re-enabling restores the digest the unsubscribe turned off; turning
        // product emails off leaves the digest switch where the user put it.
        monthly_digest: checked ? true : notificationPrefs.monthly_digest,
      });
      toast({ title: checked ? 'Product emails on' : 'Product emails off' });
    } catch {
      toast({ title: 'Could not save your email preference', variant: 'destructive' });
    }
  };

  const handleMonthlyDigestChange = async (checked: boolean) => {
    if (!notificationPrefs) return;
    try {
      await updateNotificationPrefs.mutateAsync({ ...notificationPrefs, monthly_digest: checked });
      toast({ title: checked ? 'Monthly digest on' : 'Monthly digest off' });
    } catch {
      toast({ title: 'Could not save your digest preference', variant: 'destructive' });
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      toast({ title: 'Passwords do not match', variant: 'destructive' });
      return;
    }
    // Same rule the server enforces (and register uses).
    if (newPassword.length < 8 || !/\d/.test(newPassword)) {
      toast({ title: 'Password must be at least 8 characters and contain a number', variant: 'destructive' });
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
    } catch (err) {
      const detail = (err as { detail?: unknown })?.detail;
      const description = typeof detail === 'string'
        ? detail
        : Array.isArray(detail) && typeof detail[0]?.msg === 'string'
          ? String(detail[0].msg).replace(/^Value error, /, '')
          : 'Check your current password and try again.';
      toast({ title: 'Failed to update password', description, variant: 'destructive' });
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
        <p className="text-sm text-muted-foreground mt-1">Manage your account, security and team</p>
      </div>

      <Tabs value={tab} onValueChange={handleTabChange} className="space-y-6">
      <TabsList>
        <TabsTrigger value="account" data-testid="tab-settings-account">Account</TabsTrigger>
        <TabsTrigger value="team" data-testid="tab-settings-team">Team</TabsTrigger>
      </TabsList>

      <TabsContent value="team" className="mt-0">
        <TeamSettingsTab />
      </TabsContent>

      <TabsContent value="account" className="mt-0 space-y-6">
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
              <p className="text-sm font-medium">Product emails</p>
              <p className="text-xs text-muted-foreground">
                Onboarding tips, activity summaries and product updates. Password,
                verification and receipt emails are always sent.
              </p>
            </div>
            <Switch
              checked={productEmailsOn}
              disabled={prefsLoading || !notificationPrefs || updateNotificationPrefs.isPending}
              onCheckedChange={handleProductEmailsChange}
              data-testid="switch-email-product"
            />
          </div>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <p className="text-sm font-medium">Monthly digest</p>
              <p className="text-xs text-muted-foreground">
                A monthly summary of your company's numbers. You can also change this
                from a company dashboard.
              </p>
            </div>
            <Switch
              checked={monthlyDigestOn}
              disabled={prefsLoading || !notificationPrefs || updateNotificationPrefs.isPending}
              onCheckedChange={handleMonthlyDigestChange}
              data-testid="switch-monthly-digest"
            />
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
          <div className="flex items-center justify-between gap-4 pt-4 mt-4 border-t border-destructive/10">
            <div className="space-y-0.5">
              <p className="text-sm font-medium text-destructive">Delete Account</p>
              <p className="text-xs text-muted-foreground">
                Ask us to permanently delete your account and all its data. We confirm by email and
                remove your personal data within 30 days, as our privacy policy says.
              </p>
            </div>
            <Button variant="outline" size="sm" asChild data-testid="button-request-account-deletion">
              <a href={ACCOUNT_DELETION_MAILTO}>Request deletion</a>
            </Button>
          </div>
        </CardContent>
      </Card>
      </TabsContent>
      </Tabs>
    </div>
    </FadeIn>
  );
}
