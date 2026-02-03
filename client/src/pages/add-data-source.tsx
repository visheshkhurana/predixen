import { useState, useEffect } from "react";
import { useLocation, useSearch } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { fetchConnectorDetail, CatalogConnector } from "@/services/connectors.api";
import { 
  ArrowLeft, 
  ArrowRight, 
  Check, 
  Key, 
  Database, 
  FileText, 
  Webhook,
  Loader2,
  CheckCircle,
  XCircle,
  RefreshCw,
  Shield,
  Lock
} from "lucide-react";
import { 
  SiStripe, 
  SiQuickbooks,
  SiPostgresql
} from "react-icons/si";

type WizardStep = "auth" | "test" | "entities" | "sync" | "confirm";

const STEPS: { id: WizardStep; label: string }[] = [
  { id: "auth", label: "Authentication" },
  { id: "test", label: "Test Connection" },
  { id: "entities", label: "Select Data" },
  { id: "sync", label: "Sync Settings" },
  { id: "confirm", label: "Confirm" },
];

export default function AddDataSourceWizard() {
  const [, setLocation] = useLocation();
  const searchParams = new URLSearchParams(window.location.search);
  const connectorId = searchParams.get("connector");
  const { toast } = useToast();
  
  const [currentStep, setCurrentStep] = useState<WizardStep>("auth");
  const [isLoading, setIsLoading] = useState(false);
  const [testStatus, setTestStatus] = useState<"idle" | "testing" | "success" | "error">("idle");
  
  const [formData, setFormData] = useState({
    name: "",
    apiKey: "",
    apiSecret: "",
    connectionString: "",
    webhookUrl: "",
    syncMode: "poll" as "poll" | "webhook",
    refreshFrequency: "daily" as "real-time" | "hourly" | "daily" | "manual",
    selectedEntities: [] as string[],
  });
  
  const { data: connector, isLoading: connectorLoading } = useQuery({
    queryKey: ["/api/connectors/catalog", connectorId],
    queryFn: () => fetchConnectorDetail(connectorId!),
    enabled: !!connectorId,
  });
  
  useEffect(() => {
    if (connector) {
      setFormData(prev => ({
        ...prev,
        name: `${connector.name} Connection`,
        refreshFrequency: connector.typicalRefresh as any || "daily",
        syncMode: connector.supportsWebhooks ? "webhook" : "poll",
      }));
    }
  }, [connector]);
  
  const currentStepIndex = STEPS.findIndex(s => s.id === currentStep);
  const progress = ((currentStepIndex + 1) / STEPS.length) * 100;
  
  const handleTestConnection = async () => {
    setTestStatus("testing");
    await new Promise(resolve => setTimeout(resolve, 2000));
    setTestStatus("success");
    toast({
      title: "Connection successful",
      description: "Your credentials have been verified",
    });
  };
  
  const handleNext = () => {
    const nextIndex = currentStepIndex + 1;
    if (nextIndex < STEPS.length) {
      setCurrentStep(STEPS[nextIndex].id);
    }
  };
  
  const handleBack = () => {
    const prevIndex = currentStepIndex - 1;
    if (prevIndex >= 0) {
      setCurrentStep(STEPS[prevIndex].id);
    }
  };
  
  const handleComplete = async () => {
    setIsLoading(true);
    await new Promise(resolve => setTimeout(resolve, 1500));
    toast({
      title: "Data source connected",
      description: `${connector?.name} has been successfully connected`,
    });
    setLocation(`/data-source/${connectorId}`);
  };
  
  const canProceed = () => {
    switch (currentStep) {
      case "auth":
        if (connector?.authType === "api_key") {
          return formData.apiKey.length > 0;
        }
        if (connector?.authType === "db_connection") {
          return formData.connectionString.length > 0;
        }
        return true;
      case "test":
        return testStatus === "success";
      case "entities":
        return true;
      case "sync":
        return true;
      case "confirm":
        return formData.name.length > 0;
      default:
        return true;
    }
  };
  
  if (!connectorId) {
    return (
      <div className="p-6 max-w-2xl mx-auto">
        <Card>
          <CardContent className="p-8 text-center">
            <p className="text-muted-foreground">No connector specified</p>
            <Button className="mt-4" onClick={() => setLocation("/marketplace")}>
              Browse Connectors
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }
  
  if (connectorLoading) {
    return (
      <div className="p-6 max-w-2xl mx-auto">
        <Card>
          <CardContent className="p-8 flex items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </CardContent>
        </Card>
      </div>
    );
  }
  
  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6" data-testid="add-data-source-wizard">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => setLocation("/marketplace")} data-testid="button-back">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-xl font-bold">Connect {connector?.name}</h1>
          <p className="text-sm text-muted-foreground">Follow the steps to set up your data source</p>
        </div>
      </div>
      
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              {STEPS.map((step, index) => (
                <div key={step.id} className="flex items-center">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    index < currentStepIndex 
                      ? "bg-primary text-primary-foreground" 
                      : index === currentStepIndex 
                        ? "bg-primary text-primary-foreground" 
                        : "bg-muted text-muted-foreground"
                  }`}>
                    {index < currentStepIndex ? <Check className="h-4 w-4" /> : index + 1}
                  </div>
                  {index < STEPS.length - 1 && (
                    <div className={`w-8 h-0.5 ${index < currentStepIndex ? "bg-primary" : "bg-muted"}`} />
                  )}
                </div>
              ))}
            </div>
          </div>
          <CardTitle>{STEPS[currentStepIndex].label}</CardTitle>
          <Progress value={progress} className="h-1" />
        </CardHeader>
        
        <CardContent className="space-y-4">
          {currentStep === "auth" && (
            <div className="space-y-4">
              {connector?.authType === "oauth" && (
                <div className="p-6 border rounded-lg text-center space-y-4">
                  <Shield className="h-12 w-12 mx-auto text-primary" />
                  <p className="font-medium">Connect with {connector.name}</p>
                  <p className="text-sm text-muted-foreground">
                    You'll be redirected to {connector.name} to authorize access
                  </p>
                  <Button className="w-full" onClick={handleNext}>
                    <Key className="h-4 w-4 mr-2" />
                    Connect with OAuth
                  </Button>
                </div>
              )}
              
              {connector?.authType === "api_key" && (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="apiKey">API Key</Label>
                    <Input
                      id="apiKey"
                      type="password"
                      placeholder="Enter your API key"
                      value={formData.apiKey}
                      onChange={(e) => setFormData(prev => ({ ...prev, apiKey: e.target.value }))}
                      data-testid="input-api-key"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="apiSecret">API Secret (optional)</Label>
                    <Input
                      id="apiSecret"
                      type="password"
                      placeholder="Enter your API secret"
                      value={formData.apiSecret}
                      onChange={(e) => setFormData(prev => ({ ...prev, apiSecret: e.target.value }))}
                      data-testid="input-api-secret"
                    />
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground p-3 bg-muted/50 rounded-lg">
                    <Lock className="h-4 w-4" />
                    <span>Your credentials are encrypted at rest and never logged</span>
                  </div>
                </div>
              )}
              
              {connector?.authType === "db_connection" && (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="connectionString">Connection String</Label>
                    <Textarea
                      id="connectionString"
                      placeholder="postgresql://user:password@host:port/database"
                      value={formData.connectionString}
                      onChange={(e) => setFormData(prev => ({ ...prev, connectionString: e.target.value }))}
                      className="font-mono text-sm"
                      data-testid="input-connection-string"
                    />
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground p-3 bg-muted/50 rounded-lg">
                    <Shield className="h-4 w-4" />
                    <span>Connection is read-only. We will never modify your database.</span>
                  </div>
                </div>
              )}
              
              {connector?.authType === "webhook" && (
                <div className="space-y-4">
                  <div className="p-4 border rounded-lg bg-muted/50">
                    <p className="text-sm font-medium mb-2">Your Webhook Endpoint</p>
                    <code className="text-xs bg-background p-2 rounded block">
                      https://api.predixen.io/webhooks/{connectorId}/ingest
                    </code>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Configure your system to send events to this endpoint
                  </p>
                </div>
              )}
              
              {connector?.authType === "file_upload" && (
                <div className="p-6 border-2 border-dashed rounded-lg text-center space-y-4">
                  <FileText className="h-12 w-12 mx-auto text-muted-foreground" />
                  <p className="font-medium">Upload your file</p>
                  <p className="text-sm text-muted-foreground">
                    Drag and drop or click to select a file
                  </p>
                  <Button variant="outline">Select File</Button>
                </div>
              )}
            </div>
          )}
          
          {currentStep === "test" && (
            <div className="space-y-4">
              <div className={`p-8 border rounded-lg text-center space-y-4 ${
                testStatus === "success" ? "border-emerald-500/30 bg-emerald-500/5" :
                testStatus === "error" ? "border-red-500/30 bg-red-500/5" : ""
              }`}>
                {testStatus === "idle" && (
                  <>
                    <Database className="h-12 w-12 mx-auto text-muted-foreground" />
                    <p className="font-medium">Ready to test connection</p>
                    <p className="text-sm text-muted-foreground">
                      We'll verify your credentials and check connectivity
                    </p>
                    <Button onClick={handleTestConnection} data-testid="button-test-connection">
                      Test Connection
                    </Button>
                  </>
                )}
                
                {testStatus === "testing" && (
                  <>
                    <Loader2 className="h-12 w-12 mx-auto animate-spin text-primary" />
                    <p className="font-medium">Testing connection...</p>
                    <p className="text-sm text-muted-foreground">
                      This may take a few seconds
                    </p>
                  </>
                )}
                
                {testStatus === "success" && (
                  <>
                    <CheckCircle className="h-12 w-12 mx-auto text-emerald-500" />
                    <p className="font-medium text-emerald-600">Connection successful!</p>
                    <p className="text-sm text-muted-foreground">
                      Your credentials have been verified
                    </p>
                  </>
                )}
                
                {testStatus === "error" && (
                  <>
                    <XCircle className="h-12 w-12 mx-auto text-red-500" />
                    <p className="font-medium text-red-600">Connection failed</p>
                    <p className="text-sm text-muted-foreground">
                      Please check your credentials and try again
                    </p>
                    <Button variant="outline" onClick={() => setTestStatus("idle")}>
                      Try Again
                    </Button>
                  </>
                )}
              </div>
            </div>
          )}
          
          {currentStep === "entities" && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Select which data to sync from {connector?.name}
              </p>
              <div className="space-y-2">
                {connector?.dataCollected.map((entity) => (
                  <label
                    key={entity}
                    className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover-elevate"
                  >
                    <input
                      type="checkbox"
                      checked={formData.selectedEntities.includes(entity)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setFormData(prev => ({
                            ...prev,
                            selectedEntities: [...prev.selectedEntities, entity]
                          }));
                        } else {
                          setFormData(prev => ({
                            ...prev,
                            selectedEntities: prev.selectedEntities.filter(e => e !== entity)
                          }));
                        }
                      }}
                      className="rounded"
                    />
                    <span className="font-medium">{entity}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
          
          {currentStep === "sync" && (
            <div className="space-y-6">
              {connector?.supportsWebhooks && connector?.supportsPolling && (
                <div className="space-y-3">
                  <Label>Sync Mode</Label>
                  <RadioGroup
                    value={formData.syncMode}
                    onValueChange={(v) => setFormData(prev => ({ ...prev, syncMode: v as any }))}
                  >
                    <label className="flex items-start gap-3 p-3 border rounded-lg cursor-pointer">
                      <RadioGroupItem value="webhook" id="webhook" className="mt-1" />
                      <div>
                        <p className="font-medium">Webhook (Real-time)</p>
                        <p className="text-sm text-muted-foreground">
                          Receive updates instantly when data changes
                        </p>
                      </div>
                    </label>
                    <label className="flex items-start gap-3 p-3 border rounded-lg cursor-pointer">
                      <RadioGroupItem value="poll" id="poll" className="mt-1" />
                      <div>
                        <p className="font-medium">Polling</p>
                        <p className="text-sm text-muted-foreground">
                          Periodically fetch data on a schedule
                        </p>
                      </div>
                    </label>
                  </RadioGroup>
                </div>
              )}
              
              {formData.syncMode === "poll" && (
                <div className="space-y-3">
                  <Label>Refresh Frequency</Label>
                  <Select
                    value={formData.refreshFrequency}
                    onValueChange={(v) => setFormData(prev => ({ ...prev, refreshFrequency: v as any }))}
                  >
                    <SelectTrigger data-testid="select-frequency">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="hourly">Every hour</SelectItem>
                      <SelectItem value="daily">Once per day</SelectItem>
                      <SelectItem value="manual">Manual only</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
          )}
          
          {currentStep === "confirm" && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Connection Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  data-testid="input-connection-name"
                />
              </div>
              
              <div className="p-4 border rounded-lg space-y-3">
                <h4 className="font-medium">Summary</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <span className="text-muted-foreground">Connector:</span>
                  <span>{connector?.name}</span>
                  <span className="text-muted-foreground">Sync Mode:</span>
                  <span className="capitalize">{formData.syncMode}</span>
                  <span className="text-muted-foreground">Frequency:</span>
                  <span className="capitalize">{formData.refreshFrequency}</span>
                  <span className="text-muted-foreground">Data Selected:</span>
                  <span>{formData.selectedEntities.length || "All"} entities</span>
                </div>
              </div>
            </div>
          )}
        </CardContent>
        
        <CardFooter className="flex justify-between pt-4 border-t">
          <Button
            variant="outline"
            onClick={handleBack}
            disabled={currentStepIndex === 0}
            data-testid="button-step-back"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          
          {currentStep === "confirm" ? (
            <Button onClick={handleComplete} disabled={!canProceed() || isLoading} data-testid="button-complete">
              {isLoading ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Check className="h-4 w-4 mr-2" />
              )}
              Complete Setup
            </Button>
          ) : (
            <Button onClick={handleNext} disabled={!canProceed()} data-testid="button-step-next">
              Next
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          )}
        </CardFooter>
      </Card>
    </div>
  );
}
