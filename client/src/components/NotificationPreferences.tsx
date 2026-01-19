import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Bell, Mail, AlertTriangle, TrendingDown, Calendar, CheckCircle2, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface NotificationSettings {
  email_enabled: boolean;
  email_address: string;
  alert_types: {
    runway_warning: boolean;
    growth_decline: boolean;
    churn_spike: boolean;
    cash_low: boolean;
    scenario_complete: boolean;
    team_activity: boolean;
  };
  thresholds: {
    runway_months: number;
    growth_decline_pct: number;
    churn_increase_pct: number;
    cash_low_months: number;
  };
  frequency: 'immediate' | 'daily' | 'weekly';
}

interface NotificationPreferencesProps {
  settings: NotificationSettings;
  onSave: (settings: NotificationSettings) => Promise<void>;
  isSaving: boolean;
}

const ALERT_TYPES = [
  {
    key: 'runway_warning',
    label: 'Runway Warning',
    description: 'Get notified when runway drops below threshold',
    icon: AlertTriangle,
    color: 'text-red-500',
  },
  {
    key: 'growth_decline',
    label: 'Growth Decline',
    description: 'Alert when growth rate decreases significantly',
    icon: TrendingDown,
    color: 'text-amber-500',
  },
  {
    key: 'churn_spike',
    label: 'Churn Spike',
    description: 'Notify when churn increases above normal',
    icon: TrendingDown,
    color: 'text-orange-500',
  },
  {
    key: 'cash_low',
    label: 'Low Cash Alert',
    description: 'Alert when cash reserves are running low',
    icon: AlertTriangle,
    color: 'text-red-600',
  },
  {
    key: 'scenario_complete',
    label: 'Simulation Complete',
    description: 'Notify when simulation runs finish',
    icon: CheckCircle2,
    color: 'text-green-500',
  },
  {
    key: 'team_activity',
    label: 'Team Activity',
    description: 'Updates on team comments and changes',
    icon: Calendar,
    color: 'text-blue-500',
  },
];

export function NotificationPreferences({
  settings,
  onSave,
  isSaving,
}: NotificationPreferencesProps) {
  const [localSettings, setLocalSettings] = useState<NotificationSettings>(settings);
  const [hasChanges, setHasChanges] = useState(false);

  const updateSettings = (updates: Partial<NotificationSettings>) => {
    setLocalSettings(prev => ({ ...prev, ...updates }));
    setHasChanges(true);
  };

  const updateAlertType = (key: string, enabled: boolean) => {
    setLocalSettings(prev => ({
      ...prev,
      alert_types: { ...prev.alert_types, [key]: enabled },
    }));
    setHasChanges(true);
  };

  const updateThreshold = (key: string, value: number) => {
    setLocalSettings(prev => ({
      ...prev,
      thresholds: { ...prev.thresholds, [key]: value },
    }));
    setHasChanges(true);
  };

  const handleSave = async () => {
    await onSave(localSettings);
    setHasChanges(false);
  };

  const enabledCount = Object.values(localSettings.alert_types).filter(Boolean).length;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <Bell className="h-5 w-5 text-primary" />
              <div>
                <CardTitle className="text-lg">Notification Preferences</CardTitle>
                <CardDescription>Configure how and when you receive alerts</CardDescription>
              </div>
            </div>
            <Badge variant={localSettings.email_enabled ? 'default' : 'secondary'}>
              {localSettings.email_enabled ? 'Enabled' : 'Disabled'}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-1">
              <Label className="flex items-center gap-2">
                <Mail className="h-4 w-4" />
                Email Notifications
              </Label>
              <p className="text-sm text-muted-foreground">
                Receive alerts via email
              </p>
            </div>
            <Switch
              checked={localSettings.email_enabled}
              onCheckedChange={(checked) => updateSettings({ email_enabled: checked })}
              data-testid="switch-email-notifications"
            />
          </div>

          {localSettings.email_enabled && (
            <>
              <div className="space-y-2">
                <Label htmlFor="email-address">Email Address</Label>
                <Input
                  id="email-address"
                  type="email"
                  value={localSettings.email_address}
                  onChange={(e) => updateSettings({ email_address: e.target.value })}
                  placeholder="your@email.com"
                  data-testid="input-notification-email"
                />
              </div>

              <div className="space-y-2">
                <Label>Notification Frequency</Label>
                <div className="flex gap-2">
                  {(['immediate', 'daily', 'weekly'] as const).map(freq => (
                    <Button
                      key={freq}
                      variant={localSettings.frequency === freq ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => updateSettings({ frequency: freq })}
                      data-testid={`button-frequency-${freq}`}
                    >
                      {freq.charAt(0).toUpperCase() + freq.slice(1)}
                    </Button>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">
                  {localSettings.frequency === 'immediate' && 'Receive alerts as they happen'}
                  {localSettings.frequency === 'daily' && 'Receive a daily digest of alerts'}
                  {localSettings.frequency === 'weekly' && 'Receive a weekly summary'}
                </p>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-4">
            <CardTitle className="text-base">Alert Types</CardTitle>
            <Badge variant="outline">{enabledCount} enabled</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {ALERT_TYPES.map(alertType => {
            const Icon = alertType.icon;
            const isEnabled = localSettings.alert_types[alertType.key as keyof typeof localSettings.alert_types];
            
            return (
              <div
                key={alertType.key}
                className={cn(
                  'flex items-center justify-between gap-4 p-3 rounded-lg border transition-colors',
                  isEnabled ? 'bg-primary/5 border-primary/20' : 'bg-muted/30'
                )}
              >
                <div className="flex items-center gap-3">
                  <Icon className={cn('h-5 w-5', alertType.color)} />
                  <div>
                    <Label className="cursor-pointer">{alertType.label}</Label>
                    <p className="text-xs text-muted-foreground">{alertType.description}</p>
                  </div>
                </div>
                <Switch
                  checked={isEnabled}
                  onCheckedChange={(checked) => updateAlertType(alertType.key, checked)}
                  data-testid={`switch-alert-${alertType.key}`}
                />
              </div>
            );
          })}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Alert Thresholds</CardTitle>
          <CardDescription>Customize when alerts are triggered</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="runway-threshold">Runway Warning (months)</Label>
              <Input
                id="runway-threshold"
                type="number"
                value={localSettings.thresholds.runway_months}
                onChange={(e) => updateThreshold('runway_months', parseInt(e.target.value) || 12)}
                min={1}
                max={36}
                data-testid="input-threshold-runway"
              />
              <p className="text-xs text-muted-foreground">
                Alert when runway drops below this
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="growth-threshold">Growth Decline (%)</Label>
              <Input
                id="growth-threshold"
                type="number"
                value={localSettings.thresholds.growth_decline_pct}
                onChange={(e) => updateThreshold('growth_decline_pct', parseInt(e.target.value) || 10)}
                min={1}
                max={50}
                data-testid="input-threshold-growth"
              />
              <p className="text-xs text-muted-foreground">
                Alert when growth drops by this %
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="churn-threshold">Churn Increase (%)</Label>
              <Input
                id="churn-threshold"
                type="number"
                value={localSettings.thresholds.churn_increase_pct}
                onChange={(e) => updateThreshold('churn_increase_pct', parseInt(e.target.value) || 20)}
                min={1}
                max={100}
                data-testid="input-threshold-churn"
              />
              <p className="text-xs text-muted-foreground">
                Alert when churn increases by this %
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="cash-threshold">Low Cash (months of runway)</Label>
              <Input
                id="cash-threshold"
                type="number"
                value={localSettings.thresholds.cash_low_months}
                onChange={(e) => updateThreshold('cash_low_months', parseInt(e.target.value) || 6)}
                min={1}
                max={24}
                data-testid="input-threshold-cash"
              />
              <p className="text-xs text-muted-foreground">
                Alert when cash covers less than this
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {hasChanges && (
        <div className="flex justify-end">
          <Button onClick={handleSave} disabled={isSaving} data-testid="button-save-notifications">
            {isSaving ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              'Save Preferences'
            )}
          </Button>
        </div>
      )}
    </div>
  );
}
