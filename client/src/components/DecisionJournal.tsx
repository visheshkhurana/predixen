import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  BookOpen, Check, Pause, X, Clock, TrendingUp, ArrowRight
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { DecisionStatus } from '@/components/DecisionCard';

interface JournalEntry {
  id: string;
  title: string;
  rank: number;
  status: DecisionStatus;
  survivalImpact: number;
  runwayChange: number;
}

interface DecisionJournalProps {
  entries: JournalEntry[];
  testId?: string;
}

const STATUS_CONFIG: Record<DecisionStatus, { icon: typeof Check; label: string; color: string }> = {
  adopted: { icon: Check, label: 'Adopted', color: 'text-emerald-500' },
  deferred: { icon: Pause, label: 'Deferred', color: 'text-amber-500' },
  rejected: { icon: X, label: 'Rejected', color: 'text-red-500' },
  pending: { icon: Clock, label: 'Pending', color: 'text-muted-foreground' },
};

export function DecisionJournal({ entries, testId = 'decision-journal' }: DecisionJournalProps) {
  const stats = useMemo(() => {
    const adopted = entries.filter(e => e.status === 'adopted');
    const pending = entries.filter(e => e.status === 'pending');
    const totalSurvivalGain = adopted.reduce((sum, e) => sum + e.survivalImpact, 0);
    const totalRunwayGain = adopted.reduce((sum, e) => sum + e.runwayChange, 0);

    return { adopted: adopted.length, pending: pending.length, totalSurvivalGain, totalRunwayGain };
  }, [entries]);

  if (entries.length === 0) return null;

  return (
    <Card data-testid={testId}>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-primary" />
          <CardTitle className="text-lg">Decision Journal</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-3 rounded-lg bg-secondary/50 text-center">
            <p className="text-2xl font-bold">{entries.length}</p>
            <p className="text-xs text-muted-foreground">Total Options</p>
          </div>
          <div className="p-3 rounded-lg bg-emerald-500/10 text-center">
            <p className="text-2xl font-bold text-emerald-500">{stats.adopted}</p>
            <p className="text-xs text-muted-foreground">Adopted</p>
          </div>
          <div className="p-3 rounded-lg bg-emerald-500/5 text-center">
            <p className="text-2xl font-bold text-emerald-500">
              {stats.totalSurvivalGain > 0 ? '+' : ''}{stats.totalSurvivalGain.toFixed(1)}%
            </p>
            <p className="text-xs text-muted-foreground">Survival Gain</p>
          </div>
          <div className="p-3 rounded-lg bg-primary/5 text-center">
            <p className="text-2xl font-bold text-primary">
              {stats.totalRunwayGain > 0 ? '+' : ''}{stats.totalRunwayGain.toFixed(1)}mo
            </p>
            <p className="text-xs text-muted-foreground">Runway Gain</p>
          </div>
        </div>

        <div className="space-y-2">
          {entries.map((entry) => {
            const config = STATUS_CONFIG[entry.status];
            const StatusIcon = config.icon;

            return (
              <div 
                key={entry.id} 
                className="flex items-center gap-3 p-2.5 rounded-lg bg-secondary/30"
                data-testid={`journal-entry-${entry.id}`}
              >
                <StatusIcon className={cn("h-4 w-4 flex-shrink-0", config.color)} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium truncate">{entry.title}</span>
                    <Badge variant="outline" className="text-xs flex-shrink-0">
                      #{entry.rank}
                    </Badge>
                  </div>
                </div>
                <div className="flex items-center gap-3 text-xs font-mono flex-shrink-0">
                  <span className={entry.survivalImpact >= 0 ? "text-emerald-500" : "text-red-500"}>
                    {entry.survivalImpact >= 0 ? '+' : ''}{entry.survivalImpact.toFixed(1)}%
                  </span>
                  <span className={entry.runwayChange >= 0 ? "text-emerald-500" : "text-red-500"}>
                    {entry.runwayChange >= 0 ? '+' : ''}{entry.runwayChange.toFixed(1)}mo
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {stats.pending > 0 && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground pt-2 border-t border-border">
            <ArrowRight className="h-3 w-3" />
            <span>{stats.pending} decision{stats.pending > 1 ? 's' : ''} still pending review</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
