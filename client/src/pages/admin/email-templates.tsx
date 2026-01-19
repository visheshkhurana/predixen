import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { 
  Mail, Eye, Send, CheckCircle, XCircle, FileText, 
  AlertCircle, RefreshCw, Settings
} from 'lucide-react';
import { api } from '@/api/client';

export default function EmailTemplates() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [previewTemplate, setPreviewTemplate] = useState<string | null>(null);
  const [testEmailDialog, setTestEmailDialog] = useState<{ open: boolean; templateType: string | null }>({ open: false, templateType: null });
  const [testEmail, setTestEmail] = useState('');

  const { data: emailStatus, isLoading: statusLoading } = useQuery({
    queryKey: ['/admin/email-templates/status'],
    queryFn: () => api.admin.emailTemplates.status(),
  });

  const { data: templates, isLoading: templatesLoading } = useQuery({
    queryKey: ['/admin/email-templates/list'],
    queryFn: () => api.admin.emailTemplates.list(),
  });

  const { data: previewData, isLoading: previewLoading } = useQuery({
    queryKey: ['/admin/email-templates/preview', previewTemplate],
    queryFn: () => previewTemplate ? api.admin.emailTemplates.preview(previewTemplate) : null,
    enabled: !!previewTemplate,
  });

  const sendTestMutation = useMutation({
    mutationFn: ({ templateType, toEmail }: { templateType: string; toEmail: string }) =>
      api.admin.emailTemplates.sendTest(templateType, toEmail),
    onSuccess: () => {
      toast({
        title: "Test Email Sent",
        description: `Test email sent to ${testEmail}`,
      });
      setTestEmailDialog({ open: false, templateType: null });
      setTestEmail('');
    },
    onError: (error: any) => {
      toast({
        title: "Failed to Send Test Email",
        description: error.message || "An error occurred",
        variant: "destructive",
      });
    },
  });

  const getTemplateIcon = (templateId: string) => {
    switch (templateId) {
      case 'invite': return Mail;
      case 'welcome': return CheckCircle;
      case 'password_reset': return Settings;
      default: return FileText;
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Email Templates</h1>
          <p className="text-muted-foreground">Manage and preview email templates</p>
        </div>
      </div>

      <Card data-testid="card-email-status">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            Email Service Status
          </CardTitle>
          <CardDescription>Configuration status for the email sending service</CardDescription>
        </CardHeader>
        <CardContent>
          {statusLoading ? (
            <Skeleton className="h-8 w-48" />
          ) : (
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                {emailStatus?.configured ? (
                  <>
                    <CheckCircle className="h-5 w-5 text-green-500" />
                    <Badge variant="secondary" className="bg-green-500/20 text-green-600 border-0">
                      Configured
                    </Badge>
                  </>
                ) : (
                  <>
                    <XCircle className="h-5 w-5 text-red-500" />
                    <Badge variant="secondary" className="bg-red-500/20 text-red-600 border-0">
                      Not Configured
                    </Badge>
                  </>
                )}
              </div>
              {emailStatus?.from_email && (
                <div className="text-sm text-muted-foreground">
                  Sending from: <code className="bg-muted px-2 py-0.5 rounded">{emailStatus.from_email}</code>
                </div>
              )}
            </div>
          )}
          {!emailStatus?.configured && !statusLoading && (
            <div className="mt-4 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
              <div>
                <p className="font-medium text-yellow-600">Email service not configured</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Invitations will be created but emails won't be sent. Connect Resend integration to enable email sending.
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {templatesLoading ? (
          [1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <Skeleton className="h-8 w-32 mb-2" />
                <Skeleton className="h-4 w-full mb-4" />
                <Skeleton className="h-10 w-24" />
              </CardContent>
            </Card>
          ))
        ) : (
          templates?.map((template) => {
            const Icon = getTemplateIcon(template.id);
            return (
              <Card key={template.id} data-testid={`card-template-${template.id}`}>
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-primary/10 rounded-lg">
                      <Icon className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <CardTitle className="text-base">{template.name}</CardTitle>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm text-muted-foreground">{template.description}</p>
                  
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1">Subject:</p>
                    <p className="text-sm">{template.subject}</p>
                  </div>
                  
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1">Variables:</p>
                    <div className="flex flex-wrap gap-1">
                      {template.variables.map((variable) => (
                        <Badge key={variable} variant="outline" className="text-xs">
                          {`{${variable}}`}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  
                  <div className="flex gap-2 pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPreviewTemplate(template.id)}
                      data-testid={`button-preview-${template.id}`}
                    >
                      <Eye className="h-4 w-4 mr-1" />
                      Preview
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setTestEmailDialog({ open: true, templateType: template.id })}
                      disabled={!emailStatus?.configured}
                      data-testid={`button-test-${template.id}`}
                    >
                      <Send className="h-4 w-4 mr-1" />
                      Send Test
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>

      <Dialog open={!!previewTemplate} onOpenChange={(open) => !open && setPreviewTemplate(null)}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Template Preview: {previewData?.name}</DialogTitle>
            <DialogDescription>
              Subject: {previewData?.subject}
            </DialogDescription>
          </DialogHeader>
          {previewLoading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : previewData?.html ? (
            <div className="border rounded-lg overflow-hidden">
              <iframe
                srcDoc={previewData.html}
                className="w-full h-[500px] bg-white"
                title="Email Template Preview"
                sandbox="allow-same-origin"
              />
            </div>
          ) : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setPreviewTemplate(null)}>
              Close
            </Button>
            <Button
              onClick={() => {
                setTestEmailDialog({ open: true, templateType: previewTemplate });
                setPreviewTemplate(null);
              }}
              disabled={!emailStatus?.configured}
            >
              <Send className="h-4 w-4 mr-2" />
              Send Test Email
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={testEmailDialog.open} onOpenChange={(open) => !open && setTestEmailDialog({ open: false, templateType: null })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Send Test Email</DialogTitle>
            <DialogDescription>
              Send a test email using the {templates?.find(t => t.id === testEmailDialog.templateType)?.name ?? 'selected'} template.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="test-email">Recipient Email</Label>
              <Input
                id="test-email"
                type="email"
                placeholder="test@example.com"
                value={testEmail}
                onChange={(e) => setTestEmail(e.target.value)}
                data-testid="input-test-email"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTestEmailDialog({ open: false, templateType: null })}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (testEmailDialog.templateType && testEmail) {
                  sendTestMutation.mutate({ templateType: testEmailDialog.templateType, toEmail: testEmail });
                }
              }}
              disabled={!testEmail || sendTestMutation.isPending}
              data-testid="button-send-test"
            >
              {sendTestMutation.isPending ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Send Test
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
