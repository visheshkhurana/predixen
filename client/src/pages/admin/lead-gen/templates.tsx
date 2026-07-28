/**
 * Templates editor — /admin/lead-gen/templates
 * Place at: client/src/pages/admin/lead-gen/templates.tsx
 *
 * Edit the system prompts that the n8n workflow reads at send time.
 * Iterate email copy without touching n8n.
 */

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";
import { leadGenApi, leadGenKeys, type Template } from "@/lib/api/lead-gen";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";

export default function TemplatesPage() {
  const { data: templates, isLoading } = useQuery({
    queryKey: leadGenKeys.templates(),
    queryFn: leadGenApi.listTemplates,
  });
  const [editingId, setEditingId] = useState<number | null>(null);

  if (isLoading || !templates) return <div className="text-center py-12 text-muted-foreground">Loading…</div>;

  const byCategory = templates.reduce<Record<string, Template[]>>((acc, t) => {
    (acc[t.category] ??= []).push(t);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {(["outbound", "inbound", "activation"] as const).map(cat => {
        const items = byCategory[cat] ?? [];
        if (items.length === 0) return null;
        return (
          <section key={cat}>
            <h2 className="text-lg font-semibold capitalize mb-3">{cat}</h2>
            <div className="space-y-3">
              {items.map(t => (
                <TemplateRow
                  key={t.id}
                  template={t}
                  isEditing={editingId === t.id}
                  onEdit={() => setEditingId(t.id)}
                  onCancel={() => setEditingId(null)}
                  onSaved={() => setEditingId(null)}
                />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function TemplateRow({ template, isEditing, onEdit, onCancel, onSaved }: {
  template: Template;
  isEditing: boolean;
  onEdit: () => void;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const qc = useQueryClient();
  const { toast } = useToast();
  const [form, setForm] = useState({
    label: template.label,
    system_prompt: template.system_prompt,
    sample_subject: template.sample_subject ?? "",
    sample_body: template.sample_body ?? "",
    model: template.model ?? "gpt-5-mini",
    is_active: template.is_active,
  });

  const saveMut = useMutation({
    mutationFn: (body: typeof form) => leadGenApi.patchTemplate(template.id, body),
    onSuccess: () => {
      toast({ title: "Template saved", description: `${template.key} updated.` });
      qc.invalidateQueries({ queryKey: leadGenKeys.templates() });
      onSaved();
    },
    onError: (e: Error) => toast({ title: "Save failed", description: e.message, variant: "destructive" }),
  });

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <CardTitle className="text-base">{template.label}</CardTitle>
              <Badge variant="outline" className="text-xs">{template.key}</Badge>
              {!template.is_active && <Badge variant="secondary" className="text-xs">inactive</Badge>}
            </div>
            <CardDescription className="text-xs mt-1">Model: {template.model ?? "default"}</CardDescription>
          </div>
          {!isEditing ? (
            <Button variant="outline" size="sm" onClick={onEdit}>Edit</Button>
          ) : (
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" onClick={onCancel}>Cancel</Button>
              <Button size="sm" onClick={() => saveMut.mutate(form)} disabled={saveMut.isPending}>
                {saveMut.isPending ? "Saving…" : "Save"}
              </Button>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {!isEditing ? (
          <>
            {template.sample_subject && (
              <div>
                <p className="text-xs text-muted-foreground">Sample subject</p>
                <p className="text-sm font-mono">{template.sample_subject}</p>
              </div>
            )}
            <div>
              <p className="text-xs text-muted-foreground">System prompt</p>
              <p className="text-sm whitespace-pre-wrap">{template.system_prompt}</p>
            </div>
          </>
        ) : (
          <>
            <div>
              <Label>Label</Label>
              <Input value={form.label} onChange={e => setForm(f => ({ ...f, label: e.target.value }))} />
            </div>
            <div>
              <Label>Sample subject</Label>
              <Input value={form.sample_subject} onChange={e => setForm(f => ({ ...f, sample_subject: e.target.value }))} />
            </div>
            <div>
              <Label>System prompt</Label>
              <Textarea
                rows={8}
                className="font-mono text-sm"
                value={form.system_prompt}
                onChange={e => setForm(f => ({ ...f, system_prompt: e.target.value }))}
              />
              <p className="text-xs text-muted-foreground mt-1">
                Mustache-style vars available: <code>{"{{first_name}}"}</code>, <code>{"{{company_name}}"}</code>, <code>{"{{hook}}"}</code>, <code>{"{{stage}}"}</code>, <code>{"{{sector}}"}</code>
              </p>
            </div>
            <div>
              <Label>Model</Label>
              <Input value={form.model} onChange={e => setForm(f => ({ ...f, model: e.target.value }))} placeholder="gpt-5-mini" />
            </div>
            <div className="flex items-center justify-between">
              <Label>Active</Label>
              <Switch checked={form.is_active} onCheckedChange={(v) => setForm(f => ({ ...f, is_active: v }))} />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
