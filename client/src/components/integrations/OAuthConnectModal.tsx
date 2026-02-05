import { useState } from 'react';
import { IntegrationConfig } from '@/lib/integrations/types';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { ExternalLink, Shield, Check, Loader2 } from 'lucide-react';

interface OAuthConnectModalProps {
  integration: IntegrationConfig | null;
  isOpen: boolean;
  onClose: () => void;
  onConnect: (integrationId: string, selectedDataPoints: string[]) => void;
}

export function OAuthConnectModal({
  integration,
  isOpen,
  onClose,
  onConnect,
}: OAuthConnectModalProps) {
  const [selectedDataPoints, setSelectedDataPoints] = useState<string[]>([]);
  const [isConnecting, setIsConnecting] = useState(false);
  const [step, setStep] = useState<'permissions' | 'datapoints' | 'connecting'>('permissions');

  if (!integration) return null;

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
    
    onConnect(integration.id, selectedDataPoints.length > 0 ? selectedDataPoints : integration.dataPoints.map(dp => dp.id));
    
    setIsConnecting(false);
    setStep('permissions');
    setSelectedDataPoints([]);
    onClose();
  };

  const handleClose = () => {
    setStep('permissions');
    setSelectedDataPoints([]);
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-md" data-testid="modal-oauth-connect">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Connect {integration.name}
          </DialogTitle>
          <DialogDescription>
            {step === 'permissions' && 'Review the permissions required for this integration.'}
            {step === 'datapoints' && 'Select which data points you want to sync.'}
            {step === 'connecting' && 'Connecting to your account...'}
          </DialogDescription>
        </DialogHeader>

        {step === 'permissions' && (
          <div className="space-y-4">
            <div className="bg-muted/50 rounded-lg p-4 space-y-3">
              <div className="flex items-start gap-3">
                <Shield className="w-5 h-5 text-primary mt-0.5" />
                <div>
                  <h4 className="font-medium text-sm">Secure OAuth Connection</h4>
                  <p className="text-xs text-muted-foreground">
                    You'll be redirected to {integration.name} to authorize access. 
                    We only request read-only permissions.
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="font-medium text-sm">Requested Permissions:</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                {integration.oauthConfig?.scopes.map((scope, i) => (
                  <li key={i} className="flex items-center gap-2">
                    <Check className="w-4 h-4 text-green-500" />
                    <span className="text-xs break-all">{scope}</span>
                  </li>
                ))}
              </ul>
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
          {step === 'permissions' && (
            <>
              <Button variant="outline" onClick={handleClose} data-testid="button-cancel">
                Cancel
              </Button>
              <Button onClick={() => setStep('datapoints')} data-testid="button-continue">
                Continue
              </Button>
            </>
          )}
          {step === 'datapoints' && (
            <>
              <Button variant="outline" onClick={() => setStep('permissions')} data-testid="button-back">
                Back
              </Button>
              <Button onClick={handleConnect} data-testid="button-authorize">
                <ExternalLink className="w-4 h-4 mr-2" />
                Authorize with {integration.name}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default OAuthConnectModal;
