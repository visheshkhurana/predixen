/**
 * Settings page — /admin/lead-gen/settings
 * Place at: client/src/pages/admin/lead-gen/settings.tsx
 */

import { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";
import { leadGenApi, leadGenKeys } from "@/lib/api/lead-gen";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Eye, EyeOff, CheckCircle2, AlertTriangle } from "lucide-react";

export default function SettingsPage() {
  const qc = useQueryClient();
  const { toast } = useToast();
  const { data, isLoading } = useQuery({
    queryKey: leadGenKeys.settings(),
    queryFn: leadGenApi.getSettings,
  });

  const [form, setForm] = useState({
    n8n_base_url: "",
    n8n_api_key: "",
    outbound_webhook_url: "",
    activation_webhook_url: "",
    sending_domain: "",
    daily_send_limit: 30,
    is_enabled: false,
  });
  const [showKey, setShowKey] = useState(false);

  useEffect(() => {
    if (data) {
      setForm(f => ({
        ...f,
        n8n_base_url: data.n8n_base_url ?? "",
        outbound_webhook_url: data.outbound_webhook_url ?? "",
        activation_webhook_url: data.activation_webhook_url ?? "",
        sending_domain: data.sending_domain ?? "",
        daily_send_limit: data.daily_send_limit,
        is_enabled: data.is_enabled,
      }));
    }
  }, [data]);

  const saveMut = useMutation({
    mutationFn: leadGenApi.patchSettings,
    onSuccess: () => {
      toast({ title: "Settings saved" });
      qc.invalidateQueries({ queryKey: leadGenKeys.settings() });
      setForm(f => ({ ...f, n8n_api_key: "" })); // clear the key input after save
    },
    onError: (e: Error) => toast({ title: "Save failed", description: e.message, variant: "destructive" }),
  });

  if (isLoading || !data) return <div className="text-center py-12 text-muted-foreground">Loading…</div>;

  const handleSave = () => {
    const payload: Partial<typeof form> = { ...form };
    // Don't send empty api_key — server treats missing field as "keep existing"
    if (!form.n8n_api_key) delete payload.n8n_api_key;
    saveMut.mutate(payload as any);
  };

  const readyToEnable = data.n8n_base_url && data.outbound_webhook_url && data.n8n_api_key_set;

  return (
    <div className="space-y-6 max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle>Master switch</CardTitle>
          <CardDescription>When off, no outbound emails send and no webhooks fire. Flip on after all steps below are green.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Lead-gen enabled</p>
              <p className="text-sm text-muted-foreground">
                {data.is_enabled ? "✓ Live — sends + webhooks active" : "○ Paused — no sends or activity"}
              </p>
            </div>
            <Switch
              checked={form.is_enabled}
              onCheckedChange={(v) => setForm(f => ({ ...f, is_enabled: v }))}
              disabled={!readyToEnable && !form.is_enabled}
            />
          </div>
          {!readyToEnable && !form.is_enabled && (
            <Alert className="mt-4">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>Fill in n8n base URL, API key, and outbound webhook URL below before enabling.</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>n8n connection</CardTitle>
          <CardDescription>Your n8n instance — typically <code className="text-xs">https://yourname.app.n8n.cloud</code> for Cloud.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="base_url">Base URL</Label>
            <Input
              id="base_url"
              placeholder="https://vysheshk.app.n8n.cloud"
              value={form.n8n_base_url}
              onChange={e => setForm(f => ({ ...f, n8n_base_url: e.target.value }))}
            />
          </div>

          <div>
            <Label htmlFor="api_key">API key {data.n8n_api_key_set && <span className="text-xs text-emerald-600 ml-2"><CheckCircle2 className="inline h-3 w-3" /> stored</span>}</Label>
            <div className="flex gap-2">
              <Input
                id="api_key"
                type={showKey ? "text" : "password"}
                placeholder={data.n8n_api_key_set ? "••••••• (leave blank to keep)" : "Paste n8n API key"}
                value={form.n8n_api_key}
                onChange={e => setForm(f => ({ ...f, n8n_api_key: e.target.value }))}
              />
              <Button type="button" size="icon" variant="outline" onClick={() => setShowKey(s => !s)}>
                {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-1">Generate in n8n → Settings → API. Encrypted at rest with your existing CredentialEncryption service.</p>
          </div>

          <div>
            <Label htmlFor="outbound">Outbound webhook URL</Label>
            <Input
              id="outbound"
              placeholder="https://vysheshk.app.n8n.cloud/webhook/leadgen-outbound"
              value={form.outbound_webhook_url}
              onChange={e => setForm(f => ({ ...f, outbound_webhook_url: e.target.value }))}
            />
            <p className="text-xs text-muted-foreground mt-1">Manual "send email" actions from this panel POST here.</p>
          </div>

          <div>
            <Label htmlFor="activation">Activation webhook URL</Label>
            <Input
              id="activation"
              placeholder="https://vysheshk.app.n8n.cloud/webhook/founderconsole-signup"
              value={form.activation_webhook_url}
              onChange={e => setForm(f => ({ ...f, activation_webhook_url: e.target.value }))}
            />
            <p className="text-xs text-muted-foreground mt-1">Your signup handler fires this on new user creation.</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Sending guardrails</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="domain">Sending domain</Label>
            <Input
              id="domain"
              placeholder="mail.founderconsole.ai"
              value={form.sending_domain}
              onChange={e => setForm(f => ({ ...f, sending_domain: e.target.value }))}
            />
            <p className="text-xs text-muted-foreground mt-1">Use a subdomain to protect the root domain reputation. Ensure SPF/DKIM/DMARC is configured.</p>
          </div>
          <div>
            <Label htmlFor="limit">Daily send cap</Label>
            <Input
              id="limit"
              type="number"
              min={0}
              max={500}
              value={form.daily_send_limit}
              onChange={e => setForm(f => ({ ...f, daily_send_limit: parseInt(e.target.value) || 0 }))}
            />
            <p className="text-xs text-muted-foreground mt-1">Start at 30/day on a fresh sender, ramp by +10/day each week.</p>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={saveMut.isPending}>
          {saveMut.isPending ? "Saving…" : "Save settings"}
        </Button>
      </div>
    </div>
  );
}
