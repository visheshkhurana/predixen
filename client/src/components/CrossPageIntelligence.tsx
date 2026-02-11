import { useMemo } from 'react';
import { useFounderStore } from '@/store/founderStore';
import { useScenarios, useSimulation } from '@/api/hooks';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Link } from 'wouter';
import { AlertTriangle, TrendingUp, Zap, ArrowRight, Shield, Clock } from 'lucide-react';

type AlertType = 'warning' | 'opportunity' | 'critical' | 'info';

interface IntelligenceAlert {
  type: AlertType;
  title: string;
  description: string;
  action?: { label: string; href: string };
  metric?: string;
}

function useLatestSimulation() {
  const currentCompany = useFounderStore((s) => s.currentCompany);
  const companyId = currentCompany?.id ?? null;

  const { data: scenarios } = useScenarios(companyId);

  const latestScenario = useMemo(() => {
    if (!scenarios || !Array.isArray(scenarios) || scenarios.length === 0) return null;
    const sorted = [...scenarios].sort((a: any, b: any) => {
      const dateA = new Date(a.updated_at || a.created_at || 0).getTime();
      const dateB = new Date(b.updated_at || b.created_at || 0).getTime();
      return dateB - dateA;
    });
    return sorted[0];
  }, [scenarios]);

  const scenarioId = latestScenario?.id ?? null;
  const { data: simulation } = useSimulation(scenarioId);

  return { simulation: simulation as any, scenario: latestScenario as any, companyId };
}

function generateAlerts(simulation: any, scenario: any, baseline: any): IntelligenceAlert[] {
  if (!simulation) return [];
  const alerts: IntelligenceAlert[] = [];

  const survival18m = simulation.survivalProbability?.['18m'] ?? simulation.survival?.['18m'] ?? 0;
  const runwayP50 = simulation.runway?.p50 ?? 0;
  const runwayP10 = simulation.runway?.p10 ?? 0;
  const monthlyBurn = simulation.summary?.monthly_burn ?? 0;
  const monthlyRevenue = simulation.summary?.monthly_revenue ?? 0;

  if (survival18m < 40) {
    alerts.push({
      type: 'critical',
      title: 'Survival probability below 40%',
      description: `Your latest simulation "${scenario?.name || 'scenario'}" shows ${survival18m.toFixed(0)}% survival at 18 months. Consider reviewing cost structure or fundraising options.`,
      action: { label: 'Open Scenarios', href: '/scenarios' },
    });
  } else if (survival18m < 60) {
    alerts.push({
      type: 'warning',
      title: 'Moderate survival risk detected',
      description: `${survival18m.toFixed(0)}% survival probability at 18 months. Running stress tests could help identify mitigation strategies.`,
      action: { label: 'Run Stress Test', href: '/scenarios' },
    });
  }

  if (runwayP50 > 0 && runwayP50 < 9) {
    alerts.push({
      type: 'critical',
      title: `Runway under 9 months (${runwayP50.toFixed(1)}mo P50)`,
      description: 'Consider immediate cost reduction or fundraising to extend runway.',
      action: { label: 'Explore Options', href: '/scenarios' },
    });
  } else if (runwayP50 >= 9 && runwayP50 < 14) {
    alerts.push({
      type: 'warning',
      title: `Runway at ${runwayP50.toFixed(1)} months`,
      description: 'Start planning your next fundraise or path to profitability.',
      action: { label: 'Plan Fundraise', href: '/fundraising' },
    });
  }

  if (runwayP10 > 0 && runwayP10 < 6) {
    alerts.push({
      type: 'warning',
      title: 'Worst-case runway under 6 months',
      description: `In a downside scenario (P10), your runway drops to ${runwayP10.toFixed(1)} months. Consider building a buffer.`,
      action: { label: 'View Scenarios', href: '/scenarios' },
    });
  }

  if (monthlyRevenue > 0 && monthlyBurn > 0) {
    const burnMultiple = monthlyBurn / monthlyRevenue;
    if (burnMultiple > 3) {
      alerts.push({
        type: 'warning',
        title: 'High burn multiple',
        description: `You're spending $${(burnMultiple).toFixed(1)} for every $1 of revenue. Focus on unit economics improvement.`,
        action: { label: 'Review Metrics', href: '/scenarios' },
        metric: `${burnMultiple.toFixed(1)}x`,
      });
    }
  }

  if (survival18m >= 85 && runwayP50 >= 18) {
    alerts.push({
      type: 'opportunity',
      title: 'Strong position for growth investment',
      description: `${survival18m.toFixed(0)}% survival with ${runwayP50.toFixed(0)}+ month runway. You have room to invest in growth.`,
      action: { label: 'Explore Growth', href: '/scenarios' },
    });
  }

  return alerts.slice(0, 2);
}

const alertStyles: Record<AlertType, { border: string; bg: string; icon: typeof AlertTriangle; iconColor: string; badgeClass: string }> = {
  critical: {
    border: 'border-red-500/30',
    bg: 'bg-red-50/30 dark:bg-red-950/10',
    icon: AlertTriangle,
    iconColor: 'text-red-600 dark:text-red-400',
    badgeClass: 'border-red-500/50 text-red-600 dark:text-red-400',
  },
  warning: {
    border: 'border-amber-500/30',
    bg: 'bg-amber-50/30 dark:bg-amber-950/10',
    icon: Clock,
    iconColor: 'text-amber-600 dark:text-amber-400',
    badgeClass: 'border-amber-500/50 text-amber-600 dark:text-amber-400',
  },
  opportunity: {
    border: 'border-emerald-500/30',
    bg: 'bg-emerald-50/30 dark:bg-emerald-950/10',
    icon: TrendingUp,
    iconColor: 'text-emerald-600 dark:text-emerald-400',
    badgeClass: 'border-emerald-500/50 text-emerald-600 dark:text-emerald-400',
  },
  info: {
    border: 'border-primary/30',
    bg: 'bg-primary/5',
    icon: Zap,
    iconColor: 'text-primary',
    badgeClass: 'border-primary/50 text-primary',
  },
};

interface CrossPageIntelligenceProps {
  context?: 'dashboard' | 'data-input' | 'fundraising' | 'general';
  className?: string;
  testId?: string;
}

export function CrossPageIntelligence({ context = 'general', className = '', testId = 'cross-page-intelligence' }: CrossPageIntelligenceProps) {
  const { simulation, scenario } = useLatestSimulation();
  const baseline = useFounderStore((s) => s.financialBaseline);

  const alerts = useMemo(() => generateAlerts(simulation, scenario, baseline), [simulation, scenario, baseline]);

  if (alerts.length === 0) return null;

  return (
    <div className={`space-y-2 ${className}`} data-testid={testId}>
      {alerts.map((alert, idx) => {
        const style = alertStyles[alert.type];
        const Icon = style.icon;
        return (
          <Card key={idx} className={`${style.border} ${style.bg}`} data-testid={`${testId}-alert-${idx}`}>
            <CardContent className="pt-3 pb-3 px-4">
              <div className="flex items-start gap-3">
                <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${style.iconColor}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-sm font-semibold">{alert.title}</span>
                    {alert.metric && (
                      <Badge variant="outline" className={`text-[10px] ${style.badgeClass}`}>{alert.metric}</Badge>
                    )}
                    <Badge variant="outline" className="text-[10px]">
                      <Shield className="h-2.5 w-2.5 mr-1" />
                      From simulation
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">{alert.description}</p>
                </div>
                {alert.action && (
                  <Link href={alert.action.href}>
                    <Button variant="ghost" size="sm" className="shrink-0" data-testid={`${testId}-action-${idx}`}>
                      {alert.action.label}
                      <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
                    </Button>
                  </Link>
                )}
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
