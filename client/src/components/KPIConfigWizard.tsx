import { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Settings, GripVertical, Clock, DollarSign, Percent, Users, TrendingDown, AlertTriangle, CheckCircle, Eye, EyeOff, ChevronUp, ChevronDown, RotateCcw } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface KPIConfig {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  category: 'runway' | 'revenue' | 'efficiency' | 'health';
  enabled: boolean;
  order: number;
}

export const DEFAULT_KPI_CONFIGS: KPIConfig[] = [
  { id: 'runway', name: 'Runway (P50)', description: 'Months of runway at current burn rate', icon: <Clock className="h-4 w-4" />, category: 'runway', enabled: true, order: 0 },
  { id: 'survival', name: '18-Month Survival', description: 'Probability of positive cash after 18 months', icon: <CheckCircle className="h-4 w-4" />, category: 'runway', enabled: true, order: 1 },
  { id: 'mrr', name: 'Monthly Revenue', description: 'Monthly recurring revenue from customers', icon: <DollarSign className="h-4 w-4" />, category: 'revenue', enabled: true, order: 2 },
  { id: 'burn_multiple', name: 'Burn Multiple', description: 'Net burn divided by net new ARR (requires ARR data)', icon: <Percent className="h-4 w-4" />, category: 'efficiency', enabled: false, order: 3 },
  { id: 'cash_balance', name: 'Cash Balance', description: 'Current cash on hand', icon: <DollarSign className="h-4 w-4" />, category: 'runway', enabled: true, order: 4 },
  { id: 'net_burn', name: 'Net Burn', description: 'Monthly cash outflow (expenses - revenue)', icon: <TrendingDown className="h-4 w-4" />, category: 'runway', enabled: true, order: 5 },
  { id: 'gross_margin', name: 'Gross Margin', description: 'Revenue minus COGS as percentage', icon: <Percent className="h-4 w-4" />, category: 'efficiency', enabled: true, order: 6 },
  { id: 'churn_rate', name: 'Churn Rate', description: 'Monthly customer or revenue churn (requires customer data)', icon: <Users className="h-4 w-4" />, category: 'health', enabled: false, order: 7 },
  { id: 'ltv_cac', name: 'LTV:CAC Ratio', description: 'Lifetime value to acquisition cost ratio', icon: <Users className="h-4 w-4" />, category: 'efficiency', enabled: false, order: 8 },
  { id: 'arr_growth', name: 'ARR Growth', description: 'Annual recurring revenue growth rate', icon: <TrendingDown className="h-4 w-4" />, category: 'revenue', enabled: false, order: 9 },
  { id: 'nrr', name: 'Net Revenue Retention', description: 'Revenue retention including expansion', icon: <Percent className="h-4 w-4" />, category: 'revenue', enabled: false, order: 10 },
];

const STORAGE_KEY = 'founderconsole_kpi_config';

export function loadKPIConfig(): KPIConfig[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed.map((saved: any) => {
        const def = DEFAULT_KPI_CONFIGS.find(d => d.id === saved.id);
        return def ? { ...def, enabled: saved.enabled, order: saved.order } : null;
      }).filter(Boolean).sort((a: KPIConfig, b: KPIConfig) => a.order - b.order);
    }
  } catch (e) {
    console.error('Failed to load KPI config:', e);
  }
  return [...DEFAULT_KPI_CONFIGS];
}

export function saveKPIConfig(configs: KPIConfig[]): void {
  try {
    const toSave = configs.map(c => ({ id: c.id, enabled: c.enabled, order: c.order }));
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
  } catch (e) {
    console.error('Failed to save KPI config:', e);
  }
}

interface KPIConfigWizardProps {
  configs: KPIConfig[];
  onConfigChange: (configs: KPIConfig[]) => void;
  className?: string;
}

export function KPIConfigWizard({ configs, onConfigChange, className }: KPIConfigWizardProps) {
  const [open, setOpen] = useState(false);
  const [localConfigs, setLocalConfigs] = useState<KPIConfig[]>(configs);

  const handleOpen = useCallback((isOpen: boolean) => {
    if (isOpen) {
      setLocalConfigs([...configs]);
    }
    setOpen(isOpen);
  }, [configs]);

  const toggleKPI = useCallback((id: string) => {
    setLocalConfigs(prev => 
      prev.map(c => c.id === id ? { ...c, enabled: !c.enabled } : c)
    );
  }, []);

  const moveKPI = useCallback((id: string, direction: 'up' | 'down') => {
    setLocalConfigs(prev => {
      const index = prev.findIndex(c => c.id === id);
      if (index === -1) return prev;
      const newIndex = direction === 'up' ? index - 1 : index + 1;
      if (newIndex < 0 || newIndex >= prev.length) return prev;
      
      const newConfigs = [...prev];
      [newConfigs[index], newConfigs[newIndex]] = [newConfigs[newIndex], newConfigs[index]];
      return newConfigs.map((c, i) => ({ ...c, order: i }));
    });
  }, []);

  const handleSave = useCallback(() => {
    saveKPIConfig(localConfigs);
    onConfigChange(localConfigs);
    setOpen(false);
  }, [localConfigs, onConfigChange]);

  const handleReset = useCallback(() => {
    setLocalConfigs([...DEFAULT_KPI_CONFIGS]);
  }, []);

  const enabledCount = localConfigs.filter(c => c.enabled).length;

  const categoryColors: Record<string, string> = {
    runway: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30',
    revenue: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
    efficiency: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30',
    health: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30',
  };

  return (
    <Dialog open={open} onOpenChange={handleOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className={cn("gap-2", className)} data-testid="button-kpi-config">
          <Settings className="h-4 w-4" />
          Configure KPIs
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            KPI Dashboard Configuration
          </DialogTitle>
          <DialogDescription>
            Choose which KPIs to display and arrange them in your preferred order.
            {enabledCount < 4 && (
              <span className="text-amber-600 dark:text-amber-400 ml-1">
                (Recommended: at least 4 KPIs)
              </span>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-4">
          {localConfigs.map((kpi, index) => (
            <div
              key={kpi.id}
              className={cn(
                "flex items-center gap-3 p-3 rounded-lg border transition-colors",
                kpi.enabled ? "bg-card border-border" : "bg-muted/30 border-muted opacity-60"
              )}
              data-testid={`kpi-config-item-${kpi.id}`}
            >
              <div className="flex flex-col gap-0.5">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={() => moveKPI(kpi.id, 'up')}
                  disabled={index === 0}
                  data-testid={`button-move-up-${kpi.id}`}
                >
                  <ChevronUp className="h-3 w-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={() => moveKPI(kpi.id, 'down')}
                  disabled={index === localConfigs.length - 1}
                  data-testid={`button-move-down-${kpi.id}`}
                >
                  <ChevronDown className="h-3 w-3" />
                </Button>
              </div>

              <div className="flex items-center gap-2">
                <GripVertical className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground font-mono text-xs w-5">{index + 1}</span>
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  {kpi.icon}
                  <span className="font-medium">{kpi.name}</span>
                  <Badge variant="outline" className={cn("text-xs", categoryColors[kpi.category])}>
                    {kpi.category}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground truncate">{kpi.description}</p>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant={kpi.enabled ? "default" : "ghost"}
                  size="sm"
                  onClick={() => toggleKPI(kpi.id)}
                  className="gap-1"
                  data-testid={`button-toggle-${kpi.id}`}
                >
                  {kpi.enabled ? (
                    <>
                      <Eye className="h-3 w-3" />
                      Visible
                    </>
                  ) : (
                    <>
                      <EyeOff className="h-3 w-3" />
                      Hidden
                    </>
                  )}
                </Button>
              </div>
            </div>
          ))}
        </div>

        <DialogFooter className="flex justify-between gap-2">
          <Button variant="ghost" onClick={handleReset} className="gap-2" data-testid="button-reset-kpi-config">
            <RotateCcw className="h-4 w-4" />
            Reset to Default
          </Button>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setOpen(false)} data-testid="button-cancel-kpi-config">
              Cancel
            </Button>
            <Button onClick={handleSave} data-testid="button-save-kpi-config">
              Save Configuration
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function useKPIConfig() {
  const [configs, setConfigs] = useState<KPIConfig[]>(() => loadKPIConfig());
  
  const handleConfigChange = useCallback((newConfigs: KPIConfig[]) => {
    setConfigs(newConfigs);
    saveKPIConfig(newConfigs);
  }, []);

  const enabledKPIs = configs.filter(c => c.enabled).sort((a, b) => a.order - b.order);
  const enabledKPIIds = new Set(enabledKPIs.map(k => k.id));

  return {
    configs,
    enabledKPIs,
    enabledKPIIds,
    handleConfigChange,
  };
}
