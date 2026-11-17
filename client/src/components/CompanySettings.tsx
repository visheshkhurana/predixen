import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Building2, Loader2 } from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useUpdateCompany } from '@/api/hooks';
import { useWorkspaceMembers } from '@/api/workspace';
import { useToast } from '@/hooks/use-toast';
import { roleForEmail } from '@/lib/teamInvites';
import { CURRENCY_OPTIONS, INDUSTRY_OPTIONS, STAGE_OPTIONS } from '@/lib/companyOptions';

/** Settings → Company: change the name, industry, stage and currency after onboarding. */
export function CompanySettings() {
  const { user, currentCompany } = useFounderStore();
  const { toast } = useToast();
  const update = useUpdateCompany();
  const { data: members } = useWorkspaceMembers(currentCompany && !currentCompany.is_sample ? currentCompany.id : 0);
  const role = roleForEmail(members, user?.email);
  const canEdit = !currentCompany?.is_sample && ['owner', 'admin', 'editor'].includes(role);

  const [form, setForm] = useState({ name: '', industry: '', stage: '', currency: 'USD' });
  useEffect(() => {
    if (!currentCompany) return;
    setForm({
      name: currentCompany.name || '',
      industry: currentCompany.industry || '',
      stage: currentCompany.stage || '',
      currency: (currentCompany.currency || 'USD').toUpperCase(),
    });
  }, [currentCompany]);

  if (!currentCompany) {
    return <p className="text-sm text-muted-foreground">Select a company first.</p>;
  }

  const currencyChanged = form.currency !== (currentCompany.currency || 'USD').toUpperCase();
  const knownIndustry = INDUSTRY_OPTIONS.some((o) => o.value === form.industry);
  const knownStage = STAGE_OPTIONS.some((o) => o.value === form.stage);

  const save = () => {
    if (!form.name.trim()) {
      toast({ title: 'Company name is required', variant: 'destructive' });
      return;
    }
    update.mutate(
      { id: currentCompany.id, data: { name: form.name.trim(), industry: form.industry || undefined, stage: form.stage || undefined, currency: form.currency } },
      {
        onSuccess: () => toast({ title: 'Company updated' }),
        onError: (err: Error) => toast({ title: 'Not saved', description: err.message, variant: 'destructive' }),
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Building2 className="h-5 w-5" />
          Company
        </CardTitle>
        <CardDescription>
          {canEdit
            ? 'Industry and stage choose the benchmarks and the metrics you see.'
            : currentCompany.is_sample
              ? 'This is the sample company; its details can’t be changed.'
              : 'You have view-only access to this company.'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="company-name">Company name</Label>
          <Input id="company-name" value={form.name} disabled={!canEdit} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="input-company-name" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label>Industry</Label>
            <Select value={form.industry} disabled={!canEdit} onValueChange={(v) => setForm({ ...form, industry: v })}>
              <SelectTrigger data-testid="select-company-industry"><SelectValue placeholder="Select industry" /></SelectTrigger>
              <SelectContent>
                {!knownIndustry && form.industry && <SelectItem value={form.industry}>{form.industry}</SelectItem>}
                {INDUSTRY_OPTIONS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Stage</Label>
            <Select value={form.stage} disabled={!canEdit} onValueChange={(v) => setForm({ ...form, stage: v })}>
              <SelectTrigger data-testid="select-company-stage"><SelectValue placeholder="Select stage" /></SelectTrigger>
              <SelectContent>
                {!knownStage && form.stage && <SelectItem value={form.stage}>{form.stage}</SelectItem>}
                {STAGE_OPTIONS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="space-y-1.5">
          <Label>Reporting currency</Label>
          <Select value={form.currency} disabled={!canEdit} onValueChange={(v) => setForm({ ...form, currency: v })}>
            <SelectTrigger data-testid="select-company-currency"><SelectValue /></SelectTrigger>
            <SelectContent>
              {CURRENCY_OPTIONS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
            </SelectContent>
          </Select>
          {currencyChanged && (
            <p className="text-xs text-amber-500" data-testid="text-currency-warning">
              This changes the currency label only. Numbers you have already entered are not converted.
            </p>
          )}
        </div>
        {canEdit && (
          <Button onClick={save} disabled={update.isPending} data-testid="button-save-company">
            {update.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save company
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
