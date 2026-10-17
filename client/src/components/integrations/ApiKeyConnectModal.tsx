import { useState } from 'react';
import { IntegrationConfig } from '@/lib/integrations/types';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Shield, Eye, EyeOff, Loader2, AlertCircle } from 'lucide-react';

interface ApiKeyConnectModalProps {
  integration: IntegrationConfig | null;
  isOpen: boolean;
  onClose: () => void;
  /**
   * Performs the real connect request. Resolve on success; throw to keep the
   * modal open and show the error. The modal never reports success itself.
   */
  onConnect: (integrationId: string, credentials: Record<string, string>) => Promise<void>;
}

export function ApiKeyConnectModal({
  integration,
  isOpen,
  onClose,
  onConnect,
}: ApiKeyConnectModalProps) {
  const [isConnecting, setIsConnecting] = useState(false);
  const [showPasswords, setShowPasswords] = useState<Record<string, boolean>>({});
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);

  if (!integration || !integration.apiKeyConfig) return null;

  const handleInputChange = (fieldName: string, value: string) => {
    setCredentials(prev => ({ ...prev, [fieldName]: value }));
    setSubmitError(null);
    if (errors[fieldName]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[fieldName];
        return newErrors;
      });
    }
  };

  const togglePasswordVisibility = (fieldName: string) => {
    setShowPasswords(prev => ({ ...prev, [fieldName]: !prev[fieldName] }));
  };

  const validateCredentials = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    integration.apiKeyConfig?.fields.forEach(field => {
      if (field.required && !credentials[field.name]?.trim()) {
        newErrors[field.name] = `${field.label} is required`;
      }
    });
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleClose = () => {
    if (isConnecting) return;
    setCredentials({});
    setErrors({});
    setSubmitError(null);
    setShowPasswords({});
    onClose();
  };

  const handleConnect = async () => {
    if (!validateCredentials()) return;
    setIsConnecting(true);
    setSubmitError(null);
    try {
      await onConnect(integration.id, credentials);
      setIsConnecting(false);
      setCredentials({});
      setShowPasswords({});
      onClose();
    } catch (err) {
      setIsConnecting(false);
      setSubmitError(err instanceof Error && err.message ? err.message : 'Connection failed. Check your credentials.');
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-md" data-testid="modal-apikey-connect">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Connect {integration.name}
          </DialogTitle>
          <DialogDescription>
            Enter your API credentials. We check them with {integration.name} before saving.
          </DialogDescription>
        </DialogHeader>

          <div className="space-y-4">
            <div className="bg-muted/50 rounded-lg p-3 flex items-start gap-2">
              <Shield className="w-4 h-4 text-primary mt-0.5" />
              <p className="text-xs text-muted-foreground">
                Your credentials are encrypted and stored securely. 
                We never share your API keys with third parties.
              </p>
            </div>

            <div className="space-y-4">
              {integration.apiKeyConfig.fields.map((field) => (
                <div key={field.name} className="space-y-2">
                  <Label htmlFor={field.name}>
                    {field.label}
                    {field.required && <span className="text-destructive ml-1">*</span>}
                  </Label>
                  <div className="relative">
                    <Input
                      id={field.name}
                      type={field.type === 'password' && !showPasswords[field.name] ? 'password' : 'text'}
                      placeholder={field.placeholder}
                      value={credentials[field.name] || ''}
                      onChange={(e) => handleInputChange(field.name, e.target.value)}
                      className={errors[field.name] ? 'border-destructive' : ''}
                      data-testid={`input-${field.name}`}
                    />
                    {field.type === 'password' && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="absolute right-0 top-0 h-full"
                        onClick={() => togglePasswordVisibility(field.name)}
                        aria-label={showPasswords[field.name] ? `Hide ${field.label}` : `Show ${field.label}`}
                        data-testid={`button-toggle-${field.name}`}
                      >
                        {showPasswords[field.name] ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </Button>
                    )}
                  </div>
                  {errors[field.name] && (
                    <p className="text-xs text-destructive flex items-center gap-1">
                      <AlertCircle className="w-3 h-3" />
                      {errors[field.name]}
                    </p>
                  )}
                  {field.helpText && !errors[field.name] && (
                    <p className="text-xs text-muted-foreground">{field.helpText}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
            {submitError && (
              <p className="text-sm text-destructive flex items-center gap-1" role="alert" data-testid="text-connect-error">
                <AlertCircle className="w-4 h-4" />
                {submitError}
              </p>
            )}

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isConnecting} data-testid="button-cancel">
            Cancel
          </Button>
          <Button onClick={handleConnect} disabled={isConnecting} data-testid="button-connect">
            {isConnecting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            {isConnecting ? 'Checking credentials...' : 'Connect'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default ApiKeyConnectModal;
