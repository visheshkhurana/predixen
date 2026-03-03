import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer } from 'recharts';

interface BreakdownItem {
  score: number;
  weight: number;
  value: number | null;
  label: string;
}

interface ReadinessBreakdown {
  runway: BreakdownItem;
  growth: BreakdownItem;
  unit_economics: BreakdownItem;
  market_timing: BreakdownItem;
  narrative_quality: BreakdownItem;
}

interface ReadinessData {
  overall: number;
  breakdown: ReadinessBreakdown;
  status: string;
}

function getScoreColor(score: number): string {
  if (score < 40) return '#ef4444';
  if (score < 70) return '#eab308';
  if (score < 85) return '#84cc16';
  return '#22c55e';
}

function getStatusLabel(status: string): string {
  switch (status) {
    case 'not-ready': return 'Not Ready';
    case 'getting-close': return 'Getting Close';
    case 'ready': return 'Ready';
    case 'optimal': return 'Optimal';
    default: return status;
  }
}

function getStatusVariant(status: string): 'destructive' | 'outline' | 'default' | 'secondary' {
  switch (status) {
    case 'not-ready': return 'destructive';
    case 'getting-close': return 'outline';
    case 'ready': return 'default';
    case 'optimal': return 'default';
    default: return 'outline';
  }
}

function CircularProgress({ score }: { score: number }) {
  const radius = 70;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = getScoreColor(score);

  return (
    <div className="relative inline-flex items-center justify-center" data-testid="display-readiness-score-circle">
      <svg width="180" height="180" viewBox="0 0 180 180">
        <circle
          cx="90"
          cy="90"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="10"
          className="text-muted/30"
        />
        <circle
          cx="90"
          cy="90"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 90 90)"
          style={{ transition: 'stroke-dashoffset 1s ease-in-out' }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-4xl font-bold" style={{ color }} data-testid="text-readiness-score-value">
          {Math.round(score)}
        </span>
        <span className="text-xs text-muted-foreground">/100</span>
      </div>
    </div>
  );
}

const breakdownLabels: Record<string, string> = {
  runway: 'Runway',
  growth: 'Growth',
  unit_economics: 'Unit Economics',
  market_timing: 'Market Timing',
  narrative_quality: 'Narrative Quality',
};

function safeScore(item: BreakdownItem | number | undefined): number {
  if (item == null) return 0;
  if (typeof item === 'number') return item;
  return typeof item.score === 'number' ? item.score : 0;
}

export function ReadinessScore({ data }: { data: ReadinessData }) {
  const radarData = [
    { metric: 'Runway', value: safeScore(data.breakdown.runway) },
    { metric: 'Growth', value: safeScore(data.breakdown.growth) },
    { metric: 'Unit Econ', value: safeScore(data.breakdown.unit_economics) },
    { metric: 'Market', value: safeScore(data.breakdown.market_timing) },
    { metric: 'Narrative', value: safeScore(data.breakdown.narrative_quality) },
  ];

  return (
    <div className="space-y-6">
      <Card data-testid="card-readiness-overview">
        <CardHeader>
          <CardTitle className="text-lg">Fundraising Readiness</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 md:grid-cols-2">
            <div className="flex flex-col items-center gap-3">
              <CircularProgress score={data.overall} />
              <Badge variant={getStatusVariant(data.status)} data-testid="badge-readiness-status">
                {getStatusLabel(data.status)}
              </Badge>
            </div>

            <div className="space-y-3" data-testid="display-readiness-breakdown">
              {Object.entries(data.breakdown).map(([key, item]) => {
                const score = safeScore(item as BreakdownItem | number);
                return (
                  <div key={key} className="space-y-1">
                    <div className="flex items-center justify-between gap-2 text-sm">
                      <span className="text-muted-foreground">{breakdownLabels[key] || key}</span>
                      <span className="font-medium" data-testid={`text-breakdown-${key}`}>{Math.round(score)}</span>
                    </div>
                    <Progress
                      value={score}
                      className="h-2"
                      data-testid={`progress-breakdown-${key}`}
                    />
                  </div>
                );
              })}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card data-testid="card-readiness-radar">
        <CardHeader>
          <CardTitle className="text-lg">Score Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]" data-testid="display-radar-chart">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="metric" tick={{ fontSize: 12 }} />
                <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
                <Radar
                  name="Score"
                  dataKey="value"
                  stroke={getScoreColor(data.overall)}
                  fill={getScoreColor(data.overall)}
                  fillOpacity={0.2}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
