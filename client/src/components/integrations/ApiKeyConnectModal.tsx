import { useState } from 'react';
import { IntegrationConfig } from '@/lib/integrations/types';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Shield, Eye, EyeOff, Loader2, AlertCircle } from 'lucide-react';
import { useForm } from 'react-hook-form';

interface ApiKeyConnectModalProps {
  integration: IntegrationConfig | null;
  isOpen: boolean;
  onClose: () => void;
  onConnect: (integrationId: string, credentials: Record<string, string>, selectedDataPoints: string[]) => void;
}

export function ApiKeyConnectModal({
  integration,
  isOpen,
  onClose,
  onConnect,
}: ApiKeyConnectModalProps) {
  const [step, setStep] = useState<'credentials' | 'datapoints' | 'connecting'>('credentials');
  const [isConnecting, setIsConnecting] = useState(false);
  const [showPasswords, setShowPasswords] = useState<Record<string, boolean>>({});
  const [selectedDataPoints, setSelectedDataPoints] = useState<string[]>([]);
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});

  if (!integration || !integration.apiKeyConfig) return null;

  const handleInputChange = (fieldName: string, value: string) => {
    setCredentials(prev => ({ ...prev, [fieldName]: value }));
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

  const handleContinue = () => {
    if (validateCredentials()) {
      setStep('datapoints');
    }
  };

  const handleToggleDataPoint = (dpId: string) => {
    setSelectedDataPoints(prev => 
      prev.includes(dpId) 
        ? prev.filter(id => id !== dpId)
        : [...prev, dpId]
    );
  };

  const handleSelectAll = () => {
    if (selectedDataPoints.length === integration.dataPoints.length) {
      setSelectedDataPoints([]);
    } else {
      setSelectedDataPoints(integration.dataPoints.map(dp => dp.id));
    }
  };

  const handleConnect = async () => {
    setIsConnecting(true);
    setStep('connecting');
    
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    onConnect(
      integration.id, 
      credentials,
      selectedDataPoints.length > 0 ? selectedDataPoints : integration.dataPoints.map(dp => dp.id)
    );
    
    setIsConnecting(false);
    handleClose();
  };

  const handleClose = () => {
    setStep('credentials');
    setCredentials({});
    setSelectedDataPoints([]);
    setErrors({});
    setShowPasswords({});
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-md" data-testid="modal-apikey-connect">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Connect {integration.name}
          </DialogTitle>
          <DialogDescription>
            {step === 'credentials' && 'Enter your API credentials to connect.'}
            {step === 'datapoints' && 'Select which data points you want to sync.'}
            {step === 'connecting' && 'Testing connection and syncing data...'}
          </DialogDescription>
        </DialogHeader>

        {step === 'credentials' && (
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
        )}

        {step === 'datapoints' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">Available Data Points</Label>
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={handleSelectAll}
                data-testid="button-select-all"
              >
                {selectedDataPoints.length === integration.dataPoints.length ? 'Deselect All' : 'Select All'}
              </Button>
            </div>
            
            <div className="max-h-64 overflow-y-auto space-y-2">
              {integration.dataPoints.map((dp) => (
                <div 
                  key={dp.id} 
                  className="flex items-start gap-3 p-2 rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <Checkbox
                    id={dp.id}
                    checked={selectedDataPoints.includes(dp.id)}
                    onCheckedChange={() => handleToggleDataPoint(dp.id)}
                    data-testid={`checkbox-datapoint-${dp.id}`}
                  />
                  <div className="flex-1">
                    <Label htmlFor={dp.id} className="font-medium text-sm cursor-pointer">
                      {dp.name}
                    </Label>
                    <p className="text-xs text-muted-foreground">{dp.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {step === 'connecting' && (
          <div className="py-8 flex flex-col items-center gap-4">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">
              Connecting to {integration.name}...
            </p>
          </div>
        )}

        <DialogFooter>
          {step === 'credentials' && (
            <>
              <Button variant="outline" onClick={handleClose} data-testid="button-cancel">
                Cancel
              </Button>
              <Button onClick={handleContinue} data-testid="button-continue">
                Continue
              </Button>
            </>
          )}
          {step === 'datapoints' && (
            <>
              <Button variant="outline" onClick={() => setStep('credentials')} data-testid="button-back">
                Back
              </Button>
              <Button onClick={handleConnect} data-testid="button-connect">
                Connect
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default ApiKeyConnectModal;
